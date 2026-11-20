import io
import re

import pytest

from app import create_app
from models import Exam, Submission, db


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
        "AUTH_MODE": "dev",
        "GRADER_URL": "",
        "LOCAL_CERT_DIR": str(tmp_path / "certs"),
    })
    with app.app_context():
        db.create_all()
    return app


def csrf(client, path="/login"):
    html = client.get(path).get_data(as_text=True)
    return re.search(r'name="csrf" value="([^"]+)"', html).group(1)


def login(client, name, email, role):
    r = client.post("/login", data={"csrf": csrf(client), "name": name, "email": email, "role": role})
    assert r.status_code == 302


def test_full_flow(app):
    teacher, student, other = app.test_client(), app.test_client(), app.test_client()
    login(teacher, "Ms. Lane", "lan@school.edu", "teacher")
    login(student, "Nguyễn An", "an@school.edu", "student")
    login(other, "Trần Bình", "binh@school.edu", "student")

    # Students cannot reach teacher pages; requests without CSRF token are rejected.
    assert student.get("/teacher").status_code == 403
    assert teacher.post("/teacher/exams/new", data={"title": "x"}).status_code == 400

    t = csrf(teacher, "/teacher")
    r = teacher.post("/teacher/exams/new", data={"csrf": t, "title": "Cloud Quiz", "duration_minutes": "10",
                                                 "pass_percent": "60", "visibility": "public"})
    exam_id = int(r.headers["Location"].rstrip("/").split("/")[-1])

    # Option C left blank: the correct index for "D" must be remapped to 2.
    teacher.post(f"/teacher/exams/{exam_id}/questions", data={
        "csrf": t, "text": "What is S3?", "options": ["Object storage", "VM", "", "DNS"], "correct": ["0"], "points": "1"})
    teacher.post(f"/teacher/exams/{exam_id}/questions", data={
        "csrf": t, "text": "Serverless?", "options": ["Lambda", "EC2", "", "Functions"], "correct": ["0", "3"],
        "points": "2"})
    csv_data = "question,A,B,C,D,correct,points\nWhat is Entra ID for?,Identity,Storage,,,A,1\nbroken,only one,,,,A,1\n"
    teacher.post(f"/teacher/exams/{exam_id}/import", data={
        "csrf": t, "file": (io.BytesIO(csv_data.encode()), "q.csv")}, content_type="multipart/form-data")

    with app.app_context():
        exam = db.session.get(Exam, exam_id)
        assert [q.correct for q in exam.questions] == [[0], [0, 2], [0]]
        assert exam.questions[1].options == ["Lambda", "EC2", "Functions"]
        qids = [q.id for q in exam.questions]

    # Draft exams are hidden from students.
    assert student.get(f"/student/exams/{exam_id}").status_code == 404
    teacher.post(f"/teacher/exams/{exam_id}/publish", data={"csrf": t})
    assert "Cloud Quiz" in student.get("/student").get_data(as_text=True)

    s = csrf(student, f"/student/exams/{exam_id}")
    r = student.post(f"/student/exams/{exam_id}", data={
        "csrf": s, f"q{qids[0]}": "0", f"q{qids[1]}": ["0", "2"], f"q{qids[2]}": "1"})
    sub_page = student.get(r.headers["Location"]).get_data(as_text=True)
    assert "3/4" in sub_page and "75%" in sub_page and "PASSED" in sub_page

    with app.app_context():
        sub = Submission.query.one()
        key = sub.certificate.s3_key
    pdf = student.get(f"/local-certificates/{key}")
    assert pdf.status_code == 200 and pdf.data.startswith(b"%PDF")
    assert other.get(f"/local-certificates/{key}").status_code == 403
    assert other.get(f"/submissions/{sub.id}").status_code == 403

    # Only one attempt: revisiting redirects to the existing result.
    assert student.get(f"/student/exams/{exam_id}").headers["Location"].endswith(f"/submissions/{sub.id}")

    report_csv = teacher.get(f"/teacher/exams/{exam_id}/results.csv").get_data(as_text=True)
    assert "Nguyễn An" in report_csv and "Passed" in report_csv
    report = teacher.get(f"/teacher/exams/{exam_id}/report").get_data(as_text=True)
    assert "RESULTS REPORT" in report
    assert "Exam results" in teacher.get(f"/teacher/exams/{exam_id}/results").get_data(as_text=True)


def test_grader_failure_marks_error_and_regrade(app, monkeypatch):
    import grader_client

    teacher, student = app.test_client(), app.test_client()
    login(teacher, "T", "t@x.edu", "teacher")
    login(student, "S", "s@x.edu", "student")
    t = csrf(teacher, "/teacher")
    r = teacher.post("/teacher/exams/new", data={"csrf": t, "title": "E", "visibility": "public"})
    exam_id = int(r.headers["Location"].split("/")[-1])
    teacher.post(f"/teacher/exams/{exam_id}/questions", data={
        "csrf": t, "text": "Q", "options": ["a", "b"], "correct": ["1"]})
    teacher.post(f"/teacher/exams/{exam_id}/publish", data={"csrf": t})

    real = grader_client.grade_submission

    def boom(payload):
        raise ConnectionError("lambda down")

    monkeypatch.setattr(grader_client, "grade_submission", boom)
    s = csrf(student, f"/student/exams/{exam_id}")
    r = student.post(f"/student/exams/{exam_id}", data={"csrf": s, "q1": "1"})
    page = student.get(r.headers["Location"]).get_data(as_text=True)
    assert "Regrade" in page

    monkeypatch.setattr(grader_client, "grade_submission", real)
    sub_path = r.headers["Location"]
    student.post(f"{sub_path}/regrade", data={"csrf": csrf(student, sub_path)})
    assert "1/1" in student.get(sub_path).get_data(as_text=True)


def test_async_sqs_flow_with_callback(app, monkeypatch, tmp_path):
    """Async mode: submit is queued (fake AWS), page shows pending, Lambda's callback completes it."""
    import grader_client
    from service import process_submission

    app.config.update(GRADER_URL="https://api.example/grade", GRADER_SECRET="s3cret", GRADER_ASYNC=True)
    queued = []

    class FakeResp:
        def __init__(self, body):
            self.body = body

        def raise_for_status(self):
            pass

        def json(self):
            return self.body

    def fake_post(url, json, headers, timeout):
        assert headers["x-grader-secret"] == "s3cret"
        if json["action"] == "submit":
            queued.append(json)
            return FakeResp({"status": "queued", "message_id": "m1"})
        return FakeResp({"certificate_url": f"https://s3.example/{json['certificate_key']}?sig=1"})

    monkeypatch.setattr(grader_client.requests, "post", fake_post)

    teacher, student = app.test_client(), app.test_client()
    login(teacher, "T", "t@x.edu", "teacher")
    login(student, "S", "s@x.edu", "student")
    t = csrf(teacher, "/teacher")
    r = teacher.post("/teacher/exams/new", data={"csrf": t, "title": "Async", "visibility": "public"})
    exam_id = int(r.headers["Location"].split("/")[-1])
    teacher.post(f"/teacher/exams/{exam_id}/questions", data={
        "csrf": t, "text": "Q", "options": ["a", "b"], "correct": ["1"]})
    teacher.post(f"/teacher/exams/{exam_id}/publish", data={"csrf": t})

    s = csrf(student, f"/student/exams/{exam_id}")
    r = student.post(f"/student/exams/{exam_id}", data={"csrf": s, "q1": "1"})
    sub_path = r.headers["Location"]
    assert len(queued) == 1 and queued[0]["answers"] == {"1": [1]}
    page = student.get(sub_path).get_data(as_text=True)
    assert "Grading your answers" in page and "Amazon SQS" in page
    assert student.get(f"{sub_path}/status").get_json() == {"status": "pending", "stuck": False}
    # Not stuck yet, so regrade is refused.
    assert student.post(f"{sub_path}/regrade", data={"csrf": csrf(student, sub_path)}).status_code == 403

    # What the Lambda worker computes and posts back.
    result = process_submission({k: v for k, v in queued[0].items() if k != "action"}, lambda k, b: None)
    body = {"submission_id": queued[0]["submission_id"], **result}
    anon = app.test_client()
    assert anon.post("/api/grader/callback", json=body).status_code == 401
    assert anon.post("/api/grader/callback", json=body, headers={"x-grader-secret": "wrong"}).status_code == 401
    assert anon.post("/api/grader/callback", json={"submission_id": 1},
                     headers={"x-grader-secret": "s3cret"}).status_code == 400
    assert anon.post("/api/grader/callback", json={**body, "submission_id": 999},
                     headers={"x-grader-secret": "s3cret"}).status_code == 404
    assert anon.post("/api/grader/callback", json=body, headers={"x-grader-secret": "s3cret"}).status_code == 200

    assert student.get(f"{sub_path}/status").get_json()["status"] == "graded"
    page = student.get(sub_path).get_data(as_text=True)
    assert "1/1" in page and "https://s3.example/certificates/" in page


