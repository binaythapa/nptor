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

        def section_heading(title, x, y, max_width, white=False):
            label = title.upper() if config["section_style"] == "uppercase_rule" else title
            y = draw_wrapped(
                label,
                x,
                y,
                max_width,
                config["heading_size"],
                bold=True,
                color=colors.white if white else accent_color,
                leading=config["heading_size"] + 7,
            )
            if config["section_style"] == "uppercase_rule":
                pdf.setStrokeColor(colors.Color(1, 1, 1, alpha=.45) if white else accent_color)
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

        design = config["design_style"]
        header_align = "center" if config["header_style"] == "centered" else "left"
        header_x = margin
        header_width = width - (2 * margin)
        y = height - margin

        if design == "modern_header":
            header_height = 94
            header_bottom = height - header_height
            pdf.setFillColor(accent_color)
            pdf.rect(0, header_bottom, width, header_height, stroke=0, fill=1)
            initials = f"{contact.get('first_name', '')[:1]}{contact.get('last_name', '')[:1]}".upper()
            pdf.setStrokeColor(colors.white)
            pdf.setLineWidth(.7)
            pdf.rect(margin, header_bottom + 20, 58, 58, stroke=1, fill=0)
            if initials:
                pdf.setFont("Helvetica", 18)
                pdf.setFillColor(colors.white)
                pdf.drawCentredString(margin + 29, header_bottom + 42, initials)
            text_x = margin + 76
            text_width = header_width - 76
            y = header_bottom + 66
            if name:
                y = draw_wrapped(name, text_x, y, text_width, config["heading_size"] + 11, bold=True, color=colors.white, leading=config["heading_size"] + 12)
            if payload.get("professional_title"):
                y -= 1
                y = draw_wrapped(payload["professional_title"], text_x, y, text_width, config["font_size"] + 1, color=colors.white, leading=config["font_size"] + 4)
            if details:
                y -= 1
                draw_wrapped(" | ".join(details), text_x, y, text_width, max(8, config["font_size"] - 1), color=colors.white, leading=config["font_size"] + 2)
            y = header_bottom - 22
        elif design == "elegant":
            if name:
                y = draw_wrapped(name, header_x, y, header_width * .65, config["heading_size"] + 9, bold=False, color=accent_color, leading=config["heading_size"] + 5)
            if payload.get("professional_title"):
                y -= 2
                y = draw_wrapped(payload["professional_title"], header_x, y, header_width * .65, config["font_size"] + 1, color=accent_color, leading=config["font_size"] + 4)
            if details:
                draw_wrapped(" | ".join(details), width - margin - header_width * .45, height - margin - 8, header_width * .45, max(8, config["font_size"] - 1), color=body_color, leading=config["font_size"] + 2, align="right")
            y -= 18
        else:
            if name:
                y = draw_wrapped(name, header_x, y, header_width, config["heading_size"] + 8, bold=True, color=accent_color, leading=config["heading_size"] + 3, align=header_align)
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

        def render_item(kind, item, x, y, max_width, white=False):
            if kind == "experience":
                title = f"{item.get('job_title', '')} — {item.get('employer', '')}"
                body = item.get("description", "")
                location = item.get("location")
                y = draw_wrapped(title, x, y, max_width, config["font_size"], bold=True, color=colors.white if white else None, leading=line_gap)
                if location:
                    y = draw_wrapped(location, x, y, max_width, max(8, config["font_size"] - 1), color=colors.white if white else None, leading=line_gap)
                if body:
                    y = draw_wrapped(body, x, y, max_width, max(8, config["font_size"] - 1), color=colors.white if white else None, leading=line_gap)
            elif kind == "education":
                title = f"{item.get('qualification', '')} — {item.get('institution', '')}"
                y = draw_wrapped(title, x, y, max_width, config["font_size"], bold=True, color=colors.white if white else None, leading=line_gap)
                if item.get("field_of_study"):
                    y = draw_wrapped(item["field_of_study"], x, y, max_width, max(8, config["font_size"] - 1), color=colors.white if white else None, leading=line_gap)
            elif kind == "skill":
                y = draw_wrapped(item.get("name", ""), x, y, max_width, max(8, config["font_size"] - 1), color=colors.white if white else None, leading=line_gap)
            elif kind == "project":
                title = f"{item.get('name', '')} — {item.get('role', '')}"
                y = draw_wrapped(title, x, y, max_width, config["font_size"], bold=True, color=colors.white if white else None, leading=line_gap)
                if item.get("description"):
                    y = draw_wrapped(item["description"], x, y, max_width, max(8, config["font_size"] - 1), color=colors.white if white else None, leading=line_gap)
            elif kind == "certification":
                title = f"{item.get('name', '')} — {item.get('issuer', '')}"
                y = draw_wrapped(title, x, y, max_width, max(8, config["font_size"] - 1), color=colors.white if white else None, leading=line_gap)
            elif kind == "achievement":
                y = draw_wrapped(item.get("title", ""), x, y, max_width, max(8, config["font_size"] - 1), bold=True, color=colors.white if white else None, leading=line_gap)
                if item.get("description"):
                    y = draw_wrapped(item["description"], x, y, max_width, max(8, config["font_size"] - 1), color=colors.white if white else None, leading=line_gap)
            return y - gap

        def render_sections(section_list, x, y, max_width, white=False):
            for heading, value, kind in section_list:
                if not value:
                    continue
                y = section_heading(heading, x, y, max_width, white=white)
                if kind == "text":
                    y = draw_wrapped(value, x, y, max_width, max(8, config["font_size"] - 1), color=colors.white if white else None, leading=line_gap) - gap
                elif kind == "skill_group":
                    names = [str(item.get("name", "")) for item in value if item.get("name")]
                    y = draw_wrapped(" • ".join(names), x, y, max_width, max(8, config["font_size"] - 1), color=colors.white if white else None, leading=line_gap) - gap
                else:
                    for item in value:
                        y = render_item(kind, item, x, y, max_width, white=white)
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
            pdf.setFillColor(accent_color)
            pdf.rect(side_x - 8, 0, sidebar_width + 8, height, stroke=0, fill=1)
            sidebar_body = colors.white
            sidebar_sections = (
                ("Skills", payload.get("skills", []), "skill_group"),
                ("Education", payload.get("educations", []), "education"),
                ("Certifications", payload.get("certifications", []), "certification"),
            )
            original_accent = accent_color
            original_body = body_color
            accent_color = sidebar_body
            body_color = sidebar_body
            side_y = render_sections(sidebar_sections, side_x, side_y, sidebar_width - 12, white=True)
            accent_color = original_accent
            body_color = original_body
            main_sections = (
                ("Summary", payload.get("summary"), "text"),
                ("Experience", payload.get("experiences", []), "experience"),
                ("Projects", payload.get("projects", []), "project"),
                ("Achievements", payload.get("achievements", []), "achievement"),
            )
            main_y = render_sections(main_sections, main_x, main_y, main_width)
        else:
            if design in {"split_label", "elegant"}:
                label_width = 115
                content_x = margin + label_width + 18
                content_width = width - margin - content_x
                for heading, value, kind in all_sections:
                    if not value:
                        continue
                    label_y = y
                    pdf.setFont(config["font_name"], config["heading_size"])
                    pdf.setFillColor(accent_color)
                    label = heading.upper() if config["section_style"] == "uppercase_rule" else heading
                    pdf.drawRightString(margin + label_width, label_y, label)
                    if design == "elegant":
                        pdf.setStrokeColor(colors.HexColor("#d5dbe2"))
                        pdf.setLineWidth(.5)
                        pdf.line(content_x - 9, label_y + 5, content_x - 9, max(margin, label_y - 70))
                    if kind == "text":
                        y = draw_wrapped(value, content_x, y, content_width, max(8, config["font_size"] - 1), leading=line_gap) - gap
                    elif kind == "skill_group":
                        names = [str(item.get("name", "")) for item in value if item.get("name")]
                        y = draw_wrapped(" • ".join(names), content_x, y, content_width, max(8, config["font_size"] - 1), leading=line_gap) - gap
                    else:
                        for item in value:
                            y = render_item(kind, item, content_x, y, content_width)
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
