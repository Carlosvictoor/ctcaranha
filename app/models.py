from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class AppSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gym_name = db.Column(db.String(120), nullable=False, default="CTC Aranha")
    whatsapp_template = db.Column(
        db.Text,
        nullable=False,
        default=(
            "Ola, {student_name}. Aqui e a equipe da {gym_name}. "
            "Sua mensalidade de {amount} vence em {due_date}. "
            "Se ja realizou o pagamento, desconsidere esta mensagem. Oss!"
        ),
    )
    reminder_days_before = db.Column(db.Integer, nullable=False, default=3)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class TrainingPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    monthly_fee = db.Column(db.Float, nullable=False)
    due_day = db.Column(db.Integer, nullable=False, default=10)
    description = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    students = db.relationship("Student", backref="training_plan", lazy=True)


class ClassSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    day_of_week = db.Column(db.String(20), nullable=False)
    start_time = db.Column(db.String(5), nullable=False)
    end_time = db.Column(db.String(5), nullable=False)
    coach = db.Column(db.String(120))
    level = db.Column(db.String(80))
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    students = db.relationship("Student", backref="class_schedule", lazy=True)


def get_app_settings():
    settings = AppSettings.query.first()
    if settings:
        return settings

    return AppSettings(
        gym_name="CTC Aranha",
        whatsapp_template=(
            "Ola, {student_name}. Aqui e a equipe da {gym_name}. "
            "Sua mensalidade de {amount} vence em {due_date}. "
            "Se ja realizou o pagamento, desconsidere esta mensagem. Oss!"
        ),
        reminder_days_before=3,
    )


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(120))
    plan_id = db.Column(db.Integer, db.ForeignKey("training_plan.id"))
    class_schedule_id = db.Column(db.Integer, db.ForeignKey("class_schedule.id"))
    plan = db.Column(db.String(80), nullable=False)
    monthly_fee = db.Column(db.Float, nullable=False)
    due_day = db.Column(db.Integer, nullable=False, default=10)
    active = db.Column(db.Boolean, default=True, nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    payments = db.relationship("Payment", backref="student", lazy=True, cascade="all, delete-orphan")


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    reference_month = db.Column(db.String(7), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    paid_at = db.Column(db.DateTime)
    reminder_sent_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class NotificationLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.Integer, db.ForeignKey("payment.id"), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    message = db.Column(db.Text, nullable=False)
    provider = db.Column(db.String(40), nullable=False)
    status = db.Column(db.String(40), nullable=False)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


def active_training_plans():
    return TrainingPlan.query.filter_by(active=True).order_by(TrainingPlan.name.asc()).all()


def active_class_schedules():
    return ClassSchedule.query.filter_by(active=True).order_by(ClassSchedule.day_of_week.asc(), ClassSchedule.start_time.asc()).all()