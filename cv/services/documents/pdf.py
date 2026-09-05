from io import BytesIO
import textwrap

from django.core.files.base import ContentFile
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from cv.models_document import DocumentArtifact
from cv.services.documents.base import DocumentGenerator
from cv.services.documents.renderer import get_render_config


class PDFGenerator(DocumentGenerator):
    def generate(self, version):
        payload = version.snapshot
        config = get_render_config(payload.get("template", {}))
        stream = BytesIO()
        pdf = canvas.Canvas(stream, pagesize=A4)
        width, height = A4
        margin = config["margin"]
        body_color = colors.HexColor("#374151")
        accent_color = colors.HexColor(config["accent_color"])
        gap = config["section_gap"]
        line_gap = 11 if config["density"] == "compact" else 14

        def draw_wrapped(text, x, y, max_width, size=None, bold=False, color=None, leading=None, align="left"):
            size = size or config["font_size"]
            leading = leading or max(11, size + 3)
            font = config["font_name"]
            if bold and font in {"Helvetica", "Times-Roman"}:
                font = "Helvetica-Bold" if font == "Helvetica" else "Times-Bold"
            pdf.setFont(font, size)
            pdf.setFillColor(color or body_color)
            char_width = max(pdf.stringWidth("M", font, size), 1)
            chars = max(int(max_width / char_width), 1)
            lines = []
            for paragraph in str(text).splitlines() or [""]:
                lines.extend(textwrap.wrap(paragraph, width=chars) or [""])
            for line_text in lines:
                if y < margin:
                    pdf.showPage()
                    y = height - margin
                    pdf.setFont(font, size)
                    pdf.setFillColor(color or body_color)
                if align == "center":
                    pdf.drawCentredString(x + max_width / 2, y, line_text)
                elif align == "right":
                    pdf.drawRightString(x + max_width, y, line_text)
                else:
                    pdf.drawString(x, y, line_text)
                y -= leading
            return y

        def section_heading(title, x, y, max_width):
            label = title.upper() if config["section_style"] == "uppercase_rule" else title
            y = draw_wrapped(
                label,
                x,
                y,
                max_width,
                config["heading_size"],
                bold=True,
                color=accent_color,
                leading=config["heading_size"] + 7,
            )
            if config["section_style"] == "uppercase_rule":
                pdf.setStrokeColor(accent_color)
                pdf.setLineWidth(0.6)
                pdf.line(x, y + 3, x + max_width, y + 3)
            return y - gap

        contact = payload.get("contact", {})
        name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
        details = [contact.get("email"), contact.get("phone"), contact.get("location")]
        details = [str(value) for value in details if value]
        if payload.get("linkedin_url"):
            details.append(payload["linkedin_url"])
        if payload.get("portfolio_url"):
            details.append(payload["portfolio_url"])

        header_align = "center" if config["header_style"] == "centered" else "left"
        header_x = margin if header_align == "left" else margin
        header_width = width - (2 * margin)
        y = height - margin
        if config["header_style"] == "compact":
            name_size = config["heading_size"] + 5
        else:
            name_size = config["heading_size"] + 8
        if name:
            y = draw_wrapped(name, header_x, y, header_width, name_size, bold=True, color=accent_color, leading=name_size + 3, align=header_align)
        if payload.get("professional_title"):
            y -= 2
            y = draw_wrapped(payload["professional_title"], header_x, y, header_width, config["font_size"] + 2, color=accent_color, leading=config["font_size"] + 5, align=header_align)
        if details:
            y -= 2
            y = draw_wrapped(" | ".join(details), header_x, y, header_width, max(8, config["font_size"] - 1), leading=config["font_size"] + 2, align=header_align)
        if config["header_style"] != "compact":
            pdf.setStrokeColor(accent_color)
            pdf.setLineWidth(0.9)
            pdf.line(margin, y - 3, width - margin, y - 3)
        y -= 18

        def render_item(kind, item, x, y, max_width):
            if kind == "experience":
                title = f"{item.get('job_title', '')} — {item.get('employer', '')}"
                body = item.get("description", "")
                location = item.get("location")
                y = draw_wrapped(title, x, y, max_width, config["font_size"], bold=True, leading=line_gap)
                if location:
                    y = draw_wrapped(location, x, y, max_width, max(8, config["font_size"] - 1), color=body_color, leading=line_gap)
                if body:
                    y = draw_wrapped(body, x, y, max_width, max(8, config["font_size"] - 1), leading=line_gap)
            elif kind == "education":
                title = f"{item.get('qualification', '')} — {item.get('institution', '')}"
                y = draw_wrapped(title, x, y, max_width, config["font_size"], bold=True, leading=line_gap)
                if item.get("field_of_study"):
                    y = draw_wrapped(item["field_of_study"], x, y, max_width, max(8, config["font_size"] - 1), leading=line_gap)
            elif kind == "skill":
                y = draw_wrapped(item.get("name", ""), x, y, max_width, max(8, config["font_size"] - 1), leading=line_gap)
            elif kind == "project":
                title = f"{item.get('name', '')} — {item.get('role', '')}"
                y = draw_wrapped(title, x, y, max_width, config["font_size"], bold=True, leading=line_gap)
                if item.get("description"):
                    y = draw_wrapped(item["description"], x, y, max_width, max(8, config["font_size"] - 1), leading=line_gap)
            elif kind == "certification":
                title = f"{item.get('name', '')} — {item.get('issuer', '')}"
                y = draw_wrapped(title, x, y, max_width, max(8, config["font_size"] - 1), leading=line_gap)
            elif kind == "achievement":
                y = draw_wrapped(item.get("title", ""), x, y, max_width, max(8, config["font_size"] - 1), bold=True, leading=line_gap)
                if item.get("description"):
                    y = draw_wrapped(item["description"], x, y, max_width, max(8, config["font_size"] - 1), leading=line_gap)
            return y - gap

        def render_sections(section_list, x, y, max_width):
            for heading, value, kind in section_list:
                if not value:
                    continue
                y = section_heading(heading, x, y, max_width)
                if kind == "text":
                    y = draw_wrapped(value, x, y, max_width, max(8, config["font_size"] - 1), leading=line_gap) - gap
                elif kind == "skill_group":
                    names = [str(item.get("name", "")) for item in value if item.get("name")]
                    y = draw_wrapped(" • ".join(names), x, y, max_width, max(8, config["font_size"] - 1), leading=line_gap) - gap
                else:
                    for item in value:
                        y = render_item(kind, item, x, y, max_width)
            return y

        all_sections = (
            ("Summary", payload.get("summary"), "text"),
            ("Experience", payload.get("experiences", []), "experience"),
            ("Education", payload.get("educations", []), "education"),
            ("Skills", payload.get("skills", []), "skill_group"),
            ("Projects", payload.get("projects", []), "project"),
            ("Certifications", payload.get("certifications", []), "certification"),
            ("Achievements", payload.get("achievements", []), "achievement"),
        )

        if config["layout"] == "sidebar":
            sidebar_width = max(145, min(175, width * 0.27))
            column_gap = 18
            main_x = margin
            side_x = width - margin - sidebar_width
            main_width = side_x - column_gap - main_x
            side_y = y
            main_y = y
            pdf.setFillColor(colors.HexColor(config["accent_color"]))
            pdf.rect(side_x - 8, 0, sidebar_width + 8, height, stroke=0, fill=1)
            sidebar_body = colors.white
            sidebar_sections = (
                ("Skills", payload.get("skills", []), "skill_group"),
                ("Education", payload.get("educations", []), "education"),
                ("Certifications", payload.get("certifications", []), "certification"),
            )
            # Sidebar headings and text use white on the accent panel.
            original_accent = accent_color
            accent_color = sidebar_body
            side_y = render_sections(sidebar_sections, side_x, side_y, sidebar_width - 12)
            accent_color = original_accent
            main_sections = (
                ("Summary", payload.get("summary"), "text"),
                ("Experience", payload.get("experiences", []), "experience"),
                ("Projects", payload.get("projects", []), "project"),
                ("Achievements", payload.get("achievements", []), "achievement"),
            )
            main_y = render_sections(main_sections, main_x, main_y, main_width)
        else:
            render_sections(all_sections, margin, y, width - (2 * margin))

        pdf.save()
        stream.seek(0)
        artifact = DocumentArtifact(
            cv_version=version,
            artifact_type=DocumentArtifact.PDF,
            mime_type="application/pdf",
            template_slug=payload["template"]["slug"],
            template_config=payload["template"].get("config", {}),
        )
        artifact.file.save(f"{version.cv_id}-v{version.version_number}.pdf", ContentFile(stream.read()), save=True)
        return artifact


def generate_pdf(cv_version):
    return PDFGenerator().generate(cv_version)
