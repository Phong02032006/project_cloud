from datetime import datetime, timedelta, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


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
    submissions = db.relationship("Submission", backref="exam", cascade="all, delete-orphan")

    # questions of the current version; kept the old name so existing callers work unchanged
    @property
    def questions(self):
        return self.current_version.questions if self.current_version else []

    @property
    def max_score(self):
        return sum(q.points for q in self.questions)

    # the only way to change the question set: snapshot a new version and move the ptr to it
    def new_version(self, question_ids):
        version = ExamVersion(exam=self, question_ids=list(question_ids), pass_percent=self.pass_percent,
                              duration_minutes=self.duration_minutes)
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
    created_at = db.Column(db.DateTime, default=utcnow)

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
    certificate_key = db.Column(db.String(500))
    certificate_id = db.Column(db.String(20))
    status = db.Column(db.String(20), default="pending")  # in_progress | pending | graded | error
    started_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    submitted_at = db.Column(db.DateTime, default=utcnow)

    student = db.relationship("User")
    version = db.relationship("ExamVersion")

    @property
    def deadline(self):
        return self.started_at + timedelta(minutes=self.version.duration_minutes)
