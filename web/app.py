import csv
import io
import secrets
import statistics
from datetime import timedelta

import click
from flask import (Flask, Response, abort, flash, g, jsonify, redirect, render_template, request, send_file,
                   session, url_for)
from sqlalchemy import update
from werkzeug.middleware.proxy_fix import ProxyFix

import grader_client
from auth import bp as auth_bp
from auth import login_required
from config import Config
from models import Exam, ExamVersion, Question, Submission, db, utcnow

LETTERS = "ABCDEFGH"


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
        if request.method == "POST" and request.endpoint != "grader_callback":
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


def _own_exam(exam_id):
    exam = db.get_or_404(Exam, exam_id)
    if exam.teacher_id != g.user.id:
        abort(403)
    return exam


def _parse_correct(raw, n_options):
    """'A' / 'a;c' / 'B,D' -> [0] / [0, 2] / [1, 3]."""
    idx = sorted({LETTERS.index(c) for c in raw.upper() if c in LETTERS})
    if not idx or max(idx) >= n_options:
        raise ValueError(f"invalid correct answer: '{raw}'")
    return idx


def _exam_stats(exam):
    graded = [s for s in exam.submissions if s.status == "graded"]
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


def _question_stats(exam):
    """Percentage of graded submissions answering each question correctly (for the report)."""
    graded = [s for s in exam.submissions if s.status == "graded" and s.details]
    out = {}
    for q in exam.questions:
        hits = [d["is_correct"] for s in graded for d in s.details if d["question_id"] == q.id]
        out[q.id] = round(100 * sum(hits) / len(hits), 1) if hits else None
    return out


RESULT_FIELDS = ("score", "max_score", "percent", "passed", "details", "certificate_key", "certificate_id")
# A queued submission with no callback after this long can be re-sent by the student/teacher.
STUCK_AFTER = timedelta(minutes=2)
SUBMIT_GRACE = timedelta(seconds=30)


def _apply_result(sub, result):
    sub.score, sub.max_score, sub.percent = result["score"], result["max_score"], result["percent"]
    sub.passed, sub.details = result["passed"], result["details"]
    sub.certificate_key, sub.certificate_id = result["certificate_key"], result["certificate_id"]
    sub.status = "graded"


def _is_stuck(sub):
    return sub.status == "pending" and utcnow() - sub.submitted_at > STUCK_AFTER


