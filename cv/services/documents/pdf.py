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

        def render_item(kind, item, x, y, max_width, white=False):
            text_color = colors.white if white else None
            if kind == "experience":
                title = f"{item.get('job_title', '')} — {item.get('employer', '')}".strip(" —")
                y = draw_wrapped(title, x, y, max_width, config["font_size"], bold=True, color=text_color, leading=line_gap)
                if item.get("location"):
                    y = draw_wrapped(item["location"], x, y, max_width, max(8, config["font_size"] - 1), color=text_color, leading=line_gap)
                if item.get("description"):
                    y = draw_wrapped(item["description"], x, y, max_width, max(8, config["font_size"] - 1), color=text_color, leading=line_gap)
            elif kind == "education":
                title = f"{item.get('qualification', '')} — {item.get('institution', '')}".strip(" —")
                y = draw_wrapped(title, x, y, max_width, config["font_size"], bold=True, color=text_color, leading=line_gap)
                if item.get("field_of_study"):
                    y = draw_wrapped(item["field_of_study"], x, y, max_width, max(8, config["font_size"] - 1), color=text_color, leading=line_gap)
            elif kind == "project":
                title = f"{item.get('name', '')} — {item.get('role', '')}".strip(" —")
                y = draw_wrapped(title, x, y, max_width, config["font_size"], bold=True, color=text_color, leading=line_gap)
                if item.get("description"):
                    y = draw_wrapped(item["description"], x, y, max_width, max(8, config["font_size"] - 1), color=text_color, leading=line_gap)
            elif kind == "certification":
                title = f"{item.get('name', '')} — {item.get('issuer', '')}".strip(" —")
                y = draw_wrapped(title, x, y, max_width, max(8, config["font_size"] - 1), color=text_color, leading=line_gap)
            elif kind == "achievement":
                y = draw_wrapped(item.get("title", ""), x, y, max_width, max(8, config["font_size"] - 1), bold=True, color=text_color, leading=line_gap)
                if item.get("description"):
                    y = draw_wrapped(item["description"], x, y, max_width, max(8, config["font_size"] - 1), color=text_color, leading=line_gap)
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

        contact = payload.get("contact", {})
        name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
        details = [str(value) for value in (contact.get("email"), contact.get("phone"), contact.get("location")) if value]
        if payload.get("linkedin_url"):
            details.append(payload["linkedin_url"])
        if payload.get("portfolio_url"):
            details.append(payload["portfolio_url"])

        design = config["design_style"]
        header_align = "center" if config["header_style"] == "centered" else "left"
        header_x = margin
        header_width = width - (2 * margin)
        y = height - margin
        split_main_x = split_main_y = split_main_width = None

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
        elif design == "split_label":
            teal = colors.HexColor("#2c806e")
            dark = colors.HexColor("#404040")
            sidebar_width = width * 0.34
            main_x = sidebar_width + margin
            main_width = width - main_x - margin
            pdf.setFillColor(teal)
            pdf.rect(0, 0, sidebar_width, height, stroke=0, fill=1)
            pdf.setFillColor(dark)
            pdf.rect(0, height - 168, sidebar_width, 168, stroke=0, fill=1)
            pdf.setStrokeColor(colors.Color(0.12, 0.65, 0.62, alpha=.35))
            pdf.setLineWidth(.5)
            for px in range(0, int(sidebar_width) + 24, 18):
                for py in range(0, int(height - 168), 18):
                    pdf.line(px, py, px + 10, py + 8)
                    pdf.line(px + 10, py + 8, px, py + 16)
            photo_x = sidebar_width / 2
            photo_y = height - 110
            pdf.setStrokeColor(colors.HexColor("#202020"))
            pdf.setLineWidth(2.4)
            pdf.circle(photo_x, photo_y, 46, stroke=1, fill=0)
            pdf.circle(photo_x, photo_y + 12, 21, stroke=1, fill=0)
            pdf.arc(photo_x - 31, photo_y - 40, photo_x + 31, photo_y + 20, startAng=20, extent=140)

            side_x = 16
            side_width = sidebar_width - 32
            side_y = height - 190
            if contact.get("location"):
                side_y = draw_wrapped(f"⌖ {contact['location']}", side_x, side_y, side_width, 7.5, color=colors.white, leading=11)
            if contact.get("phone"):
                side_y = draw_wrapped(f"⌕ {contact['phone']}", side_x, side_y, side_width, 7.5, color=colors.white, leading=11)
            if contact.get("email"):
                side_y = draw_wrapped(f"✉ {contact['email']}", side_x, side_y, side_width, 7.2, color=colors.white, leading=10)
            if payload.get("linkedin_url"):
                side_y = draw_wrapped(f"in {payload['linkedin_url']}", side_x, side_y, side_width, 7.0, color=colors.white, leading=10)
            if payload.get("summary"):
                side_y -= 8
                side_y = section_heading("Summary", side_x, side_y, side_width, white=True)
                side_y = draw_wrapped(payload["summary"], side_x, side_y, side_width, 7.8, color=colors.white, leading=10) - 8
            if payload.get("skills"):
                side_y = section_heading("Skills", side_x, side_y, side_width, white=True)
                for item in payload["skills"]:
                    side_y = draw_wrapped(f"• {item.get('name', '')}", side_x, side_y, side_width, 7.6, color=colors.white, leading=10)
                side_y -= 5
            if payload.get("languages"):
                side_y = section_heading("Languages", side_x, side_y, side_width, white=True)
                for item in payload["languages"]:
                    side_y = draw_wrapped(f"• {item.get('name', '')}", side_x, side_y, side_width, 7.6, color=colors.white, leading=10)

            if name:
                split_main_y = draw_wrapped(name, main_x, height - 62, main_width, config["heading_size"] + 10, bold=True, color=teal, leading=config["heading_size"] + 12)
            else:
                split_main_y = height - 62
            if payload.get("professional_title"):
                split_main_y -= 2
                split_main_y = draw_wrapped(payload["professional_title"], main_x, split_main_y, main_width, config["font_size"] + 1, color=teal, leading=config["font_size"] + 4)
            pdf.setStrokeColor(teal)
            pdf.setLineWidth(.8)
            pdf.line(main_x, split_main_y - 8, width - margin, split_main_y - 8)
            split_main_y -= 30
            split_main_x = main_x
            split_main_width = main_width
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

        all_sections = (
            ("Summary", payload.get("summary"), "text"),
            ("Experience", payload.get("experiences", []), "experience"),
            ("Education", payload.get("educations", []), "education"),
            ("Skills", payload.get("skills", []), "skill_group"),
            ("Projects", payload.get("projects", []), "project"),
            ("Certifications", payload.get("certifications", []), "certification"),
            ("Achievements", payload.get("achievements", []), "achievement"),
        )

        if design == "split_label":
            main_sections = (
                ("Experience", payload.get("experiences", []), "experience"),
                ("Education", payload.get("educations", []), "education"),
                ("Projects", payload.get("projects", []), "project"),
                ("Certifications", payload.get("certifications", []), "certification"),
                ("Achievements", payload.get("achievements", []), "achievement"),
            )
            render_sections(main_sections, split_main_x, split_main_y, split_main_width)
        elif config["layout"] == "sidebar":
            sidebar_width = max(145, min(175, width * 0.27))
            column_gap = 18
            main_x = margin
            side_x = width - margin - sidebar_width
            main_width = side_x - column_gap - main_x
            side_y = y
            pdf.setFillColor(accent_color)
            pdf.rect(side_x - 8, 0, sidebar_width + 8, height, stroke=0, fill=1)
            original_accent = accent_color
            original_body = body_color
            accent_color = colors.white
            body_color = colors.white
            sidebar_sections = (
                ("Skills", payload.get("skills", []), "skill_group"),
                ("Education", payload.get("educations", []), "education"),
                ("Certifications", payload.get("certifications", []), "certification"),
            )
            render_sections(sidebar_sections, side_x, side_y, sidebar_width - 12, white=True)
            accent_color = original_accent
            body_color = original_body
            main_sections = (
                ("Summary", payload.get("summary"), "text"),
                ("Experience", payload.get("experiences", []), "experience"),
                ("Projects", payload.get("projects", []), "project"),
                ("Achievements", payload.get("achievements", []), "achievement"),
            )
            render_sections(main_sections, main_x, y, main_width)
        elif design in {"elegant"}:
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
