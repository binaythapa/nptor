from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.colors import grey


def generate_certificate_pdf(user, course, certificate):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    center_x = width / 2

    # ================= TITLE =================
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(center_x, height - 3 * cm, "Certificate of Course Completion")

    # ================= MAIN BODY =================
    y = height - 6 * cm

    c.setFont("Helvetica", 14)
    c.drawCentredString(center_x, y, "This is to certify that")

    y -= 2 * cm
    name = user.get_full_name() or user.username
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(center_x, y, name)

    y -= 2 * cm
    c.setFont("Helvetica", 14)
    c.drawCentredString(
        center_x,
        y,
        "has successfully completed the online training course"
    )

    y -= 2 * cm
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(center_x, y, f"“{course.title}”")

    y -= 1.5 * cm
    c.setFont("Helvetica", 14)
    c.drawCentredString(center_x, y, "conducted by nptor.com")

    # ================= DISCLAIMER BOX =================
    box_top = 7 * cm
    box_left = 2.5 * cm
    box_width = width - 5 * cm
    box_height = 3.2 * cm

    c.setStrokeColor(grey)
    c.rect(box_left, box_top - box_height, box_width, box_height)

    disclaimer_text = (
        "Disclaimer: This certificate is issued by nptor.com as proof of successful "
        "completion of an online training course. It is not an official certification "
        "issued by Snowflake Inc., Microsoft, or any other vendor, and does not imply "
        "vendor authorization, endorsement, or professional accreditation."
    )

    text = c.beginText()
    text.setTextOrigin(box_left + 0.5 * cm, box_top - 1 * cm)
    text.setFont("Helvetica", 9)
    text.setLeading(14)
    text.setFillColor(grey)

    # Proper text wrapping
    max_chars = 95
    for i in range(0, len(disclaimer_text), max_chars):
        text.textLine(disclaimer_text[i:i + max_chars])

    c.drawText(text)

    # ================= FOOTER =================
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 11)

    c.drawString(
        3 * cm,
        2.8 * cm,
        "Issued by: nptor.com"
    )

    c.setFont("Helvetica", 10)
    c.drawString(
        3 * cm,
        2.2 * cm,
        f"Certificate ID: {certificate.certificate_id}"
    )

    c.drawRightString(
        width - 3 * cm,
        2.2 * cm,
        f"Issue Date: {certificate.issued_at.strftime('%d %B %Y')}"
    )

    # ================= FINALIZE =================
    c.showPage()
    c.save()

    pdf = buffer.getvalue()
    buffer.close()
    return pdf
