from datetime import date, datetime
from pathlib import Path

from flask import Response, current_app, flash, redirect, render_template, request, send_file, send_from_directory, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app import add_one_month, ensure_monthly_payments, ensure_student_payment_for_month, next_reference_month, process_automatic_reminders
from app.extensions import db
from app.models import ClassSchedule, Payment, Student, TrainingPlan, User, active_class_schedules, active_training_plans, get_app_settings
from app.services.admin import create_database_backup, list_backups
from app.services.exports import build_reports_csv, build_reports_pdf
from app.services.reports import (
    class_schedule_overview,
    dashboard_metrics,
    monthly_report_data,
    payment_status_distribution,
    plan_distribution,
    recent_notifications,
    training_plan_rows,
)
from app.services.whatsapp import is_twilio_configured, register_manual_whatsapp_click, send_whatsapp_reminder


def normalize_phone(raw_phone):
    cleaned = "".join(char for char in (raw_phone or "") if char.isdigit() or char == "+")
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    if cleaned and not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    return cleaned


def parse_student_form(form):
    full_name = form.get("full_name", "").strip()
    phone = normalize_phone(form.get("phone", "").strip())
    email = form.get("email", "").strip()
    plan = form.get("plan_name", "").strip()
    notes = form.get("notes", "").strip()
    active = form.get("active") == "on"

    plan_id = form.get("plan_id", type=int)
    class_schedule_id = form.get("class_schedule_id", type=int)

    selected_plan = TrainingPlan.query.get(plan_id) if plan_id else None
    if selected_plan:
        plan = selected_plan.name

    if not full_name:
        return None, "Informe o nome completo do aluno."

    if not phone or len(phone.replace("+", "")) < 10:
        return None, "Informe um WhatsApp valido com DDD."

    if not plan:
        return None, "Informe o plano do aluno."

    try:
        monthly_fee = float(form.get("monthly_fee", 0) or 0)
    except (TypeError, ValueError):
        return None, "Informe um valor de mensalidade valido."

    if monthly_fee <= 0:
        return None, "A mensalidade deve ser maior que zero."

    return {
        "full_name": full_name,
        "phone": phone,
        "email": email,
        "plan_id": selected_plan.id if selected_plan else None,
        "class_schedule_id": class_schedule_id,
        "plan": plan,
        "monthly_fee": monthly_fee,
        "notes": notes,
        "active": active,
    }, None


def parse_settings_form(form, fallback_template):
    gym_name = form.get("gym_name", "CTC Aranha").strip() or "CTC Aranha"
    whatsapp_template = form.get("whatsapp_template", "").strip() or fallback_template

    try:
        reminder_days_before = int(form.get("reminder_days_before", 3) or 3)
    except (TypeError, ValueError):
        return None, "Informe um numero valido de dias para o lembrete automatico."

    if reminder_days_before < 0 or reminder_days_before > 30:
        return None, "Os lembretes automaticos devem ficar entre 0 e 30 dias."

    return {
        "gym_name": gym_name,
        "whatsapp_template": whatsapp_template,
        "reminder_days_before": reminder_days_before,
    }, None