def test_async_stuck_submission_can_be_resent(app, monkeypatch):
    import grader_client
    from datetime import timedelta

    app.config.update(GRADER_URL="https://api.example/grade", GRADER_SECRET="s", GRADER_ASYNC=True)
    sent = []
    monkeypatch.setattr(grader_client, "enqueue_submission", sent.append)

    teacher, student = app.test_client(), app.test_client()
    login(teacher, "T", "t@x.edu", "teacher")
    login(student, "S", "s@x.edu", "student")
    t = csrf(teacher, "/teacher")
    r = teacher.post("/teacher/exams/new", data={"csrf": t, "title": "E", "visibility": "public"})
    exam_id = int(r.headers["Location"].split("/")[-1])
    teacher.post(f"/teacher/exams/{exam_id}/questions", data={
        "csrf": t, "text": "Q", "options": ["a", "b"], "correct": ["0"]})
    teacher.post(f"/teacher/exams/{exam_id}/publish", data={"csrf": t})
    r = student.post(f"/student/exams/{exam_id}", data={"csrf": csrf(student, f"/student/exams/{exam_id}"), "q1": "0"})
    sub_path = r.headers["Location"]

    with app.app_context():
        sub = Submission.query.one()
        sub.submitted_at -= timedelta(minutes=5)
        db.session.commit()
    assert student.get(f"{sub_path}/status").get_json()["stuck"] is True
    student.post(f"{sub_path}/regrade", data={"csrf": csrf(student, sub_path)})
    assert len(sent) == 2
    assert student.get(f"{sub_path}/status").get_json() == {"status": "pending", "stuck": False}


def _setup(app, questions=(("First question?", ["a", "b"], ["0"]), ("Second question?", ["a", "b"], ["1"])), duration="10"):
    """A published exam plus logged-in teacher and student clients. Returns (teacher, student, csrf, exam_id)."""
    teacher, student = app.test_client(), app.test_client()
    login(teacher, "T", "t@x.edu", "teacher")
    login(student, "S", "s@x.edu", "student")
    t = csrf(teacher, "/teacher")
    r = teacher.post("/teacher/exams/new", data={"csrf": t, "title": "E", "duration_minutes": duration, "visibility": "public"})
    exam_id = int(r.headers["Location"].split("/")[-1])
    for text, options, correct in questions:
        teacher.post(f"/teacher/exams/{exam_id}/questions", data={
            "csrf": t, "text": text, "options": options, "correct": correct})
    teacher.post(f"/teacher/exams/{exam_id}/publish", data={"csrf": t})
    return teacher, student, t, exam_id


def _shift_start(app, minutes, email="s@x.edu"):
    from datetime import timedelta

    from models import User
    with app.app_context():
        sub = Submission.query.join(User, Submission.student_id == User.id).filter(User.email == email).one()
        sub.started_at -= timedelta(minutes=minutes)
        db.session.commit()


def _remaining(html):
    return int(re.search(r"let remaining = (\d+);", html).group(1))


def test_opening_exam_starts_server_clock(app):
    _, student, _, exam_id = _setup(app)
    first = _remaining(student.get(f"/student/exams/{exam_id}").get_data(as_text=True))
    assert 595 <= first <= 600
    with app.app_context():
        sub = Submission.query.one()
        assert sub.status == "in_progress" and sub.answers == {}

    # Refreshing reuses the attempt, so the clock keeps running instead of restarting.
    _shift_start(app, 4)
    again = _remaining(student.get(f"/student/exams/{exam_id}").get_data(as_text=True))
    assert 355 <= again <= 360
    with app.app_context():
        assert Submission.query.count() == 1

    dashboard = student.get("/student").get_data(as_text=True)
    assert "In progress" in dashboard and "Continue exam" in dashboard
    # An unfinished attempt's result page sends the student back to the exam.
    assert student.get("/submissions/1").headers["Location"].endswith(f"/student/exams/{exam_id}")


def test_submit_within_grace_is_accepted(app):
    _, student, _, exam_id = _setup(app)
    s = csrf(student, f"/student/exams/{exam_id}")
    # Exactly at the deadline, still inside the grace window.
    _shift_start(app, 10)
    r = student.post(f"/student/exams/{exam_id}", data={"csrf": s, "q1": "0", "q2": "1"})
    assert "2/2" in student.get(r.headers["Location"]).get_data(as_text=True)


def test_late_submit_is_scored_zero(app):
    _, student, _, exam_id = _setup(app)
    s = csrf(student, f"/student/exams/{exam_id}")
    _shift_start(app, 60 * 5)
    r = student.post(f"/student/exams/{exam_id}", data={"csrf": s, "q1": "0", "q2": "1"})
    assert r.headers["Location"].endswith("/submissions/1")
    with app.app_context():
        sub = Submission.query.one()
        assert (sub.status, sub.score, sub.answers) == ("graded", 0.0, {})


def test_abandoned_attempt_expires_when_viewed(app):
    teacher, student, _, exam_id = _setup(app)
    student.get(f"/student/exams/{exam_id}")
    _shift_start(app, 11)
    assert "S" in teacher.get(f"/teacher/exams/{exam_id}/results").get_data(as_text=True)
    with app.app_context():
        sub = Submission.query.one()
        assert (sub.status, sub.score) == ("graded", 0.0)


def test_in_progress_attempts_left_out_of_csv(app):
    teacher, student, _, exam_id = _setup(app)
    student.get(f"/student/exams/{exam_id}")
    assert "s@x.edu" not in teacher.get(f"/teacher/exams/{exam_id}/results.csv").get_data(as_text=True)


def test_attempt_is_claimed_and_graded_once(app, monkeypatch):
    import grader_client

    from app import _claim
    _, student, _, exam_id = _setup(app)
    calls = []
    real = grader_client.grade_submission
    monkeypatch.setattr(grader_client, "grade_submission", lambda p: calls.append(p) or real(p))

    s = csrf(student, f"/student/exams/{exam_id}")
    student.post(f"/student/exams/{exam_id}", data={"csrf": s, "q1": "0", "q2": "1"})
    # A second submit (e.g. another tab) loses the claim: no regrade, answers untouched.
    student.post(f"/student/exams/{exam_id}", data={"csrf": s, "q1": "1"})
    assert len(calls) == 1
    with app.app_context():
        sub = Submission.query.one()
        assert sub.answers == {"1": [0], "2": [1]} and sub.score == 2
        assert _claim(sub, answers={}) is False
        assert Submission.query.one().answers == {"1": [0], "2": [1]}


