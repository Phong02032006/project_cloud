import csv
import io
import json
import re
import secrets
import statistics
from datetime import datetime, timedelta

import click
from flask import (Flask, Response, abort, flash, g, jsonify, redirect, render_template, request, send_file,
                   session, url_for)
from sqlalchemy import exists, inspect, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased
from werkzeug.middleware.proxy_fix import ProxyFix

import ai_generator
import grader_client
import pubsub_client
import storage_client
from auth import bp as auth_bp
from auth import login_required
from config import Config
from models import (DEFAULT_POLICY, AttemptEvent, Certificate, Exam, ExamVersion, Question, QuizAssignment,
                    RetakeTicket, Submission, User, db, generate_access_code, utcnow)

LETTERS = "ABCDEFGH"
EMAIL_RE = re.compile(r"^[^@\s,;]+@[^@\s,;]+\.[^@\s,;]+$")


def _ensure_schema(app):
    """Safely add missing columns, indexes and tables on existing SQLite or Azure SQL databases without losing data."""
    migrations = (
        ("questions", "image_url", "VARCHAR(500) NULL"),
        ("users", "password_hash", "VARCHAR(255) NULL"),
        ("exams", "visibility", "VARCHAR(20) NOT NULL DEFAULT 'private'"),
        ("exams", "access_code", "VARCHAR(16) NULL"),
    )
    with app.app_context():
        try:
            inspector = inspect(db.engine)
            for table, col, col_type in migrations:
                if inspector.has_table(table):
                    cols = {c["name"] for c in inspector.get_columns(table)}
                    if col not in cols:
                        db.session.execute(text(f"ALTER TABLE {table} ADD {col} {col_type}"))
                        db.session.commit()
            if inspector.has_table("exams") and not inspector.has_table("quiz_assignments"):
                QuizAssignment.__table__.create(bind=db.engine, checkfirst=True)
            if inspector.has_table("exams"):
                idx_names = {i["name"] for i in inspector.get_indexes("exams")}
                if "uq_exams_access_code" not in idx_names and "UX_exams_access_code" not in idx_names:
                    try:
                        db.session.execute(
                            text("CREATE UNIQUE INDEX uq_exams_access_code ON exams (access_code) WHERE access_code IS NOT NULL")
                        )
                        db.session.commit()
                    except Exception:
                        db.session.rollback()
                missing_codes = Exam.query.filter(Exam.visibility == "private", Exam.access_code.is_(None)).all()
                if missing_codes:
                    for ex in missing_codes:
                        ex.access_code = generate_access_code()
                    db.session.commit()
        except Exception:
            db.session.rollback()
            app.logger.warning("Auto-migration skipped", exc_info=True)


def create_app(overrides=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)
    if app.config["AUTH_MODE"] not in ("dev", "entra"):
        raise RuntimeError("AUTH_MODE must be 'dev' or 'entra'")
    # App Service terminates TLS at its front end; trust X-Forwarded-* so redirect URIs use https.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    db.init_app(app)
    _ensure_schema(app)
    app.register_blueprint(auth_bp)
    register_security(app)
    register_routes(app)
    register_cli(app)
    return app


def register_security(app):
    def csrf_token():
        if "csrf" not in session:
            session["csrf"] = secrets.token_urlsafe(32)
        return session["csrf"]

    @app.before_request
    def check_csrf():
        # The grader callback is server-to-server and authenticated by the shared secret instead.
        if request.method == "POST" and request.endpoint not in ("grader_callback", "cron_finalize"):
            # In dev mode, allow switching between accounts seamlessly without stale CSRF token clashes
            if request.endpoint == "auth.login" and app.config.get("AUTH_MODE") == "dev":
                return
            sent = request.form.get("csrf", "")
            if not sent or not secrets.compare_digest(sent, session.get("csrf", "")):
                abort(400, "Invalid or expired session. Please refresh and try again.")

    app.jinja_env.globals.update(csrf_token=csrf_token, letters=LETTERS)
    app.jinja_env.filters["num"] = lambda x: "" if x is None else f"{x:g}"
    # First letter of the given name, skipping titles such as "Dr." or "Ms.".
    app.jinja_env.filters["initial"] = lambda name: next(
        (w[0] for w in (name or "").split() if not w.endswith(".")), "?").upper()
    app.jinja_env.filters["plural"] = lambda n, word: f"{n} {word}{'' if n == 1 else 's'}"


def is_quiz_owner(user, quiz):
    if user is None or quiz is None:
        return False
    if user.role == "admin":
        return True
    return user.role == "teacher" and quiz.teacher_id == user.id


def is_student_assigned(user, quiz):
    if user is None or quiz is None or not user.email:
        return False
    email = user.email.strip().lower()
    if not email:
        return False
    return db.session.query(QuizAssignment.id).filter_by(
        quiz_id=quiz.id, student_email=email
    ).first() is not None


def can_access_quiz(user, quiz):
    if user is None or quiz is None:
        return False
    if is_quiz_owner(user, quiz):
        return True
    if user.role != "student" or not quiz.published:
        return False
    if (quiz.visibility or "private") == "public":
        return True
    return is_student_assigned(user, quiz)


def _own_exam(exam_id):
    exam = db.get_or_404(Exam, exam_id)
    if not is_quiz_owner(g.user, exam):
        abort(403)
    return exam


def _parse_lettered(row):
    """{'A'..'D', 'correct': 'A' / 'a;c' / 'B,D'} -> (options, correct indices). Blank options are
    dropped, so the correct letters are re-indexed past them; a letter pointing at a blank is rejected."""
    kept = [k for k in "ABCD" if str(row.get(k) or "").strip()]
    options = [str(row[k]).strip() for k in kept]
    raw = str(row.get("correct") or "")
    chosen = {c for c in raw.upper() if c in LETTERS}
    if not chosen or not chosen <= set(kept):
        raise ValueError(f"invalid correct answer: '{raw}'")
    return options, sorted(kept.index(c) for c in chosen)


def _counting(subs):
    """The attempts that count: the selected attempt per student, once graded and not voided."""
    return [s for s in subs if s.selected and s.status == "graded" and s.review not in ("cancelled", "revoked")]


# Preset revocation reasons: the label is shown publicly on /verify, the message goes only in the email.
REVOKE_REASONS = {
    "misconduct": ("Academic misconduct",
                   "A review found that the exam was not completed in line with the exam rules. If you believe this "
                   "is a mistake, please contact your teacher."),
    "issued_in_error": ("Issued in error",
                        "This certificate was issued by mistake. This is not a judgement on your work; your teacher "
                        "will contact you about next steps."),
    "identity": ("Identity could not be verified",
                 "We could not confirm that you were the person who took this exam. Please contact your teacher to "
                 "resolve this."),
    "other": ("Other", ""),
}


def _exam_stats(exam):
    graded = _counting(exam.submissions)
    if not graded:
        return None
    percents = [s.percent for s in graded]
    return {
        "count": len(graded),
        "avg": round(statistics.mean(percents), 2),
        "max": max(percents),
        "min": min(percents),
        "pass_rate": round(100 * sum(1 for s in graded if s.passed) / len(graded), 1),
    }


def _edit_impact(exam):
    """Who an edit would (not) affect: attempts are pinned to the version they started on."""
    per_version = {}
    for s in exam.submissions:
        per_version[s.version_id] = per_version.get(s.version_id, 0) + 1
    in_progress = sum(1 for s in exam.submissions if s.status == "in_progress")
    return {"in_progress": in_progress, "finished": len(exam.submissions) - in_progress,
            "per_version": per_version, "next_version": len(exam.versions) + 1}


def _question_stats(exam):
    """Percentage of graded submissions answering each question correctly (for the report)."""
    graded = [s for s in _counting(exam.submissions) if s.details]
    out = {}
    for q in exam.questions:
        hits = [d["is_correct"] for s in graded for d in s.details if d["question_id"] == q.id]
        out[q.id] = round(100 * sum(hits) / len(hits), 1) if hits else None
    return out


RESULT_FIELDS = ("score", "max_score", "percent", "passed", "details", "certificate_key", "certificate_id")
# A queued submission with no callback after this long can be re-sent by the student/teacher.
STUCK_AFTER = timedelta(minutes=2)
SUBMIT_GRACE = timedelta(seconds=30)
# Managed mode: the page pings every few seconds; a longer silence (tab killed, network down, JS off) is a violation.
HEARTBEAT_GAP = timedelta(seconds=30)
# Events the exam page may report: type -> counts as a violation (and locks the attempt).
CLIENT_EVENTS = {
    "fullscreen_exit": True,
    "focus_lost": True,
    "tab_switch": True,
    "copy": False,
    "paste": False,
    "context_menu": False,
}


def _answered_count(sub):
    if not isinstance(sub.answers, dict):
        return 0
    return sum(1 for v in sub.answers.values() if v)


