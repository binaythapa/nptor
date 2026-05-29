from io import BytesIO
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import grey, black, HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping
import textwrap

# -------------------------------------------------
# TEXT SANITIZER (CRITICAL FOR REPORTLAB)
# -------------------------------------------------
def sanitize_certificate_text(text: str) -> str:
    """
    Converts unsupported Unicode characters to
    ASCII-safe equivalents for ReportLab.
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
# WRAPPED TEXT HELPER
# -------------------------------------------------
def draw_wrapped_text(c, text, x, y, max_width, font_name, font_size, leading=None):
    """
    Draw wrapped text at specified position with word wrapping.
    Returns the new y position after drawing.
    """
    if leading is None:
        leading = font_size * 1.2
    
    c.setFont(font_name, font_size)
    
    # Calculate max characters per line based on font size and width
    # Approximate character width (adjust as needed)
    avg_char_width = font_size * 0.6
    max_chars = int(max_width / avg_char_width)
    
    # Wrap the text
    wrapped_lines = textwrap.wrap(text, width=max_chars)
    
    # Draw each line
    current_y = y
    for line in wrapped_lines:
        c.drawString(x, current_y, line)
        current_y -= leading
    
    return current_y


# -------------------------------------------------
# CERTIFICATE GENERATOR (PROFESSIONAL VERSION)
# -------------------------------------------------
def generate_certificate_pdf(user, course, certificate):
    buffer = BytesIO()
    
    # Use landscape orientation for better layout
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)  # 841 x 595 (landscape)
    
    # Define margins
    left_margin = 2 * cm
    right_margin = width - 2 * cm
    top_margin = height - 1.5 * cm
    bottom_margin = 1.5 * cm
    
    center_x = width / 2
    
    # ================= BORDER =================
    # Draw elegant border
    border_margin = 0.5 * cm
    c.setStrokeColor(HexColor('#CCCCCC'))
    c.setLineWidth(2)
    c.rect(
        border_margin, 
        border_margin, 
        width - 2 * border_margin, 
        height - 2 * border_margin
    )
    
    # Inner border
    inner_margin = 0.6 * cm
    c.setStrokeColor(HexColor('#E0E0E0'))
    c.setLineWidth(1)
    c.rect(
        inner_margin, 
        inner_margin, 
        width - 2 * inner_margin, 
        height - 2 * inner_margin
    )
    
    # ================= HEADER SECTION =================
    y_position = top_margin
    
    # Add decorative line above title
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
    name = sanitize_certificate_text(
        user.get_full_name() or user.username
    )
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
    
    # ================= DECORATIVE ELEMENTS =================
    # Add subtle separator line
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
    c.line(
        left_margin + 1*cm, 
        signature_y - 0.2 * cm, 
        left_margin + 6*cm, 
        signature_y - 0.2 * cm
    )
    
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
    
    # ================= DISCLAIMER BOX =================
    disclaimer_box_top = bottom_margin + 2.5 * cm
    disclaimer_box_left = left_margin
    disclaimer_box_width = width - (2 * left_margin)
    disclaimer_box_height = 2.2 * cm
    
    # Box border
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
    
    # Disclaimer text (smaller font, justified)
    disclaimer_text = sanitize_certificate_text(
        "Disclaimer: This certificate is issued by nptor.com as proof of successful "
        "completion of an online training course. It is intended solely for educational "
        "and skill-development purposes and does not represent an official professional "
        "certification, accreditation, authorization, or endorsement by any external "
        "organization or governing body."
    )
    
    c.setFont("Helvetica", 8)
    c.setFillColor(HexColor('#95A5A6'))
    
    # Draw wrapped disclaimer text
    text_y = disclaimer_box_top - 0.6 * cm
    text_x = disclaimer_box_left + 0.3 * cm
    max_width = disclaimer_box_width - 0.6 * cm
    
    draw_wrapped_text(
        c, disclaimer_text, text_x, text_y, 
        max_width, "Helvetica", 8, leading=11
    )
    
    # ================= SEAL/LOGO PLACEMENT =================
    # Optional: Add a decorative seal near the signature area
    seal_center_x = center_x
    seal_center_y = signature_y - 1 * cm
    
    # Draw simple seal circle
    c.setStrokeColor(HexColor('#4A90E2'))
    c.setFillColor(HexColor('#F0F7FF'))
    c.setLineWidth(1.5)
    c.circle(seal_center_x, seal_center_y, 0.8*cm, fill=1, stroke=1)
    
    # Inner circle
    c.setStrokeColor(HexColor('#4A90E2'))
    c.setLineWidth(1)
    c.circle(seal_center_x, seal_center_y, 0.6*cm)
    
    # Text inside seal
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(HexColor('#4A90E2'))
    c.drawCentredString(seal_center_x, seal_center_y - 0.1*cm, "NPC")
    
    # ================= FOOTER =================
    c.setFont("Helvetica", 8)
    c.setFillColor(HexColor('#BDC3C7'))
    footer_text = "This certificate is digitally generated and does not require a physical signature."
    c.drawCentredString(center_x, bottom_margin - 0.3*cm, footer_text)
    
    # Page number (if multiple pages, but single page here)
    c.drawCentredString(center_x, bottom_margin - 0.8*cm, "Page 1 of 1")
    
    # ================= FINALIZE =================
    c.showPage()
    c.save()
    
    pdf = buffer.getvalue()
    buffer.close()
    return pdf