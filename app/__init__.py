import os
from calendar import monthrange
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, flash
from sqlalchemy import inspect, text

from app.extensions import db, login_manager, scheduler
from app.models import AppSettings, ClassSchedule, Payment, Student, TrainingPlan, User, get_app_settings


def resolve_database_uri(app):
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
        elif database_url.startswith("postgresql://") and "+" not in database_url.split("://", 1)[0]:
            database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return database_url

    sqlite_path = os.getenv("SQLITE_PATH")
    if sqlite_path:
        sqlite_file = Path(sqlite_path).expanduser()
        if not sqlite_file.is_absolute():
            sqlite_file = Path(app.root_path).parent / sqlite_file
        sqlite_file.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{sqlite_file.resolve()}"

    return f"sqlite:///{Path(app.root_path) / 'ctc_aranha.db'}"


def create_app():
    load_dotenv()
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "ctc-aranha-secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = resolve_database_uri(app)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["REMEMBER_COOKIE_HTTPONLY"] = True
    app.config["BACKUP_DIR"] = str(Path(app.root_path).parent / "backups")
    app.config["DISABLE_SCHEDULER"] = os.getenv("DISABLE_SCHEDULER", "0") == "1"

    db.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        db.create_all()
        ensure_schema_updates()
        seed_database()
        ensure_monthly_payments()

    from app.routes import register_routes

    register_routes(app)
    configure_scheduler(app)

    @app.context_processor
    def inject_now():
        return {"current_year": datetime.now().year, "app_settings": get_app_settings()}

    @app.template_filter("currency")
    def currency_filter(value):
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @app.template_filter("datebr")
    def date_filter(value):
        if not value:
            return "-"
        return value.strftime("%d/%m/%Y")

    @app.template_filter("statusbr")
    def status_filter(value):
        labels = {
            "pending": "pendente",
            "late": "vencida",
            "paid": "paga",
            "queued": "na fila",
            "sent": "enviado",
            "delivered": "entregue",
            "opened": "aberto",
            "manual-required": "manual",
        }
        return labels.get(value, value)

    @app.errorhandler(404)
    def not_found(_error):
        flash("Pagina nao encontrada.", "warning")
        from flask import redirect, url_for

        return redirect(url_for("dashboard"))

    return app


def ensure_schema_updates():
    inspector = inspect(db.engine)
    columns = {column["name"] for column in inspector.get_columns("student")}

    with db.engine.begin() as connection:
        if "plan_id" not in columns:
            connection.execute(text("ALTER TABLE student ADD COLUMN plan_id INTEGER"))
        if "class_schedule_id" not in columns:
            connection.execute(text("ALTER TABLE student ADD COLUMN class_schedule_id INTEGER"))


def seed_database():
    if not AppSettings.query.first():
        db.session.add(
            AppSettings(
                gym_name="CTC Aranha",
                whatsapp_template=(
                    "Ola, {student_name}. Aqui e a equipe da {gym_name}. "
                    "Sua mensalidade de {amount} vence em {due_date}. "
                    "Se ja realizou o pagamento, desconsidere esta mensagem. Oss!"
                ),
                reminder_days_before=3,
            )
        )

    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin")
        admin.set_password("ctc123")
        db.session.add(admin)

    if TrainingPlan.query.count() == 0:
        db.session.add_all(
            [
                TrainingPlan(name="Muay Thai Iniciante", monthly_fee=180.0, due_day=5, description="Plano de entrada com foco em base e condicionamento."),
                TrainingPlan(name="Muay Thai Competicao", monthly_fee=240.0, due_day=10, description="Treinos intensivos, sparring e preparacao para eventos."),
                TrainingPlan(name="Kids", monthly_fee=150.0, due_day=15, description="Turma infantil com foco em disciplina e coordenacao."),
            ]
        )

    if ClassSchedule.query.count() == 0:
        db.session.add_all(
            [
                ClassSchedule(title="Turma Noite", day_of_week="Segunda e Quarta", start_time="19:00", end_time="20:15", coach="Mestre Aranha", level="Misto"),
                ClassSchedule(title="Turma Competicao", day_of_week="Terca e Quinta", start_time="20:15", end_time="21:30", coach="Instrutor Rafael", level="Avancado"),
                ClassSchedule(title="Kids Manha", day_of_week="Sabado", start_time="09:00", end_time="10:00", coach="Instrutora Larissa", level="Kids"),
            ]
        )

    db.session.flush()

    if Student.query.count() == 0:
        plans = {plan.name: plan for plan in TrainingPlan.query.all()}
        schedules = {schedule.title: schedule for schedule in ClassSchedule.query.all()}
        default_schedule = next(iter(schedules.values()), None)
        students = [
            Student(
                full_name="Rafael Silva",
                phone="+5511999991111",
                email="rafael@ctcaranha.com",
                plan="Muay Thai Iniciante",
                monthly_fee=180.0,
                due_day=5,
                plan_id=plans["Muay Thai Iniciante"].id,
                class_schedule_id=(schedules.get("Turma Noite") or default_schedule).id if default_schedule else None,
            ),
            Student(
                full_name="Larissa Costa",
                phone="+5511988882222",
                email="larissa@ctcaranha.com",
                plan="Muay Thai Competicao",
                monthly_fee=240.0,
                due_day=10,
                plan_id=plans["Muay Thai Competicao"].id,
                class_schedule_id=(schedules.get("Turma Competicao") or default_schedule).id if default_schedule else None,
            ),
            Student(
                full_name="Joao Victor",
                phone="+5511977773333",
                email="joao@ctcaranha.com",
                plan="Kids",
                monthly_fee=150.0,
                due_day=15,
                plan_id=plans["Kids"].id,
                class_schedule_id=(schedules.get("Kids Manha") or default_schedule).id if default_schedule else None,
            ),
        ]
        db.session.add_all(students)

    for student in Student.query.filter(Student.plan_id.is_(None)).all():
        matching_plan = TrainingPlan.query.filter_by(name=student.plan).first()
        if matching_plan:
            student.plan_id = matching_plan.id

    db.session.commit()


