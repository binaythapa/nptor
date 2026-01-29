from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm


def generate_certificate_pdf(user, course, certificate):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(width / 2, height - 3 * cm, "Certificate of Completion")

    c.setFont("Helvetica", 14)
    c.drawCentredString(width / 2, height - 6 * cm, "This is to certify that")

    name = user.get_full_name() or user.username
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width / 2, height - 8 * cm, name)

    c.setFont("Helvetica", 14)
    c.drawCentredString(
        width / 2,
        height - 10 * cm,
        "has successfully completed the course"
    )

    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 12 * cm, course.title)

    c.setFont("Helvetica", 12)
    c.drawString(3 * cm, 4 * cm, f"Certificate ID: {certificate.certificate_id}")
    c.drawRightString(
        width - 3 * cm,
        4 * cm,
        f"Issued on: {certificate.issued_at.strftime('%d %B %Y')}"
    )

    c.showPage()
    c.save()

    pdf = buffer.getvalue()
    buffer.close()
    return pdf