def test_attempt_pinned_to_version_through_edits(app, monkeypatch):
    import grader_client

    teacher, student, t, exam_id = _setup(app)
    s = csrf(student, f"/student/exams/{exam_id}")

    # Teacher edits mid-attempt: add a 5-point question, drop Q1.
    teacher.post(f"/teacher/exams/{exam_id}/questions", data={
        "csrf": t, "text": "Added later?", "options": ["a", "b"], "correct": ["0"], "points": "5"})
    teacher.post(f"/teacher/exams/{exam_id}/questions/1/delete", data={"csrf": t})
    with app.app_context():
        exam = db.session.get(Exam, exam_id)
        assert [q.text for q in exam.questions] == ["Second question?", "Added later?"] and len(exam.versions) == 4

    page = student.get(f"/student/exams/{exam_id}").get_data(as_text=True)
    assert "First question?" in page and "Added later?" not in page

    # Fail the first grading so the regrade path runs after the edits too.
    real = grader_client.grade_submission
    monkeypatch.setattr(grader_client, "grade_submission", lambda p: (_ for _ in ()).throw(ConnectionError()))
    r = student.post(f"/student/exams/{exam_id}", data={"csrf": s, "q1": "0", "q2": "1", "q3": "0"})
    sub_path = r.headers["Location"]
    monkeypatch.setattr(grader_client, "grade_submission", real)
    student.post(f"{sub_path}/regrade", data={"csrf": csrf(student, sub_path)})

    review = student.get(sub_path).get_data(as_text=True)
    assert "2/2" in review and "First question?" in review and "Added later?" not in review
    with app.app_context():
        assert Submission.query.one().answers == {"1": [0], "2": [1]}

    other = app.test_client()
    login(other, "O", "o@x.edu", "student")
    page = other.get(f"/student/exams/{exam_id}").get_data(as_text=True)
    assert "Added later?" in page and "First question?" not in page


def test_versions_created_per_edit(app):
    teacher, _, t, exam_id = _setup(app)
    csv_data = "question,A,B,C,D,correct,points\nI1,a,b,,,A,1\nI2,a,b,,,B,1\nbroken,only,,,,A,1\n"
    teacher.post(f"/teacher/exams/{exam_id}/import", data={
        "csrf": t, "file": (io.BytesIO(csv_data.encode()), "q.csv")}, content_type="multipart/form-data")
    teacher.post(f"/teacher/exams/{exam_id}/import", data={
        "csrf": t, "file": (io.BytesIO(b"question,A,B,C,D,correct,points\nbroken,only,,,,A,1\n"), "q.csv")},
        content_type="multipart/form-data")
    with app.app_context():
        exam = db.session.get(Exam, exam_id)
        # Two adds + one import; the all-invalid import adds no version.
        assert [v.question_ids for v in exam.versions] == [[1], [1, 2], [1, 2, 3, 4]]
        assert exam.current_version_id == exam.versions[-1].id
    assert teacher.post(f"/teacher/exams/{exam_id}/questions/99/delete", data={"csrf": t}).status_code == 404


def test_restore_moves_pointer_only(app):
    teacher, student, t, exam_id = _setup(app)
    teacher.post(f"/teacher/exams/{exam_id}/questions", data={
        "csrf": t, "text": "Added later?", "options": ["a", "b"], "correct": ["0"]})
    with app.app_context():
        first = db.session.get(Exam, exam_id).versions[1].id
    r = teacher.post(f"/teacher/exams/{exam_id}/versions/{first}/restore", data={"csrf": t})
    assert "Restored version 2" in teacher.get(r.headers["Location"]).get_data(as_text=True)
    with app.app_context():
        exam = db.session.get(Exam, exam_id)
        assert exam.current_version_id == first and len(exam.versions) == 3
    page = student.get(f"/student/exams/{exam_id}").get_data(as_text=True)
    assert "Second question?" in page and "Added later?" not in page

    # A version of another exam cannot be restored here, and other teachers cannot restore at all.
    r = teacher.post("/teacher/exams/new", data={"csrf": t, "title": "Other"})
    other_id = int(r.headers["Location"].split("/")[-1])
    assert teacher.post(f"/teacher/exams/{other_id}/versions/{first}/restore", data={"csrf": t}).status_code == 404
    intruder = app.test_client()
    login(intruder, "X", "x@x.edu", "teacher")
    assert intruder.post(f"/teacher/exams/{exam_id}/versions/{first}/restore",
                         data={"csrf": csrf(intruder, "/teacher")}).status_code in (403, 404)


def test_delete_exam_removes_versions_and_attempts(app):
    from models import ExamVersion, Question
    teacher, student, t, exam_id = _setup(app)
    student.post(f"/student/exams/{exam_id}", data={"csrf": csrf(student, f"/student/exams/{exam_id}"), "q1": "0"})
    teacher.post(f"/teacher/exams/{exam_id}/delete", data={"csrf": t})
    with app.app_context():
        assert (Exam.query.count(), ExamVersion.query.count(), Question.query.count(), Submission.query.count()) \
            == (0, 0, 0, 0)


def test_manage_page_warns_about_edit_impact(app):
    teacher, student, t, exam_id = _setup(app)
    page = teacher.get(f"/teacher/exams/{exam_id}").get_data(as_text=True)
    assert 'id="edit-impact"' not in page

    student.get(f"/student/exams/{exam_id}")
    finisher = app.test_client()
    login(finisher, "F", "f@x.edu", "student")
    finisher.post(f"/student/exams/{exam_id}", data={"csrf": csrf(finisher, f"/student/exams/{exam_id}"), "q1": "0"})
    page = teacher.get(f"/teacher/exams/{exam_id}").get_data(as_text=True)
    assert "version 3" in page and "1 student is mid-attempt" in page and "1 attempt is finished" in page
    assert "2 attempts" in page and page.count("js-edit") >= 4


MANAGED = {"managed": "on", "fullscreen": "on", "reentry_approval": "on"}


def _managed(app, teacher, t, exam_id, **extra):
    data = {"csrf": t, "duration_minutes": "10", "pass_percent": "50", **MANAGED, **extra}
    teacher.post(f"/teacher/exams/{exam_id}/settings", data={k: v for k, v in data.items() if v is not None})


def _sub(app):
    with app.app_context():
        sub = Submission.query.one()
        return {"status": sub.status, "violations": sub.violations, "locked": sub.locked_at is not None,
                "review": sub.review, "cert": sub.certificate and sub.certificate.s3_key, "events": [(e.type, e.counted) for e in sub.events]}


def test_settings_snapshot_policy_into_new_version(app):
    teacher, _, t, exam_id = _setup(app)
    _managed(app, teacher, t, exam_id, reentry_approval=None, autosubmit="on", autosubmit_after="3",
             allow_paste="on", duration_minutes="20")
    with app.app_context():
        exam = db.session.get(Exam, exam_id)
        p = exam.current_version.settings
        assert len(exam.versions) == 3 and exam.current_version.duration_minutes == 20
        assert p["managed"] and p["fullscreen"] and not p["reentry_approval"] and p["allow_paste"]
        assert p["autosubmit_after"] == 3 and not p["withhold_if_flagged"]
        assert not exam.versions[1].settings["managed"]
    page = teacher.get(f"/teacher/exams/{exam_id}").get_data(as_text=True)
    assert "Managed mode" in page and "Without approval" in page


def test_unmanaged_exam_ignores_events(app):
    _, student, _, exam_id = _setup(app)
    s = csrf(student, f"/student/exams/{exam_id}")
    student.get(f"/student/exams/{exam_id}")
    student.post("/submissions/1/events", data={"csrf": s, "type": "fullscreen_exit"})
    assert _sub(app)["violations"] == 0 and _sub(app)["events"] == []