# this try to claim the submission; only in_progress one can be claimed
def _claim(sub, **values):
    claimed = db.session.execute(
        update(Submission)
        .where(Submission.id == sub.id, Submission.status == "in_progress")
        .values(status="pending", submitted_at=utcnow(), **values)
    ).rowcount == 1
    db.session.commit()
    db.session.refresh(sub)
    return claimed


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
    payload = {
        "submission_id": sub.id,
        "student": {"name": sub.student.name, "email": sub.student.email},
        "exam": {"id": exam.id, "title": exam.title, "pass_percent": version.pass_percent},
        "questions": [{"id": q.id, "points": q.points, "correct": q.correct} for q in version.questions],
        "answers": sub.answers,
    }
    try:
        if grader_client.is_async():
            grader_client.enqueue_submission(payload)
            sub.status = "pending"
            sub.submitted_at = utcnow()  # restarts the "stuck" timer on regrade
            db.session.commit()
            return True
        result = grader_client.grade_submission(payload)
    except Exception:
        app.logger.exception("grading failed for submission %s", sub.id)
        sub.status = "error"
        db.session.commit()
        return False
    _apply_result(sub, result)
    db.session.commit()
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
        graded = [s for e in exams for s in e.submissions if s.status == "graded"]
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
            exam = Exam(
                title=title,
                description=request.form.get("description", "").strip(),
                duration_minutes=max(1, request.form.get("duration_minutes", 15, type=int)),
                pass_percent=min(100, max(0, request.form.get("pass_percent", 50, type=float))),
                teacher_id=g.user.id,
            )
            db.session.add(exam)
            db.session.commit()
            flash("Exam created. Now add some questions.", "success")
            return redirect(url_for("exam_manage", exam_id=exam.id))
        return render_template("exam_form.html")

    @app.route("/teacher/exams/<int:exam_id>")
    @login_required("teacher")
    def exam_manage(exam_id):
        return render_template("exam_manage.html", exam=_own_exam(exam_id))

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
            q = Question(exam=exam, text=text, options=options, correct=correct,
                         points=max(0.0, request.form.get("points", 1, type=float)))
            db.session.add(q)
            db.session.flush()  # need q.id before snapshotting
            exam.new_version([x.id for x in exam.questions] + [q.id])
            db.session.commit()
            flash("Question added.", "success")
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
                options = [row.get(k, "").strip() for k in "ABCD" if row.get(k, "").strip()]
                if not row.get("question", "").strip() or len(options) < 2:
                    raise ValueError("missing question text or fewer than 2 options")
                added.append(Question(exam=exam, text=row["question"].strip(), options=options,
                                      correct=_parse_correct(row.get("correct", ""), len(options)),
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

    @app.route("/teacher/exams/<int:exam_id>/results")
    @login_required("teacher")
    def exam_results(exam_id):
        exam = _own_exam(exam_id)
        _finish_expired(app, exam.submissions)
        subs = sorted(exam.submissions, key=lambda s: s.submitted_at, reverse=True)
        return render_template("exam_results.html", exam=exam, submissions=subs, stats=_exam_stats(exam))

    @app.route("/teacher/exams/<int:exam_id>/results.csv")
    @login_required("teacher")
    def exam_results_csv(exam_id):
        exam = _own_exam(exam_id)
        _finish_expired(app, exam.submissions)
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["Full name", "Email", "Score", "Max score", "Percent", "Result", "Submitted at (UTC)", "Certificate ID"])
        for s in sorted(exam.submissions, key=lambda s: s.submitted_at):
            if s.status == "in_progress":
                continue
            w.writerow([s.student.name, s.student.email, s.score, s.max_score, s.percent,
                        "Passed" if s.passed else "Failed", s.submitted_at.strftime("%Y-%m-%d %H:%M"),
                        s.certificate_id or ""])
        # BOM so Excel opens Vietnamese text correctly.
        return Response("\ufeff" + buf.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition": f"attachment; filename=ket-qua-exam-{exam.id}.csv"})

    @app.route("/teacher/exams/<int:exam_id>/report")
    @login_required("teacher")
    def exam_report(exam_id):
        exam = _own_exam(exam_id)
        _finish_expired(app, exam.submissions)
        return render_template("exam_report.html", exam=exam, stats=_exam_stats(exam),
                               qstats=_question_stats(exam),
                               submissions=sorted(exam.submissions, key=lambda s: -(s.percent or 0)))

    # ---------- Student ----------
    @app.route("/student")
    @login_required("student")
    def student_dashboard():
        exams = Exam.query.filter_by(published=True).order_by(Exam.created_at.desc()).all()
        mine = {s.exam_id: s for s in Submission.query.filter_by(student_id=g.user.id)}
        _finish_expired(app, mine.values())
        return render_template("student_dashboard.html", exams=exams, mine=mine)

    @app.route("/student/exams/<int:exam_id>", methods=["GET", "POST"])
    @login_required("student")
    def take_exam(exam_id):
        exam = db.get_or_404(Exam, exam_id)
        if not exam.published:
            abort(404)
        # get current attempt, if null -> start a new timed attempt
        sub = Submission.query.filter_by(exam_id=exam.id, student_id=g.user.id).first()
        if sub is None:
            # pin the current version; this attempt reads only from it from now on
            sub = Submission(exam_id=exam.id, student_id=g.user.id, version_id=exam.current_version_id,
                             answers={}, status="in_progress")
            db.session.add(sub)
            db.session.commit()
        _finish_if_expired(app, sub) # if the attempt is ongoing but expired, submit right away
        if sub.status != "in_progress":
            return redirect(url_for("submission_view", sub_id=sub.id))
        if request.method == "GET":
            # render the server side time on the web
            remaining = max(0, int((sub.deadline - utcnow()).total_seconds()))
            return render_template("take_exam.html", exam=exam, questions=sub.version.questions,
                                   remaining=remaining)

        answers = {str(q.id): [int(v) for v in request.form.getlist(f"q{q.id}") if v.isdigit()]
                   for q in sub.version.questions}
        if _claim(sub, answers=answers) and not _grade_and_save(app, sub):
            flash("Your answers were saved but grading failed. Click 'Regrade' or contact your teacher.", "danger")
        return redirect(url_for("submission_view", sub_id=sub.id))

    @app.route("/submissions/<int:sub_id>")
    @login_required()
    def submission_view(sub_id):
        sub = db.get_or_404(Submission, sub_id)
        if g.user.id not in (sub.student_id, sub.exam.teacher_id):
            abort(403)
        _finish_if_expired(app, sub)
        if sub.status == "in_progress" and g.user.id == sub.student_id:
            return redirect(url_for("take_exam", exam_id=sub.exam_id))
        cert_url = None
        if sub.certificate_key:
            try:
                cert_url = grader_client.certificate_url(sub.certificate_key)
            except Exception:
                app.logger.exception("presign failed")
        details = {d["question_id"]: d for d in (sub.details or [])}
        return render_template("submission.html", sub=sub, exam=sub.exam, questions=sub.version.questions,
                               details=details, cert_url=cert_url,
                               stuck=_is_stuck(sub))

    @app.route("/submissions/<int:sub_id>/status")
    @login_required()
    def submission_status(sub_id):
        sub = db.get_or_404(Submission, sub_id)
        if g.user.id not in (sub.student_id, sub.exam.teacher_id):
            abort(403)
        return jsonify(status=sub.status, stuck=_is_stuck(sub))

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
        app.logger.info("callback: submission %s graded %s/%s", sub.id, sub.score, sub.max_score)
        return jsonify(status="ok")

    @app.route("/submissions/<int:sub_id>/regrade", methods=["POST"])
    @login_required()
    def submission_regrade(sub_id):
        sub = db.get_or_404(Submission, sub_id)
        if g.user.id not in (sub.student_id, sub.exam.teacher_id) or not (sub.status == "error" or _is_stuck(sub)):
            abort(403)
        if not _grade_and_save(app, sub):
            flash("Grading is still unavailable, please try again later.", "danger")
        return redirect(url_for("submission_view", sub_id=sub.id))

    @app.route("/local-certificates/<path:key>")
    @login_required()
    def local_certificate(key):
        if not grader_client.is_local():
            abort(404)
        sub = Submission.query.filter_by(certificate_key=key).first_or_404()
        if g.user.id not in (sub.student_id, sub.exam.teacher_id):
            abort(403)
        return send_file(grader_client.local_certificate_path(key), mimetype="application/pdf")

    @app.errorhandler(400)
    def bad_request(e):
        msg = getattr(e, "description", "Bad Request")
        return render_template("error.html", code=400, message=msg), 400

    @app.errorhandler(403)
    def forbidden(_):
        return render_template("error.html", code=403, message="You do not have permission to access this page."), 403

    @app.errorhandler(404)
    def not_found(_):
        return render_template("error.html", code=404, message="Page not found."), 404


def register_cli(app):
    @app.cli.command("init-db")
    @click.option("--demo", is_flag=True, help="Add a sample teacher, exams and submissions")
    def init_db(demo):
        """Create tables (works on SQLite and Azure SQL)."""
        db.create_all()
        click.echo("Tables created.")
        if demo:
            from demo_data import seed_demo

            # Local grading builds download URLs with url_for, which needs a request context.
            with app.test_request_context():
                added = seed_demo(app, lambda sub: _grade_and_save(app, sub))
            click.echo("Demo data added." if added else "Demo data already present.")


app = create_app()