def _publish_submission_state(sub, event_type):
    now = utcnow()
    last_dt = (sub.last_seen_at or sub.started_at) if sub.status == "in_progress" else (sub.submitted_at or now)
    total_q = len(sub.version.question_ids) if sub.version else 0
    pubsub_client.publish_exam_event(
        sub.exam_id,
        event_type,
        {
            "submission_id": sub.id,
            "student_id": sub.student_id,
            "student_name": sub.student.name if sub.student else "",
            "student_email": sub.student.email if sub.student else "",
            "attempt_no": sub.attempt_no,
            "selected": sub.selected,
            "status": sub.status,
            "answered_count": _answered_count(sub),
            "total_questions": total_q,
            "score": sub.score,
            "max_score": sub.max_score,
            "percent": sub.percent,
            "passed": sub.passed,
            "violations": sub.violations,
            "review": sub.review,
            "locked": sub.locked_at is not None,
            "lock_reason": sub.lock_reason,
            "updated_at": last_dt.strftime("%H:%M:%S") if sub.status == "in_progress" else last_dt.strftime("%b %d, %Y %H:%M"),
        },
    )


def _apply_result(sub, result):
    sub.score, sub.max_score, sub.percent = result["score"], result["max_score"], result["percent"]
    sub.passed, sub.details = result["passed"], result["details"]
    if result["certificate_key"] and sub.certificate:
        cert = sub.certificate
        cert.s3_key, cert.issued_at = result["certificate_key"], cert.issued_at or utcnow()
        if cert.status == "issuing":
            cert.status, cert.status_changed_at = "valid", utcnow()
    sub.status = "graded"


def _is_stuck(sub):
    return sub.status == "pending" and utcnow() - sub.submitted_at > STUCK_AFTER


# this try to claim the submission; only in_progress one can be claimed
def _claim(sub, **values):
    claimed = db.session.execute(
        update(Submission)
        .where(Submission.id == sub.id, Submission.status == "in_progress")
        .values(status="pending", submitted_at=utcnow(), locked_at=None, **values)
    ).rowcount == 1
    db.session.commit()
    db.session.refresh(sub)
    return claimed


def _log(sub, type, detail=None, counted=False):
    db.session.add(AttemptEvent(submission_id=sub.id, type=type, detail=detail, counted=counted))


def _record(app, sub, type, detail=None, violation=False):
    """Log an exam monitoring event. A violation is counted, may lock the attempt for re-entry approval and
    may trigger auto-submit. Nothing is counted while the attempt is already locked or finished."""
    policy = sub.version.settings
    if sub.status != "in_progress" or (not policy["managed"] and type != "tab_switch"):
        return
    counted = violation and sub.locked_at is None
    _log(sub, type, detail, counted)
    now = utcnow()
    if counted:
        # Increment in SQL so concurrent reports from the same page are not lost.
        values = {"violations": Submission.violations + 1}
        if policy["managed"] and policy["reentry_approval"]:
            values.update(locked_at=now, lock_reason=type)
        db.session.execute(update(Submission).where(Submission.id == sub.id).values(**values))
    db.session.commit()
    db.session.refresh(sub)
    pubsub_client.publish_exam_event(
        sub.exam_id,
        "tab_violation" if type in ("tab_switch", "focus_lost") else "integrity_event",
        {
            "submission_id": sub.id,
            "student_id": sub.student_id,
            "student_name": sub.student.name if sub.student else "",
            "student_email": sub.student.email if sub.student else "",
            "attempt_no": sub.attempt_no,
            "event_type": type,
            "detail": detail,
            "counted": counted,
            "violations": sub.violations,
            "locked": sub.locked_at is not None,
            "lock_reason": sub.lock_reason,
            "status": sub.status,
            "at": now.strftime("%H:%M:%S"),
        },
    )
    limit = policy["autosubmit_after"]
    if counted and policy["managed"] and limit and sub.violations >= limit and _claim(sub):
        _log(sub, "auto_submitted", f"after {sub.violations} violations")
        db.session.commit()
        _grade_and_save(app, sub)


def _attempt_state(sub):
    state = {"status": sub.status, "locked": sub.locked_at is not None, "violations": sub.violations}
    if sub.status != "in_progress":
        state["redirect"] = url_for("submission_view", sub_id=sub.id)
    return state


def _attempts(exam, student_id):
    return Submission.query.filter_by(exam_id=exam.id, student_id=student_id).order_by(Submission.attempt_no).all()


def _claimed_ticket(exam, student_id):
    return (RetakeTicket.query.filter(RetakeTicket.exam_id == exam.id, RetakeTicket.student_id == student_id,
                                      RetakeTicket.claimed_at.isnot(None))
            .order_by(RetakeTicket.claimed_at.desc()).first())


def _open_ticket(exam, student_id):
    tickets = RetakeTicket.query.filter_by(exam_id=exam.id, student_id=student_id, claimed_at=None).all()
    return next((t for t in tickets if t.is_open), None)


def _allowance(exam, student_id):
    ticket = _claimed_ticket(exam, student_id)
    return 1 if ticket and not ticket.full else exam.max_attempts


def _window_closed(exam, student_id):
    deadline = exam.selection_deadline
    if deadline is None or utcnow() < deadline:
        return False
    # A retake claimed after the deadline runs until its attempts are used up.
    ticket = _claimed_ticket(exam, student_id)
    if ticket and ticket.claimed_at >= deadline:
        used = Submission.query.filter_by(exam_id=exam.id, student_id=student_id).count()
        return used >= _allowance(exam, student_id)
    return True


def _can_start(exam, attempts):
    student_id = attempts[0].student_id if attempts else g.user.id
    return (not any(a.selected or a.status == "in_progress" for a in attempts)
            and len(attempts) < _allowance(exam, student_id) and not _window_closed(exam, student_id))


def _start_attempt(exam, student_id, attempts):
    """Returns the new attempt, or None if another request started one at the same moment."""
    allowance = _allowance(exam, student_id)
    sub = Submission(exam_id=exam.id, student_id=student_id, version_id=exam.current_version_id, answers={},
                     status="in_progress", attempt_no=max((a.attempt_no for a in attempts), default=0) + 1,
                     selected=allowance == 1)
    db.session.add(sub)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return None
    _publish_submission_state(sub, "attempt_started")
    return sub


def _select(app, sub):
    """Mark `sub` as the attempt that counts, unless one already is (checked in the same UPDATE), then issue
    its certificate by grading it again with issuing on."""
    other = aliased(Submission)
    already = exists().where(other.exam_id == sub.exam_id, other.student_id == sub.student_id, other.selected)
    claimed = db.session.execute(
        update(Submission).where(Submission.id == sub.id, ~already).values(selected=True)
    ).rowcount == 1
    db.session.commit()
    db.session.refresh(sub)
    if claimed and sub.status == "graded":
        _grade_and_save(app, sub)
    return claimed


def _finalize(app, exam, student_id):
    """Past the deadline, pick the best graded attempt for a student who has not chosen."""
    attempts = _attempts(exam, student_id)
    _finish_expired(app, attempts)
    if (any(a.selected or a.status in ("in_progress", "pending") for a in attempts)
            or not (_window_closed(exam, student_id) or len(attempts) >= _allowance(exam, student_id) == 1)):
        return
    graded = [a for a in attempts if a.status == "graded" and a.review != "cancelled"]
    if graded:
        _select(app, max(graded, key=lambda a: (a.percent, -a.attempt_no)))


def _finalize_exam(app, exam):
    for student_id in {s.student_id for s in exam.submissions}:
        _finalize(app, exam, student_id)


def _finish_if_expired(app, sub):
    if sub.status == "in_progress" and utcnow() > sub.deadline + SUBMIT_GRACE and _claim(sub):
        _grade_and_save(app, sub)


def _finish_expired(app, subs):
    for sub in subs:
        _finish_if_expired(app, sub)


def _grade_and_save(app, sub):
    """Send a submission to the grader. Sync mode saves the result now; async mode leaves it pending
    until AWS calls back. Returns False if the grader could not be reached."""
    # grade against the version the student got, never the live exam
    exam, version = sub.exam, sub.version
    policy = version.settings
    withhold = (policy["managed"] and policy["withhold_if_flagged"] and sub.violations > 0
                and sub.review not in ("released", "cancelled"))
    notify_withheld = withhold and sub.review != "withheld"
    if withhold:
        sub.review = "withheld"
    issue = sub.selected and not withhold and sub.review != "cancelled"
    if issue and sub.certificate is None:
        db.session.add(Certificate(code=secrets.token_hex(5).upper(), exam_id=sub.exam_id, student_id=sub.student_id,
                                   submission=sub))
        db.session.flush()
    payload = {
        "submission_id": sub.id,
        "student": {"name": sub.student.name, "email": sub.student.email},
        "exam": {"id": exam.id, "title": exam.title, "pass_percent": version.pass_percent},
        "questions": [{"id": q.id, "points": q.points, "correct": q.correct} for q in version.questions],
        "answers": sub.answers,
        "issue_certificate": issue,
    }
    if notify_withheld:
        payload["notice"] = "withheld"
    if issue:
        payload["certificate_id"] = sub.certificate.code
        payload["verify_url"] = url_for("verify_certificate", code=sub.certificate.code, _external=True)
    try:
        if grader_client.is_async():
            grader_client.enqueue_submission(payload)
            sub.status = "pending"
            sub.submitted_at = utcnow()  # restarts the "stuck" timer on regrade
            db.session.commit()
            _publish_submission_state(sub, "attempt_submitted")
            return True
        result = grader_client.grade_submission(payload)
    except Exception:
        app.logger.exception("grading failed for submission %s", sub.id)
        sub.status = "error"
        db.session.commit()
        _publish_submission_state(sub, "attempt_submitted")
        return False
    _apply_result(sub, result)
    db.session.commit()
    _publish_submission_state(sub, "attempt_submitted")
    return True