def test_reentry_locks_until_teacher_approves(app):
    teacher, student, t, exam_id = _setup(app)
    _managed(app, teacher, t, exam_id)
    s = csrf(student, f"/student/exams/{exam_id}")
    assert _sub(app)["violations"] == 0
    page = student.get(f"/student/exams/{exam_id}").get_data(as_text=True)
    assert "Waiting for your teacher" in page
    assert _sub(app) | {"events": None} == {"status": "in_progress", "violations": 1, "locked": True,
                                           "review": None, "cert": None, "events": None}
    # Reloading again while locked is not counted twice.
    student.get(f"/student/exams/{exam_id}")
    assert student.post("/submissions/1/heartbeat", data={"csrf": s}).get_json()["locked"] is True
    assert _sub(app)["violations"] == 1

    live = teacher.get(f"/teacher/exams/{exam_id}/live.json").get_json()
    assert live["attempts"][0]["locked"] and live["attempts"][0]["lock_reason"] == "reentry"
    assert live["events"][0]["type"] == "reentry"

    other = app.test_client()
    login(other, "X", "x@x.edu", "teacher")
    assert other.post("/teacher/submissions/1/approve", data={"csrf": csrf(other, "/teacher")}).status_code == 403
    assert teacher.post("/teacher/submissions/1/approve", data={"csrf": t}).get_json()["locked"] is False
    assert _sub(app)["events"] == [("reentry", True), ("reentry", False), ("approved", False)]


def test_client_events_counted_logged_or_rejected(app):
    teacher, student, t, exam_id = _setup(app)
    _managed(app, teacher, t, exam_id, reentry_approval=None)
    s = csrf(student, f"/student/exams/{exam_id}")
    for kind in ("copy", "paste", "context_menu", "fullscreen_exit", "focus_lost"):
        r = student.post("/submissions/1/events", data={"csrf": s, "type": kind})
        assert r.get_json()["locked"] is False
    assert student.post("/submissions/1/events", data={"csrf": s, "type": "made_up"}).status_code == 400
    state = _sub(app)
    assert state["violations"] == 2 and [c for _, c in state["events"]] == [False, False, False, True, True]

    # Another student cannot report on this attempt.
    other = app.test_client()
    login(other, "O", "o@x.edu", "student")
    assert other.post("/submissions/1/events", data={"csrf": csrf(other, "/student"), "type": "copy"}).status_code == 403


def test_heartbeat_gap_is_a_violation(app):
    from datetime import timedelta
    teacher, student, t, exam_id = _setup(app)
    _managed(app, teacher, t, exam_id)
    s = csrf(student, f"/student/exams/{exam_id}")
    assert student.post("/submissions/1/heartbeat", data={"csrf": s}).get_json()["locked"] is False
    with app.app_context():
        sub = Submission.query.one()
        sub.last_seen_at -= timedelta(seconds=45)
        db.session.commit()
    assert student.post("/submissions/1/heartbeat", data={"csrf": s}).get_json()["locked"] is True
    assert _sub(app)["events"] == [("heartbeat_gap", True)]


def test_autosubmit_after_n_violations(app):
    teacher, student, t, exam_id = _setup(app)
    _managed(app, teacher, t, exam_id, reentry_approval=None, autosubmit="on", autosubmit_after="2")
    s = csrf(student, f"/student/exams/{exam_id}")
    assert student.post("/submissions/1/events", data={"csrf": s, "type": "focus_lost"}).get_json()["status"] == "in_progress"
    state = student.post("/submissions/1/events", data={"csrf": s, "type": "fullscreen_exit"}).get_json()
    assert state["status"] == "graded" and state["redirect"].endswith("/submissions/1")
    assert _sub(app)["events"][-1] == ("auto_submitted", False)
    # Late reports after the submit change nothing.
    student.post("/submissions/1/events", data={"csrf": s, "type": "focus_lost"})
    assert _sub(app)["violations"] == 2


def test_force_submit(app):
    teacher, student, t, exam_id = _setup(app)
    _managed(app, teacher, t, exam_id)
    student.get(f"/student/exams/{exam_id}")
    assert teacher.post("/teacher/submissions/1/force-submit", data={"csrf": t}).get_json()["status"] == "graded"
    assert _sub(app)["events"] == [("force_submitted", False)]


def test_clean_managed_attempt_gets_certificate(app):
    teacher, student, t, exam_id = _setup(app)
    _managed(app, teacher, t, exam_id, withhold_if_flagged="on")
    s = csrf(student, f"/student/exams/{exam_id}")
    r = student.post(f"/student/exams/{exam_id}", data={"csrf": s, "q1": "0", "q2": "1"})
    state = _sub(app)
    assert state["review"] is None and state["cert"]
    assert "2/2" in student.get(r.headers["Location"]).get_data(as_text=True)


def test_flagged_attempt_is_withheld_then_released(app):
    teacher, student, t, exam_id = _setup(app)
    _managed(app, teacher, t, exam_id, reentry_approval=None, withhold_if_flagged="on")
    s = csrf(student, f"/student/exams/{exam_id}")
    student.post("/submissions/1/events", data={"csrf": s, "type": "focus_lost"})
    student.post(f"/student/exams/{exam_id}", data={"csrf": s, "q1": "0", "q2": "1"})
    state = _sub(app)
    assert state["status"] == "graded" and state["review"] == "withheld" and state["cert"] is None

    page = student.get("/submissions/1").get_data(as_text=True)
    assert "under review" in page and "2/2" not in page
    assert "Under review" in student.get("/student").get_data(as_text=True)
    teacher_page = teacher.get("/submissions/1").get_data(as_text=True)
    assert "2/2" in teacher_page and "Release" in teacher_page and "focus lost" in teacher_page
    assert "Withheld" in teacher.get(f"/teacher/exams/{exam_id}/results").get_data(as_text=True)

    teacher.post("/teacher/submissions/1/release", data={"csrf": t})
    state = _sub(app)
    assert state["review"] == "released" and state["cert"]
    assert "2/2" in student.get("/submissions/1").get_data(as_text=True)
    # Release only applies to withheld results.
    assert teacher.post("/teacher/submissions/1/release", data={"csrf": t}).status_code == 409


def test_withheld_attempt_can_be_cancelled(app, monkeypatch):
    import grader_client
    sent = []
    monkeypatch.setattr(grader_client, "notify", sent.append)
    teacher, student, t, exam_id = _setup(app)
    _managed(app, teacher, t, exam_id, reentry_approval=None, withhold_if_flagged="on")
    s = csrf(student, f"/student/exams/{exam_id}")
    student.post("/submissions/1/events", data={"csrf": s, "type": "fullscreen_exit"})
    student.post(f"/student/exams/{exam_id}", data={"csrf": s, "q1": "0"})
    teacher.post("/teacher/submissions/1/cancel", data={"csrf": t})
    assert _sub(app)["review"] == "cancelled" and sent[0]["kind"] == "cancelled"
    assert sent[0]["student"]["email"] == "s@x.edu"
    page = student.get("/submissions/1").get_data(as_text=True)
    assert "Result cancelled" in page and "1/2" not in page
    assert "Cancelled" in teacher.get(f"/teacher/exams/{exam_id}/results.csv").get_data(as_text=True) or \
        "cancelled" in teacher.get(f"/teacher/exams/{exam_id}/results.csv").get_data(as_text=True)


def test_certificate_verification_page(app):
    from models import Certificate
    _, student, _, exam_id = _setup(app)
    student.post(f"/student/exams/{exam_id}", data={"csrf": csrf(student, f"/student/exams/{exam_id}"), "q1": "0"})
    with app.app_context():
        cert = Certificate.query.one()
        code, sub_id = cert.code, cert.submission_id
        assert cert.status == "valid" and cert.s3_key and cert.issued_at

    anon = app.test_client()
    page = anon.get(f"/verify/{code}").get_data(as_text=True)
    assert "Valid" in page and "S" in page and "E" in page
    assert anon.get(f"/verify/{code.lower()}").status_code == 200
    assert anon.get("/verify/NOPE123").status_code == 404
    assert anon.get(f"/verify?code={code}").headers["Location"].endswith(f"/verify/{code}")
    assert code in student.get(f"/submissions/{sub_id}").get_data(as_text=True)