def register_routes(app):
    @app.route("/", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user = User.query.filter_by(username=username).first()

            if user and user.check_password(password):
                login_user(user)
                flash("Login realizado com sucesso.", "success")
                return redirect(url_for("dashboard"))

            flash("Usuario ou senha invalidos.", "danger")

        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("Sessao encerrada.", "info")
        return redirect(url_for("login"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        ensure_monthly_payments()
        metrics = dashboard_metrics()
        return render_template("dashboard.html", metrics=metrics, today=date.today(), use_twilio=is_twilio_configured())

    @app.route("/estrutura", methods=["GET", "POST"])
    @login_required
    def structure():
        form_name = request.form.get("form_name")

        if request.method == "POST" and form_name == "plan":
            plan_name = request.form.get("name", "").strip()
            if not plan_name:
                flash("Informe um nome para o plano.", "danger")
                return redirect(url_for("structure"))

            if TrainingPlan.query.filter_by(name=plan_name).first():
                flash("Ja existe um plano com esse nome.", "warning")
                return redirect(url_for("structure"))

            plan = TrainingPlan(
                name=plan_name,
                monthly_fee=float(request.form.get("monthly_fee", 0) or 0),
                description=request.form.get("description", "").strip(),
                active=request.form.get("active") == "on",
            )
            db.session.add(plan)
            db.session.commit()
            flash("Plano cadastrado com sucesso.", "success")
            return redirect(url_for("structure"))

        if request.method == "POST" and form_name == "schedule":
            title = request.form.get("title", "").strip()
            if not title:
                flash("Informe um nome para a turma.", "danger")
                return redirect(url_for("structure"))

            schedule = ClassSchedule(
                title=title,
                day_of_week=request.form.get("day_of_week", "").strip(),
                start_time=request.form.get("start_time", "").strip(),
                end_time=request.form.get("end_time", "").strip(),
                coach=request.form.get("coach", "").strip(),
                level=request.form.get("level", "").strip(),
                active=request.form.get("active") == "on",
            )
            db.session.add(schedule)
            db.session.commit()
            flash("Turma cadastrada com sucesso.", "success")
            return redirect(url_for("structure"))

        return render_template(
            "structure.html",
            plan_rows=training_plan_rows(),
            class_rows=class_schedule_overview(),
        )

    @app.post("/estrutura/planos/<int:plan_id>/status")
    @login_required
    def toggle_plan_status(plan_id):
        plan = TrainingPlan.query.get_or_404(plan_id)
        plan.active = not plan.active
        db.session.commit()
        flash("Status do plano atualizado.", "info")
        return redirect(url_for("structure"))

    @app.post("/estrutura/planos/<int:plan_id>/excluir")
    @login_required
    def delete_plan(plan_id):
        plan = TrainingPlan.query.get_or_404(plan_id)
        if plan.students:
            flash("Nao e possivel excluir um plano com alunos vinculados.", "warning")
            return redirect(url_for("structure"))

        db.session.delete(plan)
        db.session.commit()
        flash("Plano excluido com sucesso.", "success")
        return redirect(url_for("structure"))

    @app.post("/estrutura/turmas/<int:schedule_id>/status")
    @login_required
    def toggle_schedule_status(schedule_id):
        schedule = ClassSchedule.query.get_or_404(schedule_id)
        schedule.active = not schedule.active
        db.session.commit()
        flash("Status da turma atualizado.", "info")
        return redirect(url_for("structure"))

    @app.post("/estrutura/turmas/<int:schedule_id>/excluir")
    @login_required
    def delete_schedule(schedule_id):
        schedule = ClassSchedule.query.get_or_404(schedule_id)
        if schedule.students:
            flash("Nao e possivel excluir uma turma com alunos vinculados.", "warning")
            return redirect(url_for("structure"))

        db.session.delete(schedule)
        db.session.commit()
        flash("Turma excluida com sucesso.", "success")
        return redirect(url_for("structure"))

    @app.route("/configuracoes", methods=["GET", "POST"])
    @login_required
    def settings():
        settings_record = get_app_settings()

        if request.method == "POST":
            settings_data, error_message = parse_settings_form(request.form, settings_record.whatsapp_template)
            if error_message:
                flash(error_message, "danger")
                return render_template(
                    "settings.html",
                    settings=settings_record,
                    placeholders=["{student_name}", "{gym_name}", "{amount}", "{due_date}"],
                    notification_rows=recent_notifications(limit=12),
                    backups=list_backups(current_app),
                    use_twilio=is_twilio_configured(),
                )

            settings_record.gym_name = settings_data["gym_name"]
            settings_record.reminder_days_before = settings_data["reminder_days_before"]
            settings_record.whatsapp_template = settings_data["whatsapp_template"]

            if settings_record.id is None:
                db.session.add(settings_record)

            db.session.commit()
            flash("Configuracoes atualizadas com sucesso.", "success")
            return redirect(url_for("settings"))

        placeholders = ["{student_name}", "{gym_name}", "{amount}", "{due_date}"]
        notification_rows = recent_notifications(limit=12)
        return render_template(
            "settings.html",
            settings=settings_record,
            placeholders=placeholders,
            notification_rows=notification_rows,
            backups=list_backups(current_app),
            use_twilio=is_twilio_configured(),
        )

    @app.post("/configuracoes/senha")
    @login_required
    def change_password():
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not current_user.check_password(current_password):
            flash("A senha atual esta incorreta.", "danger")
            return redirect(url_for("settings"))

        if len(new_password) < 8:
            flash("A nova senha deve ter pelo menos 8 caracteres.", "warning")
            return redirect(url_for("settings"))

        if new_password != confirm_password:
            flash("A confirmacao da nova senha nao confere.", "warning")
            return redirect(url_for("settings"))

        current_user.set_password(new_password)
        db.session.commit()
        flash("Senha do administrador atualizada.", "success")
        return redirect(url_for("settings"))

    @app.post("/configuracoes/backup")
    @login_required
    def create_backup():
        backup_path = create_database_backup(current_app)
        flash(f"Backup gerado: {backup_path.name}", "success")
        return redirect(url_for("settings"))

    @app.get("/configuracoes/backup/<path:filename>")
    @login_required
    def download_backup(filename):
        return send_from_directory(current_app.config["BACKUP_DIR"], Path(filename).name, as_attachment=True)

    @app.route("/alunos")
    @login_required
    def students():
        query = Student.query.order_by(Student.active.desc(), Student.full_name.asc())
        search = request.args.get("search", "").strip()
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                Student.full_name.ilike(search_term)
                | Student.phone.ilike(search_term)
                | Student.email.ilike(search_term)
                | Student.plan.ilike(search_term)
            )
        students = query.all()
        for student in students:
            next_payment = (
                Payment.query.filter(
                    Payment.student_id == student.id,
                    Payment.status.in_(["pending", "late"]),
                )
                .order_by(Payment.due_date.asc())
                .first()
            )
            student.next_due_date = next_payment.due_date if next_payment else None

        return render_template("students.html", students=students, search=search)

    @app.route("/alunos/novo", methods=["GET", "POST"])
    @login_required
    def create_student():
        if request.method == "POST":
            student_data, error_message = parse_student_form(request.form)
            if error_message:
                flash(error_message, "danger")
                return render_template(
                    "student_form.html",
                    student=None,
                    plans=active_training_plans(),
                    schedules=active_class_schedules(),
                )

            student = Student(**student_data)
            db.session.add(student)
            db.session.commit()
            ensure_monthly_payments()
            flash("Aluno cadastrado com sucesso.", "success")
            return redirect(url_for("students"))

        return render_template(
            "student_form.html",
            student=None,
            plans=active_training_plans(),
            schedules=active_class_schedules(),
        )

    @app.route("/alunos/<int:student_id>/editar", methods=["GET", "POST"])
    @login_required
    def edit_student(student_id):
        student = Student.query.get_or_404(student_id)

        if request.method == "POST":
            student_data, error_message = parse_student_form(request.form)
            if error_message:
                flash(error_message, "danger")
                return render_template(
                    "student_form.html",
                    student=student,
                    plans=active_training_plans(),
                    schedules=active_class_schedules(),
                )

            for field, value in student_data.items():
                setattr(student, field, value)

            db.session.commit()
            ensure_monthly_payments()
            flash("Aluno atualizado.", "success")
            return redirect(url_for("students"))

        return render_template(
            "student_form.html",
            student=student,
            plans=active_training_plans(),
            schedules=active_class_schedules(),
        )

    @app.post("/alunos/<int:student_id>/status")
    @login_required
    def toggle_student_status(student_id):
        student = Student.query.get_or_404(student_id)
        student.active = not student.active
        db.session.commit()
        flash("Status do aluno atualizado.", "info")
        return redirect(url_for("students"))

    @app.post("/alunos/<int:student_id>/excluir")
    @login_required
    def delete_student(student_id):
        student = Student.query.get_or_404(student_id)
        student_name = student.full_name
        db.session.delete(student)
        db.session.commit()
        flash(f"Aluno {student_name} excluido com sucesso.", "success")
        return redirect(url_for("students"))

    @app.route("/mensalidades")
    @login_required
    def payments():
        ensure_monthly_payments()
        status = request.args.get("status", "all")
        query = Payment.query.order_by(Payment.due_date.asc())
        if status != "all":
            query = query.filter_by(status=status)
        payment_rows = query.all()
        today = date.today()
        due_soon_days = max(get_app_settings().reminder_days_before, 3)

        for payment in payment_rows:
            next_payment = (
                Payment.query.filter(
                    Payment.student_id == payment.student_id,
                    Payment.due_date > payment.due_date,
                )
                .order_by(Payment.due_date.asc())
                .first()
            )
            payment.next_payment = next_payment
            payment.next_due_display_date = None
            if payment.status == "paid" and payment.paid_at:
                payment.next_due_display_date = add_one_month(payment.paid_at.date())
            elif next_payment:
                payment.next_due_display_date = next_payment.due_date

            payment.next_payment_due_soon = bool(
                payment.next_due_display_date
                and payment.next_due_display_date >= today
                and (payment.next_due_display_date - today).days <= due_soon_days
            )
        return render_template(
            "payments.html",
            payments=payment_rows,
            status=status,
            today=today,
            use_twilio=is_twilio_configured(),
        )

    @app.post("/mensalidades/<int:payment_id>/pagar")
    @login_required
    def mark_payment_paid(payment_id):
        payment = Payment.query.get_or_404(payment_id)
        payment.status = "paid"
        payment.paid_at = datetime.utcnow()
        payment.notes = request.form.get("notes", payment.notes)
        db.session.commit()
        next_payment = ensure_student_payment_for_month(payment.student, next_reference_month(payment.reference_month))
        flash("Mensalidade marcada como paga.", "success")
        if next_payment.status != "paid":
            flash(
                f"Proxima mensalidade de {payment.student.full_name} criada para {next_payment.due_date.strftime('%d/%m/%Y') }.",
                "info",
            )
        return redirect(url_for("payments"))

    @app.post("/mensalidades/<int:payment_id>/lembrar")
    @login_required
    def send_payment_reminder(payment_id):
        payment = Payment.query.get_or_404(payment_id)
        if not is_twilio_configured():
            flash("API de WhatsApp nao configurada. Use o botao Abrir WhatsApp para envio manual.", "warning")
            return redirect(url_for("payments"))

        provider, status = send_whatsapp_reminder(payment)
        flash(f"Lembrete enviado pelo canal {provider} com status {status}.", "info")
        return redirect(url_for("payments"))

    @app.get("/mensalidades/<int:payment_id>/whatsapp-manual")
    @login_required
    def open_manual_whatsapp(payment_id):
        payment = Payment.query.get_or_404(payment_id)
        manual_url = register_manual_whatsapp_click(payment)
        return redirect(manual_url)

    @app.post("/mensalidades/gerar")
    @login_required
    def generate_payments():
        ensure_monthly_payments()
        flash("Mensalidades do mes atual verificadas e geradas quando necessario.", "success")
        return redirect(url_for("payments"))

    @app.post("/mensalidades/processar-lembretes")
    @login_required
    def process_reminders():
        if not is_twilio_configured():
            flash("Sem Twilio configurado, os lembretes automaticos ficam indisponiveis. Use o envio manual por clique.", "warning")
            return redirect(url_for("payments"))

        process_automatic_reminders(app)
        flash("Processamento de lembretes executado.", "info")
        return redirect(url_for("payments"))

    @app.route("/relatorios")
    @login_required
    def reports():
        monthly_rows = monthly_report_data()
        plan_rows = plan_distribution()
        status_rows = payment_status_distribution()
        notification_rows = recent_notifications(limit=12)
        class_rows = class_schedule_overview()
        return render_template(
            "reports.html",
            monthly_rows=monthly_rows,
            plan_rows=plan_rows,
            status_rows=status_rows,
            notification_rows=notification_rows,
            class_rows=class_rows,
        )

    @app.get("/relatorios/export/csv")
    @login_required
    def export_reports_csv():
        data = build_reports_csv(
            monthly_report_data(),
            plan_distribution(),
            payment_status_distribution(),
            recent_notifications(limit=50),
            class_schedule_overview(),
        )
        return Response(
            data,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename=relatorios_ctc_aranha_{date.today().isoformat()}.csv"},
        )

    @app.get("/relatorios/export/pdf")
    @login_required
    def export_reports_pdf():
        pdf_buffer = build_reports_pdf(
            get_app_settings().gym_name,
            monthly_report_data(),
            plan_distribution(),
            payment_status_distribution(),
            recent_notifications(limit=25),
            class_schedule_overview(),
        )
        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"relatorios_ctc_aranha_{date.today().isoformat()}.pdf",
        )