def register_routes(app):
    @app.route("/")
    def index():
        if g.user is None:
            return render_template("home.html")
        return redirect(url_for("teacher_dashboard" if g.user.role == "teacher" else "student_dashboard"))

    # ---------- Teacher ----------
    @app.route("/teacher")
    @login_required("teacher")
    def teacher_dashboard():
        exams = Exam.query.filter_by(teacher_id=g.user.id).order_by(Exam.created_at.desc()).all()
        graded = _counting([s for e in exams for s in e.submissions])
        summary = {
            "exams": len(exams),
            "published": sum(1 for e in exams if e.published),
            "submissions": len(graded),
            "avg": round(statistics.mean(s.percent for s in graded), 1) if graded else 0,
            "pass_rate": round(100 * sum(1 for s in graded if s.passed) / len(graded), 1) if graded else 0,
        }
        return render_template("teacher_dashboard.html", exams=exams, summary=summary,
                               stats={e.id: _exam_stats(e) for e in exams})

    @app.route("/teacher/exams/new", methods=["GET", "POST"])
    @login_required("teacher")
    def exam_new():
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            if not title:
                flash("Exam title is required.", "danger")
                return render_template("exam_form.html")
            visibility = request.form.get("visibility", "private").strip().lower()
            if visibility not in ("private", "public"):
                visibility = "private"
            exam = Exam(
                title=title,
                description=request.form.get("description", "").strip(),
                duration_minutes=max(1, request.form.get("duration_minutes", 15, type=int)),
                pass_percent=min(100, max(0, request.form.get("pass_percent", 50, type=float))),
                visibility=visibility,
                access_code=generate_access_code() if visibility == "private" else None,
                teacher_id=g.user.id,
            )
            db.session.add(exam)
            db.session.commit()
            flash("Exam created. Now add some questions.", "success")
            return redirect(url_for("exam_manage", exam_id=exam.id))
        return render_template("exam_form.html")

    def _assigned_students_payload(exam):
        assigned_emails = {(a.student_email or "").strip().lower() for a in exam.assignments if a.student_email}
        users_by_email = {}
        if assigned_emails:
            for u in User.query.filter(db.func.lower(User.email).in_(assigned_emails)).all():
                if u.email:
                    users_by_email[u.email.strip().lower()] = u
        assigned_list = []
        for a in exam.assignments:
            em = (a.student_email or "").strip().lower()
            u = users_by_email.get(em)
            assigned_list.append({
                "id": a.id,
                "email": em,
                "name": u.name if u else None,
                "has_account": u is not None,
                "delete_url": url_for("exam_assignment_delete", exam_id=exam.id, assignment_id=a.id),
            })
        return assigned_emails, assigned_list

    def _render_exam_manage(exam):
        if exam.ensure_access_code() and db.session.is_modified(exam):
            db.session.commit()
        assigned_emails, assigned_list = _assigned_students_payload(exam)
        return render_template(
            "exam_manage.html",
            exam=exam,
            impact=_edit_impact(exam),
            assigned_emails=assigned_emails,
            assigned_list=assigned_list,
        )

    @app.route("/teacher/exams/<int:exam_id>")
    @login_required("teacher")
    def exam_manage(exam_id):
        exam = _own_exam(exam_id)
        return _render_exam_manage(exam)

    @app.route("/teacher/exams/<int:exam_id>/students/search")
    @login_required("teacher")
    def exam_students_search(exam_id):
        exam = _own_exam(exam_id)
        q = (request.args.get("q") or "").strip().lower()
        if len(q) < 3:
            return jsonify(students=[])
        assigned_emails = {(a.student_email or "").strip().lower() for a in exam.assignments if a.student_email}
        matches = (
            User.query.filter(User.role == "student", User.email.isnot(None), db.func.lower(User.email).contains(q))
            .order_by(User.email)
            .limit(10)
            .all()
        )
        return jsonify(students=[
            {
                "name": u.name,
                "email": u.email.strip().lower(),
                "already": u.email.strip().lower() in assigned_emails,
            }
            for u in matches
        ])

    @app.route("/teacher/exams/<int:exam_id>/visibility", methods=["POST"])
    @login_required("teacher")
    def exam_visibility(exam_id):
        exam = _own_exam(exam_id)
        vis = request.form.get("visibility", "").strip().lower()
        if vis in ("private", "public"):
            exam.visibility = vis
            exam.ensure_access_code()
            db.session.commit()
            flash("Chế độ hiển thị đã cập nhật thành Riêng tư." if vis == "private" else "Chế độ hiển thị đã cập nhật thành Công khai.", "success")
        return redirect(url_for("exam_manage", exam_id=exam.id))

    @app.route("/teacher/exams/<int:exam_id>/access-code", methods=["POST"])
    @login_required("teacher")
    def exam_access_code_regenerate(exam_id):
        exam = _own_exam(exam_id)
        exam.access_code = generate_access_code()
        db.session.commit()
        flash(f"Đã tạo mã tham gia mới: {exam.access_code}.", "success")
        return redirect(url_for("exam_manage", exam_id=exam.id))

    @app.route("/teacher/exams/<int:exam_id>/students", methods=["GET", "POST"], endpoint="exam_students")
    @app.route("/teacher/exams/<int:exam_id>/assignments", methods=["GET", "POST"])
    @login_required("teacher")
    def exam_assignments_add(exam_id):
        exam = _own_exam(exam_id)
        if request.method == "GET":
            return _render_exam_manage(exam)

        candidates = [e.strip().lower() for e in request.form.getlist("student_emails") if e and e.strip()]
        for sid in request.form.getlist("student_ids"):
            if str(sid).isdigit():
                stu = db.session.get(User, int(sid))
                if stu and stu.email:
                    candidates.append(stu.email.strip().lower())

        raw_bulk = "\n".join(
            filter(
                None,
                [
                    request.form.get("bulk_emails", ""),
                    request.form.get("emails", ""),
                    request.form.get("student_email", ""),
                ],
            )
        )
        if raw_bulk.strip():
            for token in re.split(r"[,;\r\n]+", raw_bulk):
                if token and token.strip():
                    candidates.append(token.strip().lower())

        wants_json = request.headers.get("X-Requested-With") == "XMLHttpRequest"

        if not candidates:
            msg = "Vui lòng chọn học sinh hoặc nhập ít nhất 1 email."
            if wants_json:
                _, assigned_list = _assigned_students_payload(exam)
                return jsonify(ok=False, message=msg, category="warning", assigned=assigned_list)
            flash(msg, "warning")
            return redirect(url_for("exam_manage", exam_id=exam.id))

        existing = {(a.student_email or "").strip().lower() for a in exam.assignments}
        added, skipped_dup, invalid = 0, 0, []
        for email in candidates:
            if not EMAIL_RE.match(email):
                invalid.append(email)
                continue
            if email in existing:
                skipped_dup += 1
                continue
            db.session.add(QuizAssignment(quiz_id=exam.id, student_email=email, assigned_by=g.user.id))
            existing.add(email)
            added += 1

        exam.ensure_access_code()
        db.session.commit()

        parts = [f"Đã thêm {added} học sinh"]
        if skipped_dup:
            parts.append(f"bỏ qua {skipped_dup} email đã tồn tại")
        if invalid:
            parts.append(f"bỏ qua {len(invalid)} email không hợp lệ ({', '.join(invalid[:3])})")
        msg = ", ".join(parts) + "."
        cat = "success" if added > 0 else "warning"
        if wants_json:
            db.session.expire(exam, ["assignments"])
            _, assigned_list = _assigned_students_payload(exam)
            return jsonify(ok=added > 0, message=msg, category=cat, assigned=assigned_list)
        flash(msg, cat)
        return redirect(url_for("exam_manage", exam_id=exam.id))

    @app.route("/teacher/exams/<int:exam_id>/students/<int:assignment_id>/delete", methods=["POST"], endpoint="exam_student_delete")
    @app.route("/teacher/exams/<int:exam_id>/assignments/<int:assignment_id>/delete", methods=["POST"])
    @login_required("teacher")
    def exam_assignment_delete(exam_id, assignment_id):
        exam = _own_exam(exam_id)
        assignment = db.get_or_404(QuizAssignment, assignment_id)
        if assignment.quiz_id != exam.id:
            abort(404)
        email = assignment.student_email
        db.session.delete(assignment)
        db.session.commit()
        msg = f"Đã xóa {email} khỏi danh sách thí sinh."
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            db.session.expire(exam, ["assignments"])
            _, assigned_list = _assigned_students_payload(exam)
            return jsonify(ok=True, message=msg, category="success", assigned=assigned_list)
        flash(msg, "success")
        return redirect(url_for("exam_manage", exam_id=exam.id))

    @app.route("/teacher/exams/<int:exam_id>/questions", methods=["POST"])
    @login_required("teacher")
    def question_add(exam_id):
        exam = _own_exam(exam_id)
        raw = request.form.getlist("options")
        kept = [i for i, o in enumerate(raw) if o.strip()]
        options = [raw[i].strip() for i in kept]
        # Re-index correct answers because blank option boxes are dropped.
        chosen = {int(i) for i in request.form.getlist("correct") if i.isdigit()}
        correct = sorted(kept.index(i) for i in chosen if i in kept)
        text = request.form.get("text", "").strip()
        if not text or len(options) < 2 or not correct:
            flash("A question needs text, at least 2 options and at least 1 correct answer (on a filled-in option).", "danger")
        else:
            image_url = None
            image_file = request.files.get("image")
            if image_file and image_file.filename:
                try:
                    image_url = storage_client.upload_question_image(image_file)
                except ValueError as exc:
                    flash(str(exc), "danger")
                    return redirect(url_for("exam_manage", exam_id=exam.id))
                except Exception:
                    app.logger.exception("failed to upload question image")
                    flash("Could not upload the question image. Please check storage settings.", "danger")
                    return redirect(url_for("exam_manage", exam_id=exam.id))
            q = Question(exam=exam, text=text, options=options, correct=correct,
                         points=max(0.0, request.form.get("points", 1, type=float)),
                         image_url=image_url)
            db.session.add(q)
            db.session.flush()  # need q.id before snapshotting
            exam.new_version([x.id for x in exam.questions] + [q.id])
            db.session.commit()
            flash("Question added.", "success")
        return redirect(url_for("exam_manage", exam_id=exam.id))

    @app.route("/teacher/exams/<int:exam_id>/generate-ai", methods=["POST"])
    @login_required("teacher")
    def question_generate_ai(exam_id):
        exam = _own_exam(exam_id)
        lesson_text = request.form.get("lesson_text", "").strip()
        lesson_file = request.files.get("lesson_file")
        num_questions = request.form.get("num_questions", 5, type=int)

        if lesson_file and getattr(lesson_file, "filename", ""):
            try:
                doc_text = ai_generator.extract_text_from_upload(lesson_file)
            except ValueError as exc:  # our own validation messages, safe to show
                flash(f"Could not read document: {exc}", "danger")
                return redirect(url_for("exam_manage", exam_id=exam.id))
            except Exception:
                app.logger.exception("failed to parse lesson document")
                flash("Could not read document. The file may be corrupted or password-protected.", "danger")
                return redirect(url_for("exam_manage", exam_id=exam.id))
            lesson_text = f"{lesson_text}\n\n{doc_text}".strip() if lesson_text else doc_text

        if not lesson_text:
            flash("Please paste lesson content or upload a document (.pdf, .docx, .txt).", "danger")
            return redirect(url_for("exam_manage", exam_id=exam.id))
        try:
            generated = ai_generator.generate_mcqs_from_text(lesson_text, num_questions=num_questions)
        except Exception:
            # SDK errors can carry the endpoint and deployment name, so they stay in the log.
            app.logger.exception("AI question generation failed")
            flash("Failed to generate questions with AI. Please try again later.", "danger")
            return redirect(url_for("exam_manage", exam_id=exam.id))

        added = []
        for item in generated:
            try:
                options, correct = _parse_lettered(item)
                q_text = str(item.get("question", "")).strip()
                if not q_text or len(options) < 2:
                    continue
                points = max(0.0, float(item.get("points") or 1))
                added.append(Question(exam=exam, text=q_text, options=options, correct=correct, points=points))
            except (ValueError, TypeError):
                continue

        if added:
            db.session.add_all(added)
            db.session.flush()
            exam.new_version([x.id for x in exam.questions] + [q.id for q in added])
            db.session.commit()
            if ai_generator.is_configured():
                flash(f"Generated and added {len(added)} question(s) with Azure AI.", "success")
            else:
                flash(f"Azure OpenAI is not configured: added {len(added)} placeholder demo question(s).", "warning")
        else:
            flash("AI did not return any valid questions. Please try again with clearer lesson text.", "warning")
        return redirect(url_for("exam_manage", exam_id=exam.id))

    @app.route("/teacher/exams/<int:exam_id>/import", methods=["POST"])
    @login_required("teacher")
    def question_import(exam_id):
        """CSV columns: question, A, B, C, D, correct (e.g. 'A' or 'A;C'), points (optional)."""
        exam = _own_exam(exam_id)
        file = request.files.get("file")
        if not file:
            flash("Please choose a CSV file.", "danger")
            return redirect(url_for("exam_manage", exam_id=exam.id))
        reader = csv.DictReader(io.StringIO(file.read().decode("utf-8-sig")))
        added, errors = [], []
        for line, row in enumerate(reader, start=2):
            try:
                if not row.get("question", "").strip() or sum(1 for k in "ABCD" if (row.get(k) or "").strip()) < 2:
                    raise ValueError("missing question text or fewer than 2 options")
                options, correct = _parse_lettered(row)
                added.append(Question(exam=exam, text=row["question"].strip(), options=options, correct=correct,
                                      points=float(row.get("points") or 1)))
            except (ValueError, KeyError) as exc:
                errors.append(f"line {line}: {exc}")
        # whole import = one version
        if added:
            db.session.add_all(added)
            db.session.flush()
            exam.new_version([x.id for x in exam.questions] + [q.id for q in added])
        db.session.commit()
        flash(f"Imported {len(added)} question(s).", "success" if added else "warning")
        for e in errors[:10]:
            flash(e, "danger")
        return redirect(url_for("exam_manage", exam_id=exam.id))

    @app.route("/teacher/exams/<int:exam_id>/questions/<int:qid>/delete", methods=["POST"])
    @login_required("teacher")
    def question_delete(exam_id, qid):
        exam = _own_exam(exam_id)
        ids = [x.id for x in exam.questions]
        if qid not in ids:
            abort(404)
        # row stays, older versions may still point to it
        exam.new_version([i for i in ids if i != qid])
        db.session.commit()
        return redirect(url_for("exam_manage", exam_id=exam.id))

    @app.route("/teacher/exams/<int:exam_id>/settings", methods=["POST"])
    @login_required("teacher")
    def exam_settings(exam_id):
        exam = _own_exam(exam_id)
        f = request.form
        exam.duration_minutes = max(1, f.get("duration_minutes", exam.duration_minutes, type=int))
        exam.pass_percent = min(100, max(0, f.get("pass_percent", exam.pass_percent, type=float)))
        max_attempts = max(1, f.get("max_attempts", exam.max_attempts, type=int))
        deadline = f.get("selection_deadline", "").strip()
        try:
            deadline = datetime.fromisoformat(deadline) if deadline else None
        except ValueError:
            deadline = None
        if max_attempts > 1 and deadline is None:
            flash("Exams with several attempts need a deadline for choosing the attempt that counts.", "danger")
            return redirect(url_for("exam_manage", exam_id=exam.id))
        exam.max_attempts, exam.selection_deadline = max_attempts, deadline
        if "visibility" in f:
            vis = f.get("visibility", "").strip().lower()
            if vis in ("private", "public"):
                exam.visibility = vis
        exam.ensure_access_code()
        policy = {k: k in f for k, v in DEFAULT_POLICY.items() if isinstance(v, bool)}
        limit = f.get("autosubmit_after", type=int)
        policy["autosubmit_after"] = max(1, limit) if "autosubmit" in f and limit else None
        exam.policy = policy
        if exam.versions:
            exam.new_version(exam.current_version.question_ids)
        db.session.commit()
        flash("Settings saved.", "success")
        return redirect(url_for("exam_manage", exam_id=exam.id))

    @app.route("/teacher/exams/<int:exam_id>/versions/<int:version_id>/restore", methods=["POST"])
    @login_required("teacher")
    def version_restore(exam_id, version_id):
        exam = _own_exam(exam_id)
        version = db.get_or_404(ExamVersion, version_id)
        if version.exam_id != exam.id:
            abort(404)
        exam.current_version = version  # ptr swap, nothing else changes
        db.session.commit()
        flash(f"Restored version {exam.versions.index(version) + 1}.", "success")
        return redirect(url_for("exam_manage", exam_id=exam.id))

    @app.route("/teacher/exams/<int:exam_id>/publish", methods=["POST"])
    @login_required("teacher")
    def exam_publish(exam_id):
        exam = _own_exam(exam_id)
        if not exam.published and not exam.questions:
            flash("Add at least 1 question before publishing the exam.", "danger")
        else:
            exam.published = not exam.published
            db.session.commit()
            flash("Exam published to students." if exam.published else "Exam closed.", "success")
        return redirect(url_for("exam_manage", exam_id=exam.id))

    @app.route("/teacher/exams/<int:exam_id>/delete", methods=["POST"])
    @login_required("teacher")
    def exam_delete(exam_id):
        db.session.delete(_own_exam(exam_id))
        db.session.commit()
        flash("Exam deleted.", "success")
        return redirect(url_for("teacher_dashboard"))

    def _build_monitoring_rows(exam, tickets):
        now = utcnow()
        version_no = {v.id: i + 1 for i, v in enumerate(exam.versions)}
        subs_sorted = sorted(exam.submissions, key=lambda s: (s.student.name, s.attempt_no))
        initial_fn = app.jinja_env.filters["initial"]
        attempts = []

        for s in subs_sorted:
            if s.status == "in_progress":
                total_q = len(s.version.question_ids) if s.version else 0
                answered_q = _answered_count(s)
                seen_ago = int((now - s.last_seen_at).total_seconds()) if s.last_seen_at else None
                remaining = max(0, int((s.deadline - now).total_seconds()))
                last_dt = s.last_seen_at or s.started_at
                attempts.append({
                    "id": s.id,
                    "attempt_no": s.attempt_no,
                    "name": s.student.name,
                    "email": s.student.email,
                    "version": version_no.get(s.version_id),
                    "managed": s.version.settings["managed"],
                    "violations": s.violations,
                    "locked": s.locked_at is not None,
                    "lock_reason": s.lock_reason,
                    "seen_ago": seen_ago,
                    "remaining": remaining,
                    "answered_count": answered_q,
                    "total_questions": total_q,
                    "updated_at": last_dt.strftime("%H:%M:%S"),
                })

        def _sub_row(s, is_last):
            total_q = len(s.version.question_ids) if s.version else 0
            answered_q = _answered_count(s)
            last_dt = (s.last_seen_at or s.started_at) if s.status == "in_progress" else (s.submitted_at or s.started_at)
            updated_display = (
                last_dt.strftime("%H:%M:%S")
                if s.status == "in_progress"
                else last_dt.strftime("%b %d, %Y %H:%M")
            )
            return {
                "id": s.id,
                "student_id": s.student_id,
                "name": s.student.name,
                "initial": initial_fn(s.student.name),
                "email": s.student.email,
                "has_account": True,
                "attempt_no": s.attempt_no,
                "selected": s.selected,
                "status": s.status,
                "score": s.score,
                "max_score": s.max_score,
                "percent": s.percent,
                "passed": s.passed,
                "violations": s.violations,
                "managed": s.version.settings["managed"],
                "review": s.review,
                "answered_count": answered_q,
                "total_questions": total_q,
                "submitted_at": s.submitted_at.strftime("%b %d, %Y %H:%M") if s.submitted_at else "",
                "updated_at": updated_display,
                "_sort_ts": last_dt.timestamp() if last_dt else 0,
                "details_url": url_for("submission_view", sub_id=s.id),
                "retake_url": url_for("ticket_grant", exam_id=exam.id, student_id=s.student_id),
                "has_ticket": s.student_id in tickets,
                "is_last_for_student": is_last,
            }

        submissions_data = []
        if (exam.visibility or "private") == "public":
            for idx, s in enumerate(subs_sorted):
                is_last = (idx == len(subs_sorted) - 1) or (subs_sorted[idx + 1].student_id != s.student_id)
                submissions_data.append(_sub_row(s, is_last))
        else:
            subs_by_email = {}
            for s in sorted(exam.submissions, key=lambda x: x.attempt_no):
                em = (s.student.email or "").strip().lower() if s.student else ""
                subs_by_email.setdefault(em, []).append(s)
            users_by_email = {(u.email or "").strip().lower(): u for u in User.query.all() if u.email}
            seen_emails = set()
            total_q_default = len(exam.questions)

            for a in exam.assignments:
                em = (a.student_email or "").strip().lower()
                if not em or em in seen_emails:
                    continue
                seen_emails.add(em)
                student_subs = subs_by_email.get(em, [])
                if student_subs:
                    for i, s in enumerate(student_subs):
                        submissions_data.append(_sub_row(s, i == len(student_subs) - 1))
                else:
                    u = users_by_email.get(em)
                    display_name = u.name if u else em.split("@")[0]
                    submissions_data.append({
                        "id": None,
                        "student_id": u.id if u else None,
                        "name": display_name,
                        "initial": initial_fn(u.name if u else em),
                        "email": em,
                        "has_account": u is not None,
                        "attempt_no": None,
                        "selected": False,
                        "status": "not_started",
                        "score": None,
                        "max_score": None,
                        "percent": None,
                        "passed": None,
                        "violations": 0,
                        "managed": exam.settings["managed"],
                        "review": None,
                        "answered_count": 0,
                        "total_questions": total_q_default,
                        "submitted_at": "",
                        "updated_at": "—",
                        "details_url": None,
                        "retake_url": None,
                        "has_ticket": False,
                        "is_last_for_student": False,
                    })

            extra_subs = [
                s
                for s in subs_sorted
                if ((s.student.email or "").strip().lower() if s.student else "") not in seen_emails
            ]
            for idx, s in enumerate(extra_subs):
                is_last = (idx == len(extra_subs) - 1) or (extra_subs[idx + 1].student_id != s.student_id)
                submissions_data.append(_sub_row(s, is_last))

        submissions_data.sort(key=lambda r: (1 if r["status"] == "not_started" else 0, -r.pop("_sort_ts", 0)))
        return attempts, submissions_data

    @app.route("/teacher/exams/<int:exam_id>/results")
    @login_required("teacher")
    def exam_results(exam_id):
        exam = _own_exam(exam_id)
        _finalize_exam(app, exam)
        tickets = {t.student_id: t for t in exam.tickets if t.is_open}
        _, rows = _build_monitoring_rows(exam, tickets)
        return render_template("exam_results.html", exam=exam, submissions=rows, stats=_exam_stats(exam),
                               tickets=tickets)

    @app.route("/teacher/exams/<int:exam_id>/results.csv")
    @login_required("teacher")
    def exam_results_csv(exam_id):
        exam = _own_exam(exam_id)
        _finalize_exam(app, exam)
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["Full name", "Email", "Attempt", "Counts", "Score", "Max score", "Percent", "Result", "Submitted at (UTC)", "Certificate ID",
                    "Violations", "Review"])
        for s in sorted(exam.submissions, key=lambda s: s.submitted_at):
            if s.status == "in_progress":
                continue
            w.writerow([s.student.name, s.student.email, s.attempt_no, "yes" if s.selected else "", s.score, s.max_score, s.percent,
                        "Passed" if s.passed else "Failed", s.submitted_at.strftime("%Y-%m-%d %H:%M"),
                        s.certificate.code if s.certificate else "", s.violations, s.review or ""])
        # BOM so Excel opens Vietnamese text correctly.
        return Response("\ufeff" + buf.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition": f"attachment; filename=ket-qua-exam-{exam.id}.csv"})

    @app.route("/teacher/exams/<int:exam_id>/report")
    @login_required("teacher")
    def exam_report(exam_id):
        exam = _own_exam(exam_id)
        _finalize_exam(app, exam)
        return render_template("exam_report.html", exam=exam, stats=_exam_stats(exam),
                               qstats=_question_stats(exam),
                               submissions=sorted(_counting(exam.submissions), key=lambda s: -(s.percent or 0)))

    # ---------- Student ----------
    @app.route("/student")
    @login_required("student")
    def student_dashboard():
        student_email = (g.user.email or "").strip().lower()
        assigned_ids = {
            a.quiz_id for a in QuizAssignment.query.filter_by(student_email=student_email).all()
        } if student_email else set()
        all_published = Exam.query.filter_by(published=True).order_by(Exam.created_at.desc()).all()
        exams = [e for e in all_published if (e.visibility or "private") == "public" or e.id in assigned_ids]
        assigned_exams = [e for e in exams if e.id in assigned_ids]
        public_exams = [e for e in exams if (e.visibility or "private") == "public"]
        for exam_id in {s.exam_id for s in Submission.query.filter_by(student_id=g.user.id)}:
            _finalize(app, db.session.get(Exam, exam_id), g.user.id)
        by_exam = {}
        for s in Submission.query.filter_by(student_id=g.user.id).order_by(Submission.attempt_no):
            by_exam.setdefault(s.exam_id, []).append(s)
        # The attempt shown on each card: the running one, else the selected one, else the latest.
        mine = {eid: next((a for a in subs if a.status == "in_progress"), None)
                or next((a for a in subs if a.selected), None) or subs[-1] for eid, subs in by_exam.items()}
        tickets = {t.exam_id: t for t in RetakeTicket.query.filter_by(student_id=g.user.id, claimed_at=None)
                   if t.is_open}
        return render_template("student_dashboard.html", exams=exams, assigned_exams=assigned_exams,
                               public_exams=public_exams, assigned_ids=assigned_ids,
                               mine=mine, attempts=by_exam, tickets=tickets)

    @app.route("/student/join", methods=["POST"], endpoint="student_join_exam")
    @app.route("/student/join-code", methods=["POST"])
    @login_required("student")
    def student_join_code():
        code = request.form.get("access_code", "").strip().upper()
        student_email = (g.user.email or "").strip().lower()
        if not code:
            flash("Vui lòng nhập mã bài thi.", "danger")
            return redirect(url_for("student_dashboard"))
        exam = Exam.query.filter_by(access_code=code, visibility="private").first()
        if not exam or not exam.published:
            flash("Mã bài thi không hợp lệ hoặc bài thi chưa được mở.", "danger")
            return redirect(url_for("student_dashboard"))
        if not student_email:
            flash("Tài khoản của bạn chưa có email hợp lệ để tham gia bài thi.", "danger")
            return redirect(url_for("student_dashboard"))
        existing = QuizAssignment.query.filter_by(quiz_id=exam.id, student_email=student_email).first()
        if existing:
            flash(f"Bạn đã có quyền truy cập bài thi '{exam.title}'.", "info")
        else:
            db.session.add(QuizAssignment(quiz_id=exam.id, student_email=student_email, assigned_by=None))
            db.session.commit()
            flash(f"Đã mở quyền truy cập bài thi: {exam.title}.", "success")
        return redirect(url_for("student_dashboard"))

    @app.route("/exam/<int:exam_id>", methods=["GET", "POST"], endpoint="take_exam_short")
    @app.route("/student/exams/<int:exam_id>", methods=["GET", "POST"])
    @login_required("student")
    def take_exam(exam_id):
        exam = db.get_or_404(Exam, exam_id)
        if (exam.visibility or "private") == "private" and not is_student_assigned(g.user, exam):
            abort(403)
        if not exam.published:
            abort(404)
        if not can_access_quiz(g.user, exam):
            abort(403)
        attempts = _attempts(exam, g.user.id)
        _finish_expired(app, attempts)
        sub = next((a for a in attempts if a.status == "in_progress"), None)
        if sub is None:
            # Only the very first attempt starts straight from the exam link; later ones go through the
            # attempts page so a stray click cannot burn an attempt.
            if attempts or not _can_start(exam, attempts) or request.method != "GET":
                if len(attempts) == 1 and exam.max_attempts == 1:
                    return redirect(url_for("submission_view", sub_id=attempts[0].id))
                return redirect(url_for("exam_attempts", exam_id=exam.id))
            sub = _start_attempt(exam, g.user.id, attempts)
            if sub is None:
                return redirect(url_for("take_exam", exam_id=exam.id))
        if request.method == "GET":
            policy = sub.version.settings
            if policy["managed"]:
                # Opening the exam page again (reload, new tab, other device) while in progress is a re-entry.
                if sub.last_seen_at is not None:
                    _record(app, sub, "reentry", request.user_agent.string[:300], violation=True)
                    if sub.status != "in_progress":
                        return redirect(url_for("submission_view", sub_id=sub.id))
                sub.last_seen_at = utcnow()
                db.session.commit()
            # render the server side time on the web
            remaining = max(0, int((sub.deadline - utcnow()).total_seconds()))
            return render_template("take_exam.html", exam=exam, sub=sub, policy=policy,
                                   questions=sub.version.questions, remaining=remaining)

        answers = {str(q.id): [int(v) for v in request.form.getlist(f"q{q.id}") if v.isdigit()]
                   for q in sub.version.questions}
        if _claim(sub, answers=answers) and not _grade_and_save(app, sub):
            flash("Your answers were saved but grading failed. Click 'Regrade' or contact your teacher.", "danger")
        return redirect(url_for("submission_view", sub_id=sub.id))

    @app.route("/student/exams/<int:exam_id>/attempts")
    @login_required("student")
    def exam_attempts(exam_id):
        exam = db.get_or_404(Exam, exam_id)
        if (exam.visibility or "private") == "private" and not is_student_assigned(g.user, exam):
            abort(403)
        _finalize(app, exam, g.user.id)
        attempts = _attempts(exam, g.user.id)
        if not exam.published and not attempts:
            abort(404)
        return render_template("exam_attempts.html", exam=exam, attempts=attempts,
                               allowance=_allowance(exam, g.user.id),
                               can_start=exam.published and can_access_quiz(g.user, exam) and _can_start(exam, attempts),
                               window_closed=_window_closed(exam, g.user.id),
                               ticket=_open_ticket(exam, g.user.id))

    @app.route("/student/exams/<int:exam_id>/start", methods=["POST"])
    @login_required("student")
    def exam_start(exam_id):
        exam = db.get_or_404(Exam, exam_id)
        if (exam.visibility or "private") == "private" and not is_student_assigned(g.user, exam):
            abort(403)
        if not exam.published:
            abort(404)
        if not can_access_quiz(g.user, exam):
            abort(403)
        attempts = _attempts(exam, g.user.id)
        _finish_expired(app, attempts)
        if any(a.status == "in_progress" for a in attempts):
            return redirect(url_for("take_exam", exam_id=exam.id))
        if not _can_start(exam, attempts):
            flash("No attempts left for this exam.", "danger")
            return redirect(url_for("exam_attempts", exam_id=exam.id))
        _start_attempt(exam, g.user.id, attempts)
        return redirect(url_for("take_exam", exam_id=exam.id))

    @app.route("/student/attempts/<int:sub_id>/select", methods=["POST"])
    @login_required("student")
    def attempt_select(sub_id):
        sub = db.get_or_404(Submission, sub_id)
        if sub.student_id != g.user.id or not can_access_quiz(g.user, sub.exam):
            abort(403)
        if sub.status != "graded" or sub.review == "cancelled" or not _select(app, sub):
            flash("This attempt cannot be selected.", "danger")
        else:
            flash(f"Attempt {sub.attempt_no} selected. This exam is now final.", "success")
        return redirect(url_for("exam_attempts", exam_id=sub.exam_id))

    @app.route("/student/tickets/<int:ticket_id>/claim", methods=["POST"])
    @login_required("student")
    def ticket_claim(ticket_id):
        ticket = db.get_or_404(RetakeTicket, ticket_id)
        exam = ticket.exam
        if ticket.student_id != g.user.id or (exam.published and not can_access_quiz(g.user, exam)):
            abort(403)
        attempts = _attempts(exam, g.user.id)
        _finish_expired(app, attempts)
        if not exam.published or any(a.status in ("in_progress", "pending") for a in attempts):
            flash("This retake cannot be claimed right now.", "danger")
            return redirect(url_for("student_dashboard"))
        now = utcnow()
        claimed = db.session.execute(
            update(RetakeTicket).where(RetakeTicket.id == ticket.id, RetakeTicket.claimed_at.is_(None),
                                       (RetakeTicket.expires_at.is_(None)) | (RetakeTicket.expires_at > now))
            .values(claimed_at=now)
        ).rowcount == 1
        if not claimed:
            db.session.rollback()
            flash("This retake has expired or was already used.", "danger")
            return redirect(url_for("student_dashboard"))
        # As if the student never took the exam: the attempts go, the certificate record stays as invalidated.
        invalidated = 0
        for cert in Certificate.query.filter_by(exam_id=exam.id, student_id=g.user.id):
            if cert.status in ("valid", "issuing"):
                cert.status, cert.status_changed_at = "invalidated", now
                invalidated += 1
        for a in attempts:
            db.session.delete(a)
        db.session.commit()
        if invalidated:
            try:
                grader_client.notify({"kind": "invalidated", "student": {"name": g.user.name, "email": g.user.email},
                                      "exam": {"id": exam.id, "title": exam.title}})
            except Exception:
                app.logger.exception("invalidation notice failed for ticket %s", ticket.id)
        _start_attempt(exam, g.user.id, [])
        return redirect(url_for("take_exam", exam_id=exam.id))

    @app.route("/submissions/<int:sub_id>")
    @login_required()
    def submission_view(sub_id):
        sub = db.get_or_404(Submission, sub_id)
        if g.user.id != sub.student_id and not is_quiz_owner(g.user, sub.exam):
            abort(403)
        _finalize(app, sub.exam, sub.student_id)
        if sub.status == "in_progress" and g.user.id == sub.student_id:
            return redirect(url_for("take_exam", exam_id=sub.exam_id))
        cert_url = None
        cert = sub.certificate
        if cert and cert.status == "valid" and cert.s3_key and not sub.result_hidden:
            try:
                cert_url = grader_client.certificate_url(cert.s3_key)
            except Exception:
                app.logger.exception("presign failed")
        details = {d["question_id"]: d for d in (sub.details or [])}
        return render_template("submission.html", sub=sub, exam=sub.exam, questions=sub.version.questions,
                               revoke_reasons=REVOKE_REASONS,
                               details=details, cert_url=cert_url, is_teacher=is_quiz_owner(g.user, sub.exam),
                               stuck=_is_stuck(sub))

    @app.route("/submissions/<int:sub_id>/status")
    @login_required()
    def submission_status(sub_id):
        sub = db.get_or_404(Submission, sub_id)
        if g.user.id != sub.student_id and not is_quiz_owner(g.user, sub.exam):
            abort(403)
        return jsonify(status=sub.status, stuck=_is_stuck(sub))

    def _own_attempt(sub_id):
        sub = db.get_or_404(Submission, sub_id)
        if sub.student_id != g.user.id or not can_access_quiz(g.user, sub.exam):
            abort(403)
        _finish_if_expired(app, sub)
        return sub

    @app.route("/submissions/<int:sub_id>/heartbeat", methods=["POST"])
    @login_required("student")
    def attempt_heartbeat(sub_id):
        sub = _own_attempt(sub_id)
        if sub.status == "in_progress" and sub.version.settings["managed"]:
            now = utcnow()
            if sub.last_seen_at and now - sub.last_seen_at > HEARTBEAT_GAP:
                gap = int((now - sub.last_seen_at).total_seconds())
                _record(app, sub, "heartbeat_gap", f"no heartbeat for {gap}s", violation=True)
            sub.last_seen_at = now
            db.session.commit()
        return jsonify(_attempt_state(sub))

    @app.route("/submissions/<int:sub_id>/progress", methods=["POST"])
    @login_required("student")
    def attempt_progress(sub_id):
        sub = _own_attempt(sub_id)
        if sub.status == "in_progress":
            answers = {
                str(q.id): [int(v) for v in request.form.getlist(f"q{q.id}") if v.isdigit()]
                for q in sub.version.questions
            }
            sub.answers = answers
            sub.last_seen_at = utcnow()
            db.session.commit()
            _publish_submission_state(sub, "progress_updated")
        return jsonify({
            **_attempt_state(sub),
            "answered_count": _answered_count(sub),
            "total_questions": len(sub.version.question_ids) if sub.version else 0,
        })

    @app.route("/submissions/<int:sub_id>/events", methods=["POST"])
    @login_required("student")
    def attempt_event(sub_id):
        sub = _own_attempt(sub_id)
        kind = request.form.get("type", "")
        if kind not in CLIENT_EVENTS:
            abort(400)
        _record(app, sub, kind, request.form.get("detail", "")[:300] or None, violation=CLIENT_EVENTS[kind])
        return jsonify(_attempt_state(sub))

    @app.route("/api/exams/<int:exam_id>/pubsub-token")
    @login_required()
    def exam_pubsub_token(exam_id):
        exam = db.get_or_404(Exam, exam_id)
        if g.user.role in ("teacher", "admin"):
            if not is_quiz_owner(g.user, exam):
                abort(403)
        elif not can_access_quiz(g.user, exam):
            abort(403)
        return jsonify(pubsub_client.get_client_access_url(exam.id, user_id=g.user.id))

    # ---------- Teacher: managed-mode controls ----------
    def _teacher_attempt(sub_id):
        sub = db.get_or_404(Submission, sub_id)
        if not is_quiz_owner(g.user, sub.exam):
            abort(403)
        return sub

    @app.route("/teacher/exams/<int:exam_id>/live.json")
    @login_required("teacher")
    def exam_live(exam_id):
        exam = _own_exam(exam_id)
        _finalize_exam(app, exam)
        tickets = {t.student_id: t for t in exam.tickets if t.is_open}
        attempts, submissions_data = _build_monitoring_rows(exam, tickets)
        sub_ids = [s.id for s in exam.submissions]
        events = (AttemptEvent.query.filter(AttemptEvent.submission_id.in_(sub_ids))
                  .order_by(AttemptEvent.id.desc()).limit(30).all()) if sub_ids else []
        return jsonify(
            attempts=attempts,
            submissions=submissions_data,
            stats=_exam_stats(exam),
            events=[{
                "id": e.id,
                "submission_id": e.submission_id,
                "student": e.submission.student.name,
                "type": e.type,
                "detail": e.detail,
                "counted": e.counted,
                "violations": e.submission.violations,
                "at": e.at.strftime("%H:%M:%S"),
            } for e in events],
        )

    def _exam_student(exam_id, student_id):
        exam = _own_exam(exam_id)
        student = db.get_or_404(User, student_id)
        attempts = _attempts(exam, student.id)
        if not attempts:
            abort(404)
        return exam, student, attempts

    @app.route("/teacher/exams/<int:exam_id>/students/<int:student_id>/attempts.json")
    @login_required("teacher")
    def attempts_export(exam_id, student_id):
        """Everything a retake will erase, for the teacher to keep."""
        exam, student, attempts = _exam_student(exam_id, student_id)
        data = {
            "exported_at": utcnow().isoformat() + "Z",
            "exam": {"id": exam.id, "title": exam.title, "max_attempts": exam.max_attempts},
            "student": {"id": student.id, "name": student.name, "email": student.email},
            "attempts": [{
                "attempt_no": a.attempt_no, "status": a.status, "selected": a.selected, "review": a.review,
                "started_at": a.started_at.isoformat() + "Z", "submitted_at": a.submitted_at.isoformat() + "Z",
                "score": a.score, "max_score": a.max_score, "percent": a.percent, "passed": a.passed,
                "pass_percent": a.version.pass_percent, "policy": a.version.settings,
                "questions": [{"id": q.id, "text": q.text, "options": q.options, "correct": q.correct,
                               "points": q.points} for q in a.version.questions],
                "answers": a.answers, "details": a.details, "violations": a.violations,
                "events": [{"type": e.type, "detail": e.detail, "counted": e.counted, "at": e.at.isoformat() + "Z"}
                           for e in a.events],
                "certificate": {"code": a.certificate.code, "status": a.certificate.status} if a.certificate else None,
            } for a in attempts],
        }
        return Response(json.dumps(data, ensure_ascii=False, indent=2), mimetype="application/json", headers={
            "Content-Disposition": f"attachment; filename=exam-{exam.id}-student-{student.id}-attempts.json"})

    @app.route("/teacher/exams/<int:exam_id>/students/<int:student_id>/retake", methods=["GET", "POST"])
    @login_required("teacher")
    def ticket_grant(exam_id, student_id):
        exam, student, attempts = _exam_student(exam_id, student_id)
        open_ticket = _open_ticket(exam, student.id)
        if request.method == "GET":
            return render_template("retake_grant.html", exam=exam, student=student, attempts=attempts,
                                   open_ticket=open_ticket)
        if open_ticket:
            flash("This student already has an open retake.", "warning")
        elif "understand" not in request.form:
            flash("Confirm that you understand what claiming a retake erases.", "danger")
            return redirect(url_for("ticket_grant", exam_id=exam.id, student_id=student.id))
        elif any(a.status == "in_progress" for a in attempts):
            flash("The student has an attempt in progress; grant the retake after it ends.", "danger")
        else:
            expires = request.form.get("expires_at", "").strip()
            try:
                expires = datetime.fromisoformat(expires) if expires else None
            except ValueError:
                expires = None
            db.session.add(RetakeTicket(exam_id=exam.id, student_id=student.id, granted_by_id=g.user.id,
                                        expires_at=expires, full=request.form.get("scope") == "full"))
            db.session.commit()
            try:
                grader_client.notify({"kind": "retake_granted",
                                      "student": {"name": student.name, "email": student.email},
                                      "exam": {"id": exam.id, "title": exam.title}})
            except Exception:
                app.logger.exception("retake notice failed for exam %s student %s", exam.id, student.id)
            flash(f"Retake granted to {student.name}.", "success")
        return redirect(url_for("exam_results", exam_id=exam.id))

    @app.route("/teacher/tickets/<int:ticket_id>/withdraw", methods=["POST"])
    @login_required("teacher")
    def ticket_withdraw(ticket_id):
        ticket = db.get_or_404(RetakeTicket, ticket_id)
        _own_exam(ticket.exam_id)
        if ticket.claimed_at is None:
            db.session.delete(ticket)
            db.session.commit()
            flash("Retake withdrawn.", "success")
        return redirect(url_for("exam_results", exam_id=ticket.exam_id))

    @app.route("/teacher/submissions/<int:sub_id>/approve", methods=["POST"])
    @login_required("teacher")
    def attempt_approve(sub_id):
        sub = _teacher_attempt(sub_id)
        if sub.status == "in_progress" and sub.locked_at:
            sub.locked_at = None
            # The student was waiting, not gone: do not count that silence as a heartbeat gap.
            sub.last_seen_at = utcnow()
            _log(sub, "approved", f"by {g.user.name}")
            db.session.commit()
            _publish_submission_state(sub, "attempt_approved")
        return jsonify(_attempt_state(sub))

    @app.route("/teacher/submissions/<int:sub_id>/force-submit", methods=["POST"])
    @login_required("teacher")
    def attempt_force_submit(sub_id):
        sub = _teacher_attempt(sub_id)
        if _claim(sub):
            _log(sub, "force_submitted", f"by {g.user.name}")
            db.session.commit()
            _grade_and_save(app, sub)
        return jsonify(_attempt_state(sub))

    @app.route("/teacher/submissions/<int:sub_id>/release", methods=["POST"])
    @login_required("teacher")
    def attempt_release(sub_id):
        sub = _teacher_attempt(sub_id)
        if sub.review != "withheld":
            abort(409)
        sub.review = "released"
        _log(sub, "released", f"by {g.user.name}")
        db.session.commit()
        # Grading again issues the certificate and the normal result email; the pinned version keeps the score.
        if not _grade_and_save(app, sub):
            flash("Released, but issuing the certificate failed. Use 'Regrade' to retry.", "danger")
        else:
            flash("Result released to the student.", "success")
        return redirect(url_for("submission_view", sub_id=sub.id))

    @app.route("/teacher/submissions/<int:sub_id>/revoke", methods=["POST"])
    @login_required("teacher")
    def certificate_revoke(sub_id):
        sub = _teacher_attempt(sub_id)
        cert = sub.certificate
        preset = REVOKE_REASONS.get(request.form.get("reason", ""))
        note = request.form.get("note", "").strip()[:300]
        if cert is None or cert.status != "valid":
            abort(409)
        if preset is None or (request.form.get("reason") == "other" and not note):
            flash("Choose a reason (and describe it when choosing 'Other').", "danger")
            return redirect(url_for("submission_view", sub_id=sub.id))
        label, message = preset
        reason = note if request.form.get("reason") == "other" else label + (f": {note}" if note else "")
        # Permanent, and the attempt is voided like a cancelled withheld result.
        cert.status, cert.status_changed_at, cert.revoked_reason = "revoked", utcnow(), reason
        sub.review = "revoked"
        _log(sub, "revoked", f"by {g.user.name}: {reason}")
        db.session.commit()
        try:
            grader_client.notify({"kind": "revoked", "reason": reason, "message": message,
                                  "student": {"name": sub.student.name, "email": sub.student.email},
                                  "exam": {"id": sub.exam.id, "title": sub.exam.title}})
        except Exception:
            app.logger.exception("revocation notice failed for submission %s", sub.id)
        flash("Certificate revoked; the student has been notified.", "success")
        return redirect(url_for("submission_view", sub_id=sub.id))

    @app.route("/teacher/submissions/<int:sub_id>/cancel", methods=["POST"])
    @login_required("teacher")
    def attempt_cancel(sub_id):
        sub = _teacher_attempt(sub_id)
        if sub.review != "withheld":
            abort(409)
        sub.review = "cancelled"
        _log(sub, "cancelled", f"by {g.user.name}")
        db.session.commit()
        try:
            grader_client.notify({"kind": "cancelled", "submission_id": sub.id,
                                  "student": {"name": sub.student.name, "email": sub.student.email},
                                  "exam": {"id": sub.exam.id, "title": sub.exam.title}})
        except Exception:
            app.logger.exception("cancel notification failed for submission %s", sub.id)
        flash("Certificate cancelled; the student has been notified.", "success")
        return redirect(url_for("submission_view", sub_id=sub.id))

    @app.route("/api/grader/callback", methods=["POST"])
    def grader_callback():
        """Called by the AWS Lambda worker after grading a queued submission."""
        secret = app.config["GRADER_SECRET"]
        if not secret or not secrets.compare_digest(request.headers.get("x-grader-secret", ""), secret):
            return jsonify(error="unauthorized"), 401
        data = request.get_json(silent=True) or {}
        if not isinstance(data.get("submission_id"), int) or any(k not in data for k in RESULT_FIELDS):
            return jsonify(error="bad payload"), 400
        sub = db.session.get(Submission, data["submission_id"])
        if sub is None:
            return jsonify(error="unknown submission"), 404
        _apply_result(sub, data)
        db.session.commit()
        _publish_submission_state(sub, "attempt_submitted")
        app.logger.info("callback: submission %s graded %s/%s", sub.id, sub.score, sub.max_score)
        return jsonify(status="ok")

    @app.route("/api/cron/finalize", methods=["POST"])
    def cron_finalize():
        """Called every ~15 minutes by an EventBridge schedule (through the Lambda): expire abandoned attempts and
        pick the best attempt for students who missed the selection deadline. The same work also happens lazily
        whenever a page touches those attempts, so a missed run only delays certificates."""
        secret = app.config["GRADER_SECRET"]
        if not secret or not secrets.compare_digest(request.headers.get("x-grader-secret", ""), secret):
            return jsonify(error="unauthorized"), 401
        _finish_expired(app, Submission.query.filter_by(status="in_progress").all())
        exams = Exam.query.filter(Exam.selection_deadline.isnot(None), Exam.selection_deadline <= utcnow()).all()
        for exam in exams:
            _finalize_exam(app, exam)
        return jsonify(status="ok", exams=len(exams))

    @app.route("/submissions/<int:sub_id>/regrade", methods=["POST"])
    @login_required()
    def submission_regrade(sub_id):
        sub = db.get_or_404(Submission, sub_id)
        if (g.user.id != sub.student_id and not is_quiz_owner(g.user, sub.exam)) or not (sub.status == "error" or _is_stuck(sub)):
            abort(403)
        if not _grade_and_save(app, sub):
            flash("Grading is still unavailable, please try again later.", "danger")
        return redirect(url_for("submission_view", sub_id=sub.id))

    @app.route("/local-certificates/<path:key>")
    @login_required()
    def local_certificate(key):
        if not grader_client.is_local():
            abort(404)
        cert = Certificate.query.filter_by(s3_key=key).first_or_404()
        if g.user.id != cert.student_id and not is_quiz_owner(g.user, cert.exam):
            abort(403)
        return send_file(grader_client.local_certificate_path(key), mimetype="application/pdf")

    @app.route("/verify/<code>")
    def verify_certificate(code):
        """Public: anyone holding a certificate can check it is genuine and still valid."""
        cert = Certificate.query.filter_by(code=code.strip().upper()).first()
        return render_template("verify.html", cert=cert, code=code), 200 if cert else 404

    @app.route("/verify")
    def verify_lookup():
        code = request.args.get("code", "").strip()
        return redirect(url_for("verify_certificate", code=code)) if code else render_template("verify.html", cert=None, code="")

    @app.errorhandler(400)
    def bad_request(e):
        msg = getattr(e, "description", "Bad Request")
        return render_template("error.html", code=400, message=msg), 400

    @app.errorhandler(403)
    def forbidden(_):
        return render_template("error.html", code=403, message="You do not have permission to access this page."), 403

    @app.errorhandler(413)
    def too_large(_):
        return render_template("error.html", code=413, message="The uploaded file is too large (max 10 MB)."), 413

    @app.errorhandler(404)
    def not_found(_):
        return render_template("error.html", code=404, message="Page not found."), 404

    @app.errorhandler(500)
    def server_error(e):
        import traceback
        tb = traceback.format_exc()
        app.logger.error("500 Internal Server Error: %s\n%s", e, tb)
        return render_template("error.html", code=500, message=f"Internal Error: {e}\n\n{tb}"), 500

    @app.route("/api/debug-db")
    def debug_db():
        try:
            db.create_all()
            from models import User
            count = User.query.count()
            return jsonify(status="ok", message="Database connected and tables verified", user_count=count)
        except Exception as e:
            import traceback
            return jsonify(status="error", error=str(e), traceback=traceback.format_exc()), 500


def register_cli(app):
    @app.cli.command("init-db")
    @click.option("--demo", is_flag=True, help="Add a sample teacher, exams and submissions")
    def init_db(demo):
        """Create tables (works on SQLite and Azure SQL)."""
        db.create_all()
        _ensure_schema(app)
        click.echo("Tables created.")
        if demo:
            from demo_data import seed_demo

            # Local grading builds download URLs with url_for, which needs a request context.
            with app.test_request_context():
                added = seed_demo(app, lambda sub: _grade_and_save(app, sub))
            click.echo("Demo data added." if added else "Demo data already present.")


app = create_app()