def test_regrade_reuses_certificate_code(app, monkeypatch):
    import grader_client
    from models import Certificate
    _, student, _, exam_id = _setup(app)
    payloads = []
    real = grader_client.grade_submission
    monkeypatch.setattr(grader_client, "grade_submission", lambda p: payloads.append(p) or real(p))
    r = student.post(f"/student/exams/{exam_id}", data={"csrf": csrf(student, f"/student/exams/{exam_id}"), "q1": "0"})
    with app.app_context():
        sub = Submission.query.one()
        sub.status = "error"
        db.session.commit()
    student.post(f"{r.headers['Location']}/regrade", data={"csrf": csrf(student, r.headers["Location"])})
    with app.app_context():
        code = Certificate.query.one().code
    assert [p["certificate_id"] for p in payloads] == [code, code]
    assert payloads[0]["verify_url"].endswith(f"/verify/{code}")


def _multi(app, teacher, t, exam_id, attempts="3", deadline="2099-01-01T00:00"):
    return teacher.post(f"/teacher/exams/{exam_id}/settings", data={
        "csrf": t, "duration_minutes": "10", "pass_percent": "50", "max_attempts": attempts,
        "selection_deadline": deadline})


def _attempts_state(app):
    from models import Certificate
    with app.app_context():
        return [(s.attempt_no, s.status, s.score, s.selected, s.certificate.code if s.certificate else None)
                for s in Submission.query.order_by(Submission.attempt_no)], Certificate.query.count()


def _take(student, exam_id, answers):
    s = csrf(student, f"/student/exams/{exam_id}")
    return student.post(f"/student/exams/{exam_id}", data={"csrf": s, **answers})


def test_several_attempts_need_a_deadline(app):
    teacher, _, t, exam_id = _setup(app)
    page = teacher.get(_multi(app, teacher, t, exam_id, deadline="").headers["Location"]).get_data(as_text=True)
    assert "need a deadline" in page
    with app.app_context():
        assert db.session.get(Exam, exam_id).max_attempts == 1


def test_attempts_then_choose_one_locks_exam(app):
    teacher, student, t, exam_id = _setup(app)
    _multi(app, teacher, t, exam_id)
    _take(student, exam_id, {"q1": "0"})
    states, certs = _attempts_state(app)
    assert states == [(1, "graded", 1.0, False, None)] and certs == 0

    # Revisiting the exam link does not burn an attempt; the next one starts explicitly.
    assert student.get(f"/student/exams/{exam_id}").headers["Location"].endswith(f"/student/exams/{exam_id}/attempts")
    page = student.get(f"/student/exams/{exam_id}/attempts").get_data(as_text=True)
    assert "1/3 attempts used" in page and "Start attempt 2" in page and "Choose this one" in page
    s = csrf(student, f"/student/exams/{exam_id}/attempts")
    student.post(f"/student/exams/{exam_id}/start", data={"csrf": s})
    _take(student, exam_id, {"q1": "0", "q2": "1"})

    other = app.test_client()
    login(other, "O", "o@x.edu", "student")
    assert other.post("/student/attempts/1/select", data={"csrf": csrf(other, "/student")}).status_code == 403

    student.post("/student/attempts/1/select", data={"csrf": s})
    states, certs = _attempts_state(app)
    assert [st[3] for st in states] == [True, False] and states[0][4] and certs == 1
    # Final: no second choice, no more attempts.
    student.post("/student/attempts/2/select", data={"csrf": s})
    assert [st[3] for st in _attempts_state(app)[0]] == [True, False]
    r = student.post(f"/student/exams/{exam_id}/start", data={"csrf": s})
    assert "No attempts left" in student.get(r.headers["Location"]).get_data(as_text=True)

    # Stats count only the chosen attempt.
    results = teacher.get(f"/teacher/exams/{exam_id}/results").get_data(as_text=True)
    assert "Counts" in results and "#2" in results
    with app.app_context():
        from app import _exam_stats
        assert _exam_stats(db.session.get(Exam, exam_id))["count"] == 1


def test_deadline_picks_best_attempt(app):
    teacher, student, t, exam_id = _setup(app)
    _multi(app, teacher, t, exam_id)
    _take(student, exam_id, {"q1": "0"})
    s = csrf(student, f"/student/exams/{exam_id}/attempts")
    student.post(f"/student/exams/{exam_id}/start", data={"csrf": s})
    _take(student, exam_id, {"q1": "0", "q2": "1"})
    student.post(f"/student/exams/{exam_id}/start", data={"csrf": s})
    _take(student, exam_id, {"q1": "0", "q2": "1"})
    with app.app_context():
        from datetime import timedelta

        from models import utcnow
        db.session.get(Exam, exam_id).selection_deadline = utcnow() - timedelta(minutes=1)
        db.session.commit()
    student.get("/student")
    states, certs = _attempts_state(app)
    # Best score wins; on a tie the earlier attempt.
    assert [st[3] for st in states] == [False, True, False] and states[1][4] and certs == 1


def test_cron_finalize_needs_secret_and_finalizes(app):
    app.config["GRADER_SECRET"] = "s3cret"
    teacher, student, t, exam_id = _setup(app)
    _multi(app, teacher, t, exam_id)
    _take(student, exam_id, {"q1": "0"})
    anon = app.test_client()
    assert anon.post("/api/cron/finalize").status_code == 401
    assert anon.post("/api/cron/finalize", json={}, headers={"x-grader-secret": "s3cret"}).get_json()["exams"] == 0
    with app.app_context():
        from datetime import timedelta

        from models import utcnow
        db.session.get(Exam, exam_id).selection_deadline = utcnow() - timedelta(minutes=1)
        db.session.commit()
    assert anon.post("/api/cron/finalize", json={}, headers={"x-grader-secret": "s3cret"}).get_json()["exams"] == 1
    assert _attempts_state(app)[0][0][3] is True


def test_concurrent_start_creates_one_attempt(app):
    from app import _start_attempt
    from models import User
    teacher, _, t, exam_id = _setup(app)
    _multi(app, teacher, t, exam_id)
    with app.app_context():
        exam = db.session.get(Exam, exam_id)
        sid = User.query.filter_by(email="s@x.edu").one().id
        # Both requests read "no attempts yet" before either inserted.
        assert _start_attempt(exam, sid, []) is not None
        assert _start_attempt(exam, sid, []) is None
        assert Submission.query.count() == 1


def _grant(teacher, t, exam_id, student_id=2, **form):
    return teacher.post(f"/teacher/exams/{exam_id}/students/{student_id}/retake",
                        data={"csrf": t, "understand": "on", **form})


def test_retake_grant_warns_exports_and_notifies(app, monkeypatch):
    import json

    import grader_client
    from models import RetakeTicket
    sent = []
    monkeypatch.setattr(grader_client, "notify", sent.append)
    teacher, student, t, exam_id = _setup(app)
    assert teacher.get(f"/teacher/exams/{exam_id}/students/2/retake").status_code == 404  # nothing to retake yet
    _take(student, exam_id, {"q1": "0"})

    page = teacher.get(f"/teacher/exams/{exam_id}/students/2/retake").get_data(as_text=True)
    assert "permanently deleted" in page and "attempts.json" in page
    export = teacher.get(f"/teacher/exams/{exam_id}/students/2/attempts.json")
    data = json.loads(export.data)
    assert "attachment" in export.headers["Content-Disposition"]
    assert data["attempts"][0]["answers"] == {"1": [0], "2": []} and data["attempts"][0]["certificate"]["status"] == "valid"
    assert data["attempts"][0]["questions"][0]["text"] == "First question?"

    teacher.post(f"/teacher/exams/{exam_id}/students/2/retake", data={"csrf": t})
    with app.app_context():
        assert RetakeTicket.query.count() == 0  # the "I understand" box is required
    _grant(teacher, t, exam_id)
    _grant(teacher, t, exam_id)
    with app.app_context():
        assert RetakeTicket.query.count() == 1
    assert [n["kind"] for n in sent] == ["retake_granted"]
    assert "Claim retake" in student.get("/student").get_data(as_text=True)


