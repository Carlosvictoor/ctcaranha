import csv
from io import BytesIO, StringIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_reports_csv(monthly_rows, plan_rows, status_rows, notification_rows, class_rows):
    buffer = StringIO()
    writer = csv.writer(buffer)

    writer.writerow(["Resumo financeiro"])
    writer.writerow(["Mes", "Total previsto", "Total recebido"])
    for row in monthly_rows:
        writer.writerow([row.reference_month, row.total, row.received])

    writer.writerow([])
    writer.writerow(["Distribuicao de planos"])
    writer.writerow(["Plano", "Total de alunos"])
    for plan_name, total in plan_rows:
        writer.writerow([plan_name, total])

    writer.writerow([])
    writer.writerow(["Status das mensalidades"])
    writer.writerow(["Status", "Total"])
    for status, total in status_rows.items():
        writer.writerow([status, total])

    writer.writerow([])
    writer.writerow(["Turmas"])
    writer.writerow(["Turma", "Dias", "Horario", "Nivel", "Alunos"])
    for row in class_rows:
        writer.writerow([row[1], row[2], row[3], row[4], row[6]])

    writer.writerow([])
    writer.writerow(["Avisos recentes"])
    writer.writerow(["Telefone", "Canal", "Status", "Criado em", "Mensagem"])
    for item in notification_rows:
        writer.writerow([item.phone, item.provider, item.status, item.created_at.strftime("%d/%m/%Y %H:%M"), item.message])

    return buffer.getvalue().encode("utf-8-sig")


def build_reports_pdf(app_name, monthly_rows, plan_rows, status_rows, notification_rows, class_rows):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    story = [Paragraph(f"{app_name} - Relatorios Gerenciais", styles["Title"]), Spacer(1, 12)]

    story.extend(_build_section("Resumo financeiro", [["Mes", "Previsto", "Recebido"]] + [
        [row.reference_month, _currency(row.total), _currency(row.received)] for row in monthly_rows
    ]))
    story.extend(_build_section("Distribuicao de planos", [["Plano", "Alunos"]] + [
        [plan_name, str(total)] for plan_name, total in plan_rows
    ]))
    story.extend(_build_section("Status das mensalidades", [["Status", "Total"]] + [
        [status, str(total)] for status, total in status_rows.items()
    ]))
    story.extend(_build_section("Turmas cadastradas", [["Turma", "Dias", "Horario", "Nivel", "Alunos"]] + [
        [row[1], row[2], row[3], row[4], str(row[6])] for row in class_rows
    ]))
    story.extend(_build_section("Avisos recentes", [["Telefone", "Canal", "Status", "Criado em"]] + [
        [item.phone, item.provider, item.status, item.created_at.strftime("%d/%m/%Y %H:%M")] for item in notification_rows
    ]))

    doc.build(story)
    buffer.seek(0)
    return buffer


def _build_section(title, data):
    styles = getSampleStyleSheet()
    section = [Paragraph(title, styles["Heading2"]), Spacer(1, 8)]
    table = Table(data, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#c1121f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#fff6dd")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#222222")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEADING", (0, 0), (-1, -1), 11),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ]
        )
    )
    section.extend([table, Spacer(1, 14)])
    return section


def _currency(value):
    numeric = value or 0
    return f"R$ {numeric:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
