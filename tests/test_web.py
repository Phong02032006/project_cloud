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
                                                 "pass_percent": "60"})
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
    r = teacher.post("/teacher/exams/new", data={"csrf": t, "title": "E"})
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
    r = teacher.post("/teacher/exams/new", data={"csrf": t, "title": "Async"})
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
    r = teacher.post("/teacher/exams/new", data={"csrf": t, "title": "E"})
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
    r = teacher.post("/teacher/exams/new", data={"csrf": t, "title": "E", "duration_minutes": duration})
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