def test_claiming_retake_erases_attempts_and_invalidates_certificate(app, monkeypatch):
    import grader_client
    from models import AttemptEvent, Certificate, RetakeTicket
    sent = []
    monkeypatch.setattr(grader_client, "notify", sent.append)
    teacher, student, t, exam_id = _setup(app)
    _managed(app, teacher, t, exam_id, reentry_approval=None)
    s = csrf(student, f"/student/exams/{exam_id}")
    student.post("/submissions/1/events", data={"csrf": s, "type": "focus_lost"})
    student.post(f"/student/exams/{exam_id}", data={"csrf": s, "q1": "0"})
    with app.app_context():
        code = Certificate.query.one().code
    _grant(teacher, t, exam_id)

    other = app.test_client()
    login(other, "O", "o@x.edu", "student")
    assert other.post("/student/tickets/1/claim", data={"csrf": csrf(other, "/student")}).status_code == 403

    r = student.post("/student/tickets/1/claim", data={"csrf": s})
    assert r.headers["Location"].endswith(f"/student/exams/{exam_id}")
    with app.app_context():
        subs = Submission.query.all()
        assert [(a.attempt_no, a.status, a.selected, a.violations) for a in subs] == [(1, "in_progress", True, 0)]
        assert AttemptEvent.query.count() == 0
        cert = Certificate.query.one()
        assert cert.status == "invalidated" and cert.submission_id is None
        assert RetakeTicket.query.one().claimed_at is not None
    assert sent[-1]["kind"] == "invalidated"
    assert "Invalidated" in app.test_client().get(f"/verify/{code}").get_data(as_text=True)

    # One-way: the ticket cannot be used again.
    _take(student, exam_id, {"q1": "0"})
    r = student.post("/student/tickets/1/claim", data={"csrf": s})
    assert "already used" in student.get(r.headers["Location"]).get_data(as_text=True)


def test_expired_retake_cannot_be_claimed(app):
    teacher, student, t, exam_id = _setup(app)
    _take(student, exam_id, {"q1": "0"})
    _grant(teacher, t, exam_id, expires_at="2000-01-01T00:00")
    s = csrf(student, "/student")
    assert "Claim retake" not in student.get("/student").get_data(as_text=True)
    student.post("/student/tickets/1/claim", data={"csrf": s})
    with app.app_context():
        assert Submission.query.one().status == "graded"


def test_retake_scope_on_multi_attempt_exam(app):
    teacher, student, t, exam_id = _setup(app)
    _multi(app, teacher, t, exam_id)
    _take(student, exam_id, {"q1": "0"})
    s = csrf(student, "/student")
    student.post("/student/attempts/1/select", data={"csrf": s})

    _grant(teacher, t, exam_id, scope="one")
    student.post("/student/tickets/1/claim", data={"csrf": s})
    with app.app_context():
        assert [(a.attempt_no, a.selected) for a in Submission.query.all()] == [(1, True)]  # counts automatically
    _take(student, exam_id, {"q1": "0"})

    _grant(teacher, t, exam_id, scope="full")
    student.post("/student/tickets/2/claim", data={"csrf": s})
    _take(student, exam_id, {"q1": "0"})
    page = student.get(f"/student/exams/{exam_id}/attempts").get_data(as_text=True)
    assert "1/3 attempts used" in page and "Start attempt 2" in page and "Choose this one" in page


def test_withdraw_retake(app):
    from models import RetakeTicket
    teacher, student, t, exam_id = _setup(app)
    _take(student, exam_id, {"q1": "0"})
    _grant(teacher, t, exam_id)
    teacher.post("/teacher/tickets/1/withdraw", data={"csrf": t})
    with app.app_context():
        assert RetakeTicket.query.count() == 0


def test_revoke_certificate(app, monkeypatch):
    import grader_client
    from models import Certificate
    sent = []
    monkeypatch.setattr(grader_client, "notify", sent.append)
    teacher, student, t, exam_id = _setup(app)
    _take(student, exam_id, {"q1": "0", "q2": "1"})
    with app.app_context():
        code = Certificate.query.one().code
    assert "Revoke certificate" in teacher.get("/submissions/1").get_data(as_text=True)
    assert "Revoke certificate" not in student.get("/submissions/1").get_data(as_text=True)

    # 'Other' needs a description; students and other teachers cannot revoke.
    teacher.post("/teacher/submissions/1/revoke", data={"csrf": t, "reason": "other"})
    assert student.post("/teacher/submissions/1/revoke", data={"csrf": csrf(student, "/student"),
                                                              "reason": "misconduct"}).status_code == 403
    with app.app_context():
        assert Certificate.query.one().status == "valid"

    teacher.post("/teacher/submissions/1/revoke", data={"csrf": t, "reason": "misconduct", "note": "copied answers"})
    with app.app_context():
        cert = Certificate.query.one()
        assert (cert.status, cert.revoked_reason) == ("revoked", "Academic misconduct: copied answers")
        assert Submission.query.one().review == "revoked"
        from app import _exam_stats
        assert _exam_stats(db.session.get(Exam, exam_id)) is None
    assert sent[0]["kind"] == "revoked" and sent[0]["reason"] == "Academic misconduct: copied answers"
    assert "exam rules" in sent[0]["message"]

    verify = app.test_client().get(f"/verify/{code}").get_data(as_text=True)
    assert "Revoked" in verify and "copied answers" in verify and "exam rules" not in verify
    page = student.get("/submissions/1").get_data(as_text=True)
    assert "Certificate revoked" in page and "2/2" not in page and "Download" not in page
    assert "Revoked" in student.get("/student").get_data(as_text=True)

    # Permanent: no second revocation, and a retake does not turn it into "invalidated".
    assert teacher.post("/teacher/submissions/1/revoke", data={"csrf": t, "reason": "misconduct"}).status_code == 409
    _grant(teacher, t, exam_id)
    student.post("/student/tickets/1/claim", data={"csrf": csrf(student, "/student")})
    with app.app_context():
        assert Certificate.query.one().status == "revoked"


def test_pubsub_progress_and_tab_switch_flow(app, monkeypatch):
    import pubsub_client

    published_events = []
    real_publish = pubsub_client.publish_exam_event
    monkeypatch.setattr(
        pubsub_client,
        "publish_exam_event",
        lambda exam_id, event_type, data=None: published_events.append((exam_id, event_type, data))
        or real_publish(exam_id, event_type, data),
    )

    teacher, student, _, exam_id = _setup(app)

    # Local fallback mode when AZURE_WEBPUBSUB_CONNECTION_STRING is unset
    token_resp = teacher.get(f"/api/exams/{exam_id}/pubsub-token")
    assert token_resp.status_code == 200
    token_data = token_resp.get_json()
    assert token_data["enabled"] is False and token_data["group"] == f"exam_{exam_id}"

    # Another teacher cannot request token for this exam
    other_teacher = app.test_client()
    login(other_teacher, "Other", "other@x.edu", "teacher")
    assert other_teacher.get(f"/api/exams/{exam_id}/pubsub-token").status_code == 403

    # Configured mode returns a valid wss:// client access URL for the exam group
    app.config["AZURE_WEBPUBSUB_CONNECTION_STRING"] = (
        "Endpoint=https://demo.webpubsub.azure.com;AccessKey=0123456789abcdef0123456789abcdef;Version=1.0;"
    )
    app.config["AZURE_WEBPUBSUB_HUB"] = "quizcloud"
    token_cfg = teacher.get(f"/api/exams/{exam_id}/pubsub-token").get_json()
    assert token_cfg["enabled"] is True
    assert token_cfg["url"].startswith("wss://demo.webpubsub.azure.com/client/hubs/quizcloud?access_token=")
    app.config["AZURE_WEBPUBSUB_CONNECTION_STRING"] = ""

    # 1. Student starts exam -> attempt_started event published
    s = csrf(student, f"/student/exams/{exam_id}")
    assert any(ev[1] == "attempt_started" for ev in published_events)

    # 2. Student updates progress -> progress_updated event published and draft answers saved
    prog = student.post("/submissions/1/progress", data={"csrf": s, "q1": "0"}).get_json()
    assert prog["answered_count"] == 1 and prog["total_questions"] == 2
    assert published_events[-1][1] == "progress_updated"
    assert published_events[-1][2]["answered_count"] == 1

    # 3. Student switches tab -> tab_violation event published and violation stored in DB even on standard exam
    ev_resp = student.post("/submissions/1/events", data={"csrf": s, "type": "tab_switch", "detail": "switched browser tab"}).get_json()
    assert ev_resp["violations"] == 1
    assert published_events[-1][1] == "tab_violation"
    assert published_events[-1][2]["violations"] == 1
    assert _sub(app)["violations"] == 1 and _sub(app)["events"] == [("tab_switch", True)]

    # Live endpoint returns active attempt progress, events, and full submissions table snapshot
    live = teacher.get(f"/teacher/exams/{exam_id}/live.json").get_json()
    assert live["attempts"][0]["answered_count"] == 1 and live["attempts"][0]["violations"] == 1
    assert live["submissions"][0]["status"] == "in_progress" and live["submissions"][0]["answered_count"] == 1
    assert live["events"][0]["type"] == "tab_switch"

    # 4. Student submits exam -> attempt_submitted event published with final score
    student.post(f"/student/exams/{exam_id}", data={"csrf": s, "q1": "0", "q2": "1"})
    assert published_events[-1][1] == "attempt_submitted"
    assert published_events[-1][2]["status"] == "graded" and published_events[-1][2]["score"] == 2.0
    live_after = teacher.get(f"/teacher/exams/{exam_id}/live.json").get_json()
    assert live_after["attempts"] == []
    assert live_after["submissions"][0]["status"] == "graded" and live_after["submissions"][0]["score"] == 2.0
    assert live_after["stats"]["count"] == 1


