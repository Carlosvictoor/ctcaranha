from collections import defaultdict
from datetime import date

from sqlalchemy import case, func

from app.extensions import db
from app.models import ClassSchedule, NotificationLog, Payment, Student, TrainingPlan


def dashboard_metrics():
    today = date.today()
    current_month = today.strftime("%Y-%m")

    active_students = Student.query.filter_by(active=True).count()
    overdue_payments = Payment.query.filter(Payment.status != "paid", Payment.due_date < today).count()
    pending_payments = Payment.query.filter(Payment.status == "pending").count()

    monthly_revenue = (
        Payment.query.with_entities(func.sum(Payment.amount))
        .filter(Payment.reference_month == current_month, Payment.status == "paid")
        .scalar()
        or 0
    )

    month_total = Payment.query.with_entities(func.sum(Payment.amount)).filter(Payment.reference_month == current_month).scalar() or 0
    month_progress_percent = (monthly_revenue / month_total * 100) if month_total else 0
    pending_amount = Payment.query.with_entities(func.sum(Payment.amount)).filter(Payment.status == "pending").scalar() or 0
    overdue_amount = Payment.query.with_entities(func.sum(Payment.amount)).filter(Payment.status == "late").scalar() or 0

    current_day_charges = (
        Payment.query.filter(
            Payment.due_date == today,
            Payment.status.in_(["pending", "late"]),
        )
        .order_by(Payment.student_id.asc())
        .limit(8)
        .all()
    )
    pending_students = (
        Payment.query.filter(Payment.status.in_(["pending", "late"]))
        .order_by(Payment.due_date.asc(), Payment.created_at.asc())
        .limit(5)
        .all()
    )
    for payment in pending_students:
        payment.days_until_due = (payment.due_date - today).days

    active_plans = TrainingPlan.query.filter_by(active=True).count()
    active_classes = ClassSchedule.query.filter_by(active=True).count()

    return {
        "active_students": active_students,
        "overdue_payments": overdue_payments,
        "pending_payments": pending_payments,
        "monthly_revenue": monthly_revenue,
        "month_total": month_total,
        "month_progress_percent": month_progress_percent,
        "pending_amount": pending_amount,
        "overdue_amount": overdue_amount,
        "current_month": current_month,
        "current_day_charges": current_day_charges,
        "pending_students": pending_students,
        "active_plans": active_plans,
        "active_classes": active_classes,
    }


def monthly_report_data():
    rows = (
        Payment.query.with_entities(
            Payment.reference_month,
            func.sum(Payment.amount).label("total"),
            func.sum(case((Payment.status == "paid", Payment.amount), else_=0)).label("received"),
        )
        .group_by(Payment.reference_month)
        .order_by(Payment.reference_month.desc())
        .limit(12)
        .all()
    )

    return rows


def plan_distribution():
    rows = (
        Student.query.with_entities(Student.plan, func.count(Student.id))
        .filter(Student.active.is_(True))
        .group_by(Student.plan)
        .all()
    )
    return rows


def payment_status_distribution():
    totals = defaultdict(int)
    for status, count in Payment.query.with_entities(Payment.status, func.count(Payment.id)).group_by(Payment.status).all():
        totals[status] = count
    return totals


def recent_notifications(limit=10):
    return NotificationLog.query.order_by(NotificationLog.created_at.desc()).limit(limit).all()


def class_schedule_overview():
    rows = (
        db.session.query(
            ClassSchedule.id,
            ClassSchedule.title,
            ClassSchedule.day_of_week,
            ClassSchedule.start_time,
            ClassSchedule.end_time,
            ClassSchedule.level,
            ClassSchedule.active,
            func.count(Student.id),
        )
        .outerjoin(Student, Student.class_schedule_id == ClassSchedule.id)
        .group_by(ClassSchedule.id)
        .order_by(ClassSchedule.day_of_week.asc(), ClassSchedule.start_time.asc())
        .all()
    )
    # Format time range for display
    return [(row[0], row[1], row[2], f"{row[3]}-{row[4]}", row[5], row[6], row[7]) for row in rows]


def training_plan_rows():
    return (
        db.session.query(
            TrainingPlan.id,
            TrainingPlan.name,
            TrainingPlan.monthly_fee,
            TrainingPlan.active,
            func.count(Student.id),
        )
        .outerjoin(Student, Student.plan_id == TrainingPlan.id)
        .group_by(TrainingPlan.id)
        .order_by(TrainingPlan.name.asc())
        .all()
    )