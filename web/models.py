from datetime import datetime, timedelta, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


# Managed-mode settings. Violations are always logged when managed is on; the rest are opt-in actions.
DEFAULT_POLICY = {
    "managed": False,
    "fullscreen": True,
    "reentry_approval": True,
    "withhold_if_flagged": False,
    "autosubmit_after": None,  # int N, or None for no auto-submit
    "allow_copy": False,
    "allow_paste": False,
    "allow_context_menu": False,
}


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    # Entra object id (oid claim), or "dev:<email>" in dev auth mode.
    external_id = db.Column(db.String(128), unique=True, nullable=False)
    name = db.Column(db.Unicode(200), nullable=False)
    email = db.Column(db.String(255))
    role = db.Column(db.String(20), nullable=False)  # "teacher" | "student"
    created_at = db.Column(db.DateTime, default=utcnow)


class Exam(db.Model):
    __tablename__ = "exams"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Unicode(300), nullable=False)
    description = db.Column(db.UnicodeText, default="")
    duration_minutes = db.Column(db.Integer, default=15)
    pass_percent = db.Column(db.Float, default=50)
    published = db.Column(db.Boolean, default=False, nullable=False)
    policy = db.Column(db.JSON)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)

    # ptr to the version new attempts get; restore = just move this
    # use_alter: exams <-> exam_versions point at each other, so this FK is added after both tables exist
    current_version_id = db.Column(db.Integer, db.ForeignKey("exam_versions.id", use_alter=True,
                                                             name="fk_exams_current_version"))

    teacher = db.relationship("User")
    # post_update: set the ptr in a separate UPDATE after insert (and null it before delete) to break the cycle
    current_version = db.relationship("ExamVersion", foreign_keys=[current_version_id], post_update=True)
    versions = db.relationship("ExamVersion", foreign_keys="ExamVersion.exam_id", backref="exam",
                               cascade="all, delete-orphan", order_by="ExamVersion.id")
    # every question row this exam ever owned; only here so deleting the exam cleans them up
    question_rows = db.relationship("Question", backref="exam", cascade="all, delete-orphan")
    certificates = db.relationship("Certificate", backref="exam", cascade="all, delete-orphan")
    submissions = db.relationship("Submission", backref="exam", cascade="all, delete-orphan")

    # questions of the current version; kept the old name so existing callers work unchanged
    @property
    def questions(self):
        return self.current_version.questions if self.current_version else []

    @property
    def max_score(self):
        return sum(q.points for q in self.questions)

    # the only way to change the question set: snapshot a new version and move the ptr to it
    @property
    def settings(self):
        return {**DEFAULT_POLICY, **(self.policy or {})}

    def new_version(self, question_ids):
        version = ExamVersion(exam=self, question_ids=list(question_ids), pass_percent=self.pass_percent,
                              duration_minutes=self.duration_minutes, policy=self.settings)
        db.session.add(version)
        self.current_version = version
        return version


# immutable snapshot of an exam; never updated after insert
# attempts pin one of these, so editing the exam never touches a running or graded attempt
class ExamVersion(db.Model):
    __tablename__ = "exam_versions"
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("exams.id"), nullable=False)
    question_ids = db.Column(db.JSON, nullable=False)  # ordered Question.id list; rows are never modified
    # copied from the exam at snapshot time since they affect grading / the deadline
    pass_percent = db.Column(db.Float, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    policy = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=utcnow)

    @property
    def settings(self):
        return {**DEFAULT_POLICY, **(self.policy or {})}

    # one IN query, then reorder by question_ids since IN gives no order guarantee
    @property
    def questions(self):
        rows = {q.id: q for q in Question.query.filter(Question.id.in_(self.question_ids))}
        return [rows[i] for i in self.question_ids]

    @property
    def max_score(self):
        return sum(q.points for q in self.questions)


class Question(db.Model):
    __tablename__ = "questions"
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("exams.id"), nullable=False)
    text = db.Column(db.UnicodeText, nullable=False)  # rows are insert-only, so ids stay stable across versions
    options = db.Column(db.JSON, nullable=False)  # ["option A", "option B", ...]
    correct = db.Column(db.JSON, nullable=False)  # indices into options, e.g. [0] or [0, 2]
    points = db.Column(db.Float, default=1)

    @property
    def is_multi(self):
        return len(self.correct) > 1


class Submission(db.Model):
    __tablename__ = "submissions"
    __table_args__ = (db.UniqueConstraint("exam_id", "student_id", name="uq_one_attempt"),)
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("exams.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    version_id = db.Column(db.Integer, db.ForeignKey("exam_versions.id"), nullable=False)  # pinned at start
    answers = db.Column(db.JSON, nullable=False)
    details = db.Column(db.JSON)
    score = db.Column(db.Float)
    max_score = db.Column(db.Float)
    percent = db.Column(db.Float)
    passed = db.Column(db.Boolean)
    status = db.Column(db.String(20), default="pending")  # in_progress | pending | graded | error
    started_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    submitted_at = db.Column(db.DateTime, default=utcnow)
    # Managed mode: last heartbeat, pending re-entry approval, counted violations.
    last_seen_at = db.Column(db.DateTime)
    locked_at = db.Column(db.DateTime)
    lock_reason = db.Column(db.String(30))
    violations = db.Column(db.Integer, default=0, nullable=False)
    review = db.Column(db.String(20))  # None | withheld | released | cancelled

    student = db.relationship("User")
    version = db.relationship("ExamVersion")
    certificate = db.relationship("Certificate", uselist=False, backref="submission")
    events = db.relationship("AttemptEvent", backref="submission", cascade="all, delete-orphan",
                             order_by="AttemptEvent.id")

    @property
    def result_hidden(self):
        """Withheld or cancelled results are visible to the teacher only."""
        return self.review in ("withheld", "cancelled")

    @property
    def deadline(self):
        return self.started_at + timedelta(minutes=self.version.duration_minutes)


class AttemptEvent(db.Model):
    """Append-only managed-mode log; `at` is always server time."""
    __tablename__ = "attempt_events"
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey("submissions.id"), nullable=False, index=True)
    type = db.Column(db.String(30), nullable=False)
    detail = db.Column(db.Unicode(300))
    counted = db.Column(db.Boolean, default=False, nullable=False)
    at = db.Column(db.DateTime, default=utcnow, nullable=False)


class Certificate(db.Model):
    """Lives apart from the attempt so its status can still be verified after a retake deletes the attempt.
    The PDF itself is rendered by the Lambda grader and stored on S3 (or locally in demo mode)."""
    __tablename__ = "certificates"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)  # printed on the PDF, used in /verify/<code>
    exam_id = db.Column(db.Integer, db.ForeignKey("exams.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    submission_id = db.Column(db.Integer, db.ForeignKey("submissions.id"))  # NULL once the attempt is deleted
    s3_key = db.Column(db.String(500))
    status = db.Column(db.String(20), default="issuing", nullable=False)  # issuing | valid | invalidated | revoked
    issued_at = db.Column(db.DateTime)
    status_changed_at = db.Column(db.DateTime)

    student = db.relationship("User")