def test_register_and_password_login_in_entra_mode(app):
    app.config["AUTH_MODE"] = "entra"
    c = app.test_client()

    # Login page offers both Microsoft Entra ID button and email/password + register link
    login_html = c.get("/login").get_data(as_text=True)
    assert "Sign in with Microsoft Entra ID" in login_html and "/auth/entra" in login_html and "/register" in login_html

    # Validation: password too short / mismatch
    token = csrf(c, "/register")
    bad = c.post("/register", data={
        "csrf": token, "name": "New User", "email": "new@x.edu",
        "password": "123", "confirm_password": "123", "role": "student",
    })
    assert "at least 6 characters" in bad.get_data(as_text=True)

    # Registration ignores any tampered role=teacher and always creates a student
    ok = c.post("/register", data={
        "csrf": token, "name": "New Student", "email": "new@x.edu",
        "password": "secret123", "confirm_password": "secret123", "role": "teacher",
    })
    assert ok.status_code == 302 and ok.headers["Location"].endswith("/")
    assert "New Student" in c.get("/student").get_data(as_text=True)
    assert c.get("/teacher").status_code == 403

    # Logout of a local user stays in the app (does not redirect to Microsoft logout)
    out = c.post("/logout", data={"csrf": csrf(c, "/student")})
    assert out.status_code == 302 and out.headers["Location"].endswith("/")

    # Duplicate email registration is rejected
    dup = c.post("/register", data={
        "csrf": csrf(c, "/register"), "name": "Dup", "email": "new@x.edu",
        "password": "secret123", "confirm_password": "secret123", "role": "student",
    })
    assert "already exists" in dup.get_data(as_text=True)

    # Wrong password fails, right password succeeds
    wrong = c.post("/login", data={"csrf": csrf(c, "/login"), "email": "new@x.edu", "password": "wrong"})
    assert "Invalid email or password" in wrong.get_data(as_text=True)
    right = c.post("/login", data={"csrf": csrf(c, "/login"), "email": "new@x.edu", "password": "secret123"})
    assert right.status_code == 302 and "New Student" in c.get("/student").get_data(as_text=True)


def test_private_exam_permissions_assignments_and_realtime_monitoring(app):
    from models import QuizAssignment

    teacher, other_teacher = app.test_client(), app.test_client()
    s_allowed, s_blocked, s_code = app.test_client(), app.test_client(), app.test_client()

    login(teacher, "Owner Teacher", "owner@school.edu", "teacher")
    login(other_teacher, "Other Teacher", "other_t@school.edu", "teacher")
    login(s_allowed, "Student Allowed", "allowed@school.edu", "student")
    login(s_blocked, "Student Blocked", "blocked@school.edu", "student")
    login(s_code, "Student Code", "codeuser@school.edu", "student")

    t = csrf(teacher, "/teacher")
    # Default visibility is 'private' with auto-generated 6-char access_code
    r = teacher.post("/teacher/exams/new", data={"csrf": t, "title": "Private Final Exam", "duration_minutes": "15"})
    exam_id = int(r.headers["Location"].rstrip("/").split("/")[-1])

    with app.app_context():
        exam = db.session.get(Exam, exam_id)
        assert exam.visibility == "private"
        assert exam.access_code and len(exam.access_code) == 6
        access_code = exam.access_code

    teacher.post(f"/teacher/exams/{exam_id}/questions", data={
        "csrf": t, "text": "Cloud question 1?", "options": ["Azure", "On-prem"], "correct": ["0"], "points": "2"})
    teacher.post(f"/teacher/exams/{exam_id}/publish", data={"csrf": t})

    # Another teacher is strictly blocked (403) from editing, assigning, or monitoring
    ot = csrf(other_teacher, "/teacher")
    assert other_teacher.get(f"/teacher/exams/{exam_id}").status_code == 403
    assert other_teacher.get(f"/teacher/exams/{exam_id}/students/search?q=allowed").status_code == 403
    assert other_teacher.post(f"/teacher/exams/{exam_id}/assignments",
                              data={"csrf": ot, "bulk_emails": "a@b.com"}).status_code == 403
    assert other_teacher.get(f"/teacher/exams/{exam_id}/results").status_code == 403
    assert other_teacher.get(f"/teacher/exams/{exam_id}/live.json").status_code == 403
    assert other_teacher.get(f"/api/exams/{exam_id}/pubsub-token").status_code == 403

    # Unassigned students are hidden from the exam management page until searched by email
    initial_manage = teacher.get(f"/teacher/exams/{exam_id}").get_data(as_text=True)
    assert "blocked@school.edu" not in initial_manage and "allowed@school.edu" not in initial_manage
    assert teacher.get(f"/teacher/exams/{exam_id}/students/search?q=al").get_json()["students"] == []
    found = teacher.get(f"/teacher/exams/{exam_id}/students/search?q=allowed@school.edu").get_json()["students"]
    assert len(found) == 1 and found[0]["email"] == "allowed@school.edu" and found[0]["already"] is False

    # Unassigned students cannot see the private exam on dashboard and get 403 on all direct URLs
    assert "Private Final Exam" not in s_blocked.get("/student").get_data(as_text=True)
    assert s_blocked.get(f"/student/exams/{exam_id}").status_code == 403
    assert s_blocked.get(f"/exam/{exam_id}").status_code == 403
    assert s_blocked.get(f"/student/exams/{exam_id}/attempts").status_code == 403
    assert s_blocked.post(f"/student/exams/{exam_id}/start",
                          data={"csrf": csrf(s_blocked, "/student")}).status_code == 403
    assert s_blocked.get(f"/api/exams/{exam_id}/pubsub-token").status_code == 403

    # Teacher assigns s_allowed via checkbox + bulk paste (including an Entra email not yet logged in, duplicates, invalid)
    teacher.post(f"/teacher/exams/{exam_id}/assignments", data={
        "csrf": t,
        "student_emails": ["allowed@school.edu"],
        "bulk_emails": "  ALLOWED@school.edu , future_entra@school.edu;\nnot-an-email\nfuture_entra@school.edu ",
    })
    manage_html = teacher.get(f"/teacher/exams/{exam_id}").get_data(as_text=True)
    assert "Đã thêm 2 học sinh" in manage_html
    assert "bỏ qua 2 email đã tồn tại" in manage_html
    assert "Đã có tài khoản" in manage_html and "Chờ đăng nhập" in manage_html

    # Realtime monitoring for private exam pre-populates assigned students with status 'not_started' (Chưa vào thi)
    live_init = teacher.get(f"/teacher/exams/{exam_id}/live.json").get_json()
    assert len(live_init["submissions"]) == 2
    assert {row["email"]: row["status"] for row in live_init["submissions"]} == {
        "allowed@school.edu": "not_started",
        "future_entra@school.edu": "not_started",
    }
    results_html = teacher.get(f"/teacher/exams/{exam_id}/results").get_data(as_text=True)
    assert "Chưa vào thi" in results_html

    # Assigned student sees the exam under "Bài thi được giao", can get Web PubSub token, and starts the exam
    allowed_dash = s_allowed.get("/student").get_data(as_text=True)
    assert "Private Final Exam" in allowed_dash and "Bài thi được giao" in allowed_dash
    assert s_allowed.get(f"/api/exams/{exam_id}/pubsub-token").status_code == 200

    # When s_allowed enters the exam, their row updates to 'in_progress' without duplicating rows
    s_tok = csrf(s_allowed, f"/student/exams/{exam_id}")
    live_mid = teacher.get(f"/teacher/exams/{exam_id}/live.json").get_json()
    assert len(live_mid["submissions"]) == 2
    assert {row["email"]: row["status"] for row in live_mid["submissions"]} == {
        "allowed@school.edu": "in_progress",
        "future_entra@school.edu": "not_started",
    }

    # Blocked student still gets 403 even on /submissions/<id>/progress
    assert s_blocked.post("/submissions/1/progress",
                          data={"csrf": csrf(s_blocked, "/student"), "q1": "0"}).status_code == 403

    # s_allowed submits -> row updates to 'graded' with score, still no duplicate rows
    s_allowed.post(f"/student/exams/{exam_id}", data={"csrf": s_tok, "q1": "0"})
    live_done = teacher.get(f"/teacher/exams/{exam_id}/live.json").get_json()
    assert len(live_done["submissions"]) == 2
    by_email = {row["email"]: row for row in live_done["submissions"]}
    assert by_email["allowed@school.edu"]["status"] == "graded"
    assert by_email["allowed@school.edu"]["score"] == 2.0
    assert by_email["future_entra@school.edu"]["status"] == "not_started"

    # Student s_code joins via access_code (wrong code fails, right code unlocks access)
    c_tok = csrf(s_code, "/student")
    bad_join = s_code.post("/student/join-code", data={"csrf": c_tok, "access_code": "WRONG1"}, follow_redirects=True)
    assert "Mã bài thi không hợp lệ" in bad_join.get_data(as_text=True)
    assert s_code.get(f"/student/exams/{exam_id}").status_code == 403

    ok_join = s_code.post("/student/join-code", data={"csrf": c_tok, "access_code": access_code.lower()},
                          follow_redirects=True)
    assert "Đã mở quyền truy cập bài thi" in ok_join.get_data(as_text=True)
    assert s_code.get(f"/exam/{exam_id}").status_code == 200

    # Teacher removes future_entra@school.edu from assignments
    with app.app_context():
        assign_row = QuizAssignment.query.filter_by(quiz_id=exam_id, student_email="future_entra@school.edu").one()
        aid = assign_row.id
    teacher.post(f"/teacher/exams/{exam_id}/assignments/{aid}/delete", data={"csrf": t})
    with app.app_context():
        assert QuizAssignment.query.filter_by(id=aid).first() is None

    # Teacher can regenerate access_code
    teacher.post(f"/teacher/exams/{exam_id}/access-code", data={"csrf": t})
    with app.app_context():
        new_code = db.session.get(Exam, exam_id).access_code
        assert new_code and len(new_code) == 6 and new_code != access_code