def ensure_monthly_payments(reference_month=None):
    if reference_month is None:
        today = date.today()
        reference_month = today.strftime("%Y-%m")

    for student in Student.query.filter_by(active=True).all():
        existing = Payment.query.filter_by(student_id=student.id, reference_month=reference_month).first()
        if existing:
            continue

        payment = Payment(
            student_id=student.id,
            reference_month=reference_month,
            amount=student.monthly_fee,
            due_date=resolve_payment_due_date(student, reference_month),
            status="pending",
        )
        db.session.add(payment)

    db.session.commit()
    update_overdue_statuses()


def next_reference_month(reference_month):
    year, month = [int(part) for part in reference_month.split("-")]
    if month == 12:
        return f"{year + 1}-01"
    return f"{year}-{month + 1:02d}"


def add_one_month(base_date):
    return add_months(base_date, 1)


def add_months(base_date, months):
    month_index = (base_date.month - 1) + months
    year = base_date.year + (month_index // 12)
    month = (month_index % 12) + 1
    day = min(base_date.day, monthrange(year, month)[1])
    return date(year, month, day)


def resolve_payment_due_date(student, reference_month):
    previous_payment = (
        Payment.query.filter(
            Payment.student_id == student.id,
            Payment.reference_month < reference_month,
        )
        .order_by(Payment.reference_month.desc(), Payment.created_at.desc())
        .first()
    )

    if previous_payment:
        previous_year, previous_month = [int(part) for part in previous_payment.reference_month.split("-")]
        current_year, current_month = [int(part) for part in reference_month.split("-")]
        months_ahead = ((current_year - previous_year) * 12) + (current_month - previous_month)
        anchor_date = previous_payment.paid_at.date() if previous_payment.paid_at else previous_payment.due_date
        return add_months(anchor_date, max(months_ahead, 1))

    today = date.today()
    if reference_month == today.strftime("%Y-%m"):
        return today

    year, month = [int(part) for part in reference_month.split("-")]
    day = min(today.day, monthrange(year, month)[1])
    return date(year, month, day)


def ensure_student_payment_for_month(student, reference_month):
    existing = Payment.query.filter_by(student_id=student.id, reference_month=reference_month).first()
    if existing:
        return existing

    payment = Payment(
        student_id=student.id,
        reference_month=reference_month,
        amount=student.monthly_fee,
        due_date=resolve_payment_due_date(student, reference_month),
        status="pending",
    )
    db.session.add(payment)
    db.session.commit()
    update_overdue_statuses()
    return payment


def update_overdue_statuses():
    today = date.today()
    overdue_items = Payment.query.filter(Payment.status == "pending", Payment.due_date < today).all()
    for payment in overdue_items:
        payment.status = "late"
    db.session.commit()


def process_automatic_reminders(app):
    from app.services.whatsapp import is_twilio_configured, send_whatsapp_reminder

    with app.app_context():
        if not is_twilio_configured():
            return

        ensure_monthly_payments()
        settings = get_app_settings()
        reminder_limit = date.today()
        if settings.reminder_days_before > 0:
            from datetime import timedelta

            reminder_limit = date.today() + timedelta(days=settings.reminder_days_before)

        target_payments = Payment.query.filter(
            Payment.status.in_(["pending", "late"]),
            Payment.reminder_sent_at.is_(None),
            Payment.due_date <= reminder_limit,
        ).all()

        for payment in target_payments:
            send_whatsapp_reminder(payment)


def configure_scheduler(app):
    if app.config.get("DISABLE_SCHEDULER"):
        return

    if scheduler.running:
        return

    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    scheduler.add_job(
        id="automatic_whatsapp_reminders",
        func=lambda: process_automatic_reminders(app),
        trigger="cron",
        hour=9,
        minute=0,
        replace_existing=True,
    )
    scheduler.start()


app = create_app()