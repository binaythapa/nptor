from io import BytesIO
from reportlab.lib.pagesizes import landscape, A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, grey
import textwrap

# -------------------------------------------------
# TEXT SANITIZER
# -------------------------------------------------
def sanitize_certificate_text(text: str) -> str:
    """
    Converts unsupported Unicode characters to ASCII-safe equivalents for ReportLab.
    """
    if not text:
        return ""

    replacements = {
        "Ⓡ": "(R)",
        "®": "(R)",
        "™": "(TM)",
        "©": "(C)",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "–": "-",
        "—": "-",
        "…": "...",
        "€": "EUR",
        "£": "GBP",
        "¥": "JPY",
    }

    for bad, good in replacements.items():
        text = text.replace(bad, good)

    # Remove any other non-ASCII characters
    text = text.encode('ascii', 'ignore').decode('ascii')
    return text


# -------------------------------------------------
# CERTIFICATE GENERATOR - 100% CORRECT VERSION
# -------------------------------------------------
def generate_certificate_pdf(user, course, certificate):
    buffer = BytesIO()
    
    # Use landscape A4
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)  # 841 x 595 points
    
    # Define margins
    left_margin = 2 * cm
    right_margin = width - 2 * cm
    top_margin = height - 1.5 * cm
    bottom_margin = 1.5 * cm
    center_x = width / 2
    
    # ================= BORDER =================
    border_margin = 0.5 * cm
    c.setStrokeColor(HexColor('#CCCCCC'))
    c.setLineWidth(2)
    c.rect(border_margin, border_margin, width - 2 * border_margin, height - 2 * border_margin)
    
    # Inner border
    inner_margin = 0.6 * cm
    c.setStrokeColor(HexColor('#E0E0E0'))
    c.setLineWidth(1)
    c.rect(inner_margin, inner_margin, width - 2 * inner_margin, height - 2 * inner_margin)
    
    # ================= HEADER SECTION =================
    y_position = top_margin
    
    # Decorative line above title
    line_y = y_position - 0.5 * cm
    c.setStrokeColor(HexColor('#4A90E2'))
    c.setLineWidth(2)
    c.line(left_margin + 3*cm, line_y, right_margin - 3*cm, line_y)
    
    # Certificate Title
    c.setFont("Helvetica-Bold", 32)
    c.setFillColor(HexColor('#2C3E50'))
    c.drawCentredString(center_x, y_position, "CERTIFICATE OF COMPLETION")
    
    # Subtitle
    y_position -= 1 * cm
    c.setFont("Helvetica", 12)
    c.setFillColor(HexColor('#7F8C8D'))
    c.drawCentredString(center_x, y_position, "Proudly Presented To")
    
    # Decorative line below title
    y_position -= 0.7 * cm
    c.setStrokeColor(HexColor('#BDC3C7'))
    c.setLineWidth(1)
    c.line(left_margin + 5*cm, y_position, right_margin - 5*cm, y_position)
    
    # ================= RECIPIENT NAME =================
    y_position -= 2 * cm
    name = sanitize_certificate_text(user.get_full_name() or user.username)
    c.setFont("Helvetica-Bold", 36)
    c.setFillColor(HexColor('#2C3E50'))
    c.drawCentredString(center_x, y_position, name)
    
    # ================= MAIN BODY =================
    y_position -= 1.5 * cm
    c.setFont("Helvetica", 14)
    c.setFillColor(HexColor('#34495E'))
    c.drawCentredString(center_x, y_position, "for successfully completing the course")
    
    # Course Title
    y_position -= 1.8 * cm
    course_title = sanitize_certificate_text(course.title)
    c.setFont("Helvetica-Bold", 26)
    c.setFillColor(HexColor('#4A90E2'))
    c.drawCentredString(center_x, y_position, f'"{course_title}"')
    
    # Additional info
    y_position -= 1.2 * cm
    c.setFont("Helvetica", 13)
    c.setFillColor(HexColor('#34495E'))
    c.drawCentredString(center_x, y_position, "conducted by")
    
    # Provider name
    y_position -= 1.2 * cm
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(HexColor('#2C3E50'))
    c.drawCentredString(center_x, y_position, "nptor.com")
    
    # ================= DECORATIVE SEPARATOR =================
    y_position -= 1.5 * cm
    c.setStrokeColor(HexColor('#BDC3C7'))
    c.setLineWidth(0.5)
    c.line(left_margin + 4*cm, y_position, right_margin - 4*cm, y_position)
    
    # ================= SIGNATURE SECTION =================
    signature_y = y_position - 1.5 * cm
    
    # Left side - Authorized signature
    c.setFont("Helvetica", 10)
    c.setFillColor(HexColor('#7F8C8D'))
    c.drawString(left_margin + 1*cm, signature_y, "Authorized Signature")
    
    # Signature line
    c.line(left_margin + 1*cm, signature_y - 0.2 * cm, left_margin + 6*cm, signature_y - 0.2 * cm)
    
    # Right side - Certificate details
    c.setFont("Helvetica", 10)
    c.drawRightString(right_margin - 1*cm, signature_y, "Certificate ID")
    c.setFont("Helvetica", 9)
    cert_id = sanitize_certificate_text(certificate.certificate_id)
    c.drawRightString(right_margin - 1*cm, signature_y - 0.5*cm, cert_id)
    
    c.setFont("Helvetica", 10)
    c.drawRightString(right_margin - 1*cm, signature_y - 1.2*cm, "Issue Date")
    c.setFont("Helvetica", 9)
    issue_date = certificate.issued_at.strftime('%d %B %Y')
    c.drawRightString(right_margin - 1*cm, signature_y - 1.7*cm, issue_date)
    
    # ================= DISCLAIMER BOX - 100% CORRECT ALIGNMENT =================
    disclaimer_box_top = bottom_margin + 2.5 * cm
    disclaimer_box_left = left_margin
    disclaimer_box_width = width - (2 * left_margin)
    disclaimer_box_height = 2.2 * cm
    
    # Draw box background and border
    c.setStrokeColor(HexColor('#E0E0E0'))
    c.setFillColor(HexColor('#F9F9F9'))
    c.rect(
        disclaimer_box_left,
        disclaimer_box_top - disclaimer_box_height,
        disclaimer_box_width,
        disclaimer_box_height,
        fill=1,
        stroke=1
    )
    
    # Disclaimer text - EXACT LINE BREAKS FOR PERFECT ALIGNMENT
    disclaimer_text = sanitize_certificate_text(
        "Disclaimer: This certificate is issued by nptor.com as proof of successful completion of an online training course. "
        "It is intended solely for educational and skill-development purposes and does not represent an official professional "
        "certification, accreditation, authorization, or endorsement by any external organization or governing body."
    )
    
    # Manual but perfect line wrapping
    line1 = "Disclaimer: This certificate is issued by nptor.com as proof of successful completion of an online training course."
    line2 = "It is intended solely for educational and skill-development purposes and does not represent an official professional"
    line3 = "certification, accreditation, authorization, or endorsement by any external organization or governing body."
    
    c.setFont("Helvetica", 8)
    c.setFillColor(HexColor('#666666'))
    
    # Draw disclaimer with exact positioning
    start_y = disclaimer_box_top - 0.65 * cm
    c.drawCentredString(center_x, start_y, line1)
    c.drawCentredString(center_x, start_y - 0.4 * cm, line2)
    c.drawCentredString(center_x, start_y - 0.8 * cm, line3)
    
    # ================= SEAL =================
    seal_center_x = center_x
    seal_center_y = signature_y - 1 * cm
    
    c.setStrokeColor(HexColor('#4A90E2'))
    c.setFillColor(HexColor('#F0F7FF'))
    c.setLineWidth(1.5)
    c.circle(seal_center_x, seal_center_y, 0.8*cm, fill=1, stroke=1)
    
    c.setStrokeColor(HexColor('#4A90E2'))
    c.setLineWidth(1)
    c.circle(seal_center_x, seal_center_y, 0.6*cm)
    
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(HexColor('#4A90E2'))
    c.drawCentredString(seal_center_x, seal_center_y - 0.1*cm, "NPC")
    
    # ================= FOOTER =================
    c.setFont("Helvetica", 8)
    c.setFillColor(HexColor('#BDC3C7'))
    footer_text = "This certificate is digitally generated and does not require a physical signature."
    c.drawCentredString(center_x, bottom_margin - 0.3*cm, footer_text)
    
    # Page number
    c.drawCentredString(center_x, bottom_margin - 0.8*cm, "Page 1 of 1")
    
    # ================= FINALIZE =================
    c.showPage()
    c.save()
    
    pdf = buffer.getvalue()
    buffer.close()
    return pdf