def test_auto_migration_from_legacy_sqlite_schema(tmp_path):
    import sqlite3

    from models import User

    db_file = tmp_path / "legacy.db"
    conn = sqlite3.connect(db_file)
    conn.executescript(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            external_id VARCHAR(128) NOT NULL UNIQUE,
            name VARCHAR(200) NOT NULL,
            email VARCHAR(255),
            role VARCHAR(20) NOT NULL,
            created_at DATETIME
        );
        CREATE TABLE exams (
            id INTEGER PRIMARY KEY,
            title VARCHAR(300) NOT NULL,
            description TEXT,
            duration_minutes INTEGER,
            pass_percent FLOAT,
            published BOOLEAN NOT NULL,
            policy JSON,
            max_attempts INTEGER NOT NULL,
            selection_deadline DATETIME,
            teacher_id INTEGER NOT NULL,
            created_at DATETIME,
            current_version_id INTEGER
        );
        CREATE TABLE questions (
            id INTEGER PRIMARY KEY,
            exam_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            options JSON NOT NULL,
            correct JSON NOT NULL,
            points FLOAT
        );
        INSERT INTO users (id, external_id, name, email, role) VALUES (1, 'dev:t@x.edu', 'T', 't@x.edu', 'teacher');
        INSERT INTO exams (id, title, duration_minutes, pass_percent, published, max_attempts, teacher_id)
        VALUES (1, 'Legacy Exam', 15, 50, 1, 1, 1);
        """
    )
    conn.commit()
    conn.close()

    migrated_app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_file}",
        "AUTH_MODE": "dev",
    })
    with migrated_app.app_context():
        exam = db.session.get(Exam, 1)
        user = db.session.get(User, 1)
        assert exam.visibility == "private"
        assert exam.access_code and len(exam.access_code) == 6
        assert user.password_hash is None
        db.engine.dispose()


def test_entra_common_personal_account_defaults_to_student(app, monkeypatch):
    import auth as auth_mod

    app.config["AUTH_MODE"] = "entra"

    class FakeMsal:
        def acquire_token_by_auth_code_flow(self, flow, args):
            return {"id_token_claims": {"sub": "msa-123", "name": "Guest User", "preferred_username": "guest@outlook.com"}}

    monkeypatch.setattr(auth_mod, "_msal_app", lambda: FakeMsal())
    c = app.test_client()
    r = c.get("/auth/callback?code=abc")
    assert r.status_code == 302 and r.headers["Location"].endswith("/")
    assert "Guest User" in c.get("/student").get_data(as_text=True)


def test_ai_generate_from_uploaded_documents(app):
    import io
    from docx import Document

    teacher, _, t, exam_id = _setup(app)

    # 1. Generate from uploaded .txt file (no textarea text)
    txt_bytes = io.BytesIO("Cloud computing separates compute and storage layers.".encode("utf-8"))
    r_txt = teacher.post(
        f"/teacher/exams/{exam_id}/generate-ai",
        data={"csrf": t, "lesson_text": "", "num_questions": "2", "lesson_file": (txt_bytes, "notes.txt")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert "Generated and added 2 question(s)" in r_txt.get_data(as_text=True)

    # 2. Generate from uploaded .docx file
    doc = Document()
    doc.add_paragraph("Amazon SQS decouples web servers from serverless Lambda workers.")
    doc_buf = io.BytesIO()
    doc.save(doc_buf)
    doc_buf.seek(0)
    r_docx = teacher.post(
        f"/teacher/exams/{exam_id}/generate-ai",
        data={"csrf": t, "lesson_text": "", "num_questions": "2", "lesson_file": (doc_buf, "lesson.docx")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert "Generated and added 2 question(s)" in r_docx.get_data(as_text=True)

    # 3. Reject unsupported extension cleanly
    bad_buf = io.BytesIO(b"binary")
    r_bad = teacher.post(
        f"/teacher/exams/{exam_id}/generate-ai",
        data={"csrf": t, "lesson_text": "", "num_questions": "2", "lesson_file": (bad_buf, "malware.exe")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert "Unsupported document format" in r_bad.get_data(as_text=True)



