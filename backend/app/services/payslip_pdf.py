"""Real Payslip PDF generation (reportlab) from persisted, already-computed
Payslip data. Never recomputes — renders exactly what was snapshotted, so
the PDF for a VALIDATED/PAID payslip stays historically stable even if
Salary Rules change afterward."""
import io
from datetime import datetime, timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from app.models.payroll import Payslip

styles = getSampleStyleSheet()
_title_style = ParagraphStyle("PayloomTitle", parent=styles["Heading1"], fontSize=16, spaceAfter=2)
_sub_style = ParagraphStyle("PayloomSub", parent=styles["Normal"], fontSize=9, textColor=colors.grey)
_section_style = ParagraphStyle("PayloomSection", parent=styles["Heading3"], fontSize=11, spaceBefore=10, spaceAfter=4)


def _money(amount) -> str:
    return f"Rs. {amount:,.2f}"


def generate_payslip_pdf(payslip: Payslip) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm, leftMargin=18 * mm, rightMargin=18 * mm)
    elements = []

    employee = payslip.employee
    elements.append(Paragraph("Payloom", _title_style))
    elements.append(Paragraph("Payslip", _sub_style))
    elements.append(Spacer(1, 10))

    info_rows = [
        ["Employee", f"{employee.first_name} {employee.last_name}", "Employee ID", employee.employee_code or "-"],
        ["Department", employee.department.name if employee.department else "-", "Payroll Period", f"{payslip.period_start.isoformat()} to {payslip.period_end.isoformat()}"],
        ["Payrun", payslip.payrun.reference, "Salary Structure", payslip.salary_structure.name],
        ["Status", payslip.status.value, "Worked Days", str(payslip.worked_days) if payslip.worked_days is not None else "-"],
    ]
    info_table = Table(info_rows, colWidths=[35 * mm, 60 * mm, 35 * mm, 45 * mm])
    info_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
        ("TEXTCOLOR", (2, 0), (2, -1), colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_table)

    elements.append(Paragraph("Salary Computation", _section_style))
    line_rows = [["Rule", "Category", "Base / Rate", "Amount"]]
    for line in sorted(payslip.lines, key=lambda l: l.sequence_snapshot):
        line_rows.append([
            f"{line.rule_name_snapshot} ({line.rule_code_snapshot})",
            line.category_snapshot.value.title(),
            line.base_description_snapshot or "-",
            _money(line.amount),
        ])
    comp_table = Table(line_rows, colWidths=[55 * mm, 30 * mm, 55 * mm, 35 * mm])
    comp_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (3, 0), (3, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(comp_table)

    elements.append(Spacer(1, 10))
    summary_rows = [
        ["Basic", _money(payslip.basic)],
        ["Allowances", _money(payslip.allowances)],
        ["Gross Salary", _money(payslip.gross)],
        ["Deductions", _money(payslip.deductions)],
        ["Net Salary", _money(payslip.net)],
    ]
    summary_table = Table(summary_rows, colWidths=[140 * mm, 35 * mm])
    summary_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, 4), (-1, 4), "Helvetica-Bold"),
        ("FONTSIZE", (0, 4), (-1, 4), 12),
        ("LINEABOVE", (0, 4), (-1, 4), 0.8, colors.black),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(summary_table)

    if payslip.warnings:
        elements.append(Paragraph("Notes", _section_style))
        for w in payslip.warnings:
            elements.append(Paragraph(f"&bull; [{w.severity.value}] {w.message}", styles["Normal"]))

    elements.append(Spacer(1, 14))
    generated_at = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    elements.append(Paragraph(f"Generated {generated_at} by Payloom - not a statutory or compliance document.", _sub_style))

    doc.build(elements)
    return buffer.getvalue()
