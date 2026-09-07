from django.core.management.base import BaseCommand

from cv.models_template import CVTemplate


TEMPLATES = [
    ("ats-classic", "ATS Classic", "Clean, ATS-friendly single-column layout.", {"template_version": 3, "font_name": "Helvetica", "font_size": 10, "heading_size": 12, "margin": 48, "accent_color": "#111827", "layout": "single_column", "header_style": "left", "section_style": "uppercase_rule", "density": "comfortable"}),
    ("modern-professional", "Modern Professional", "Contemporary two-column layout with a visual skills rail.", {"template_version": 3, "font_name": "Helvetica", "font_size": 10, "heading_size": 12, "margin": 44, "accent_color": "#2563eb", "layout": "sidebar", "header_style": "left", "section_style": "uppercase_rule", "density": "comfortable"}),
    ("executive", "Executive", "Leadership-focused layout for senior professionals.", {"template_version": 3, "font_name": "Times-Roman", "font_size": 10, "heading_size": 13, "margin": 52, "accent_color": "#1f2937", "layout": "single_column", "header_style": "centered", "section_style": "title_case", "density": "comfortable"}),
    ("technical", "Technical", "Skills and project-focused layout for technical roles.", {"template_version": 3, "font_name": "Helvetica", "font_size": 9, "heading_size": 11, "margin": 42, "accent_color": "#0f766e", "layout": "sidebar", "header_style": "compact", "section_style": "minimal", "density": "compact"}),
    ("fresher", "Fresher", "Entry-level layout emphasizing education, skills, and projects.", {"template_version": 3, "font_name": "Helvetica", "font_size": 10, "heading_size": 12, "margin": 46, "accent_color": "#7c3aed", "layout": "single_column", "header_style": "centered", "section_style": "uppercase_rule", "density": "comfortable"}),
    ("academic", "Academic", "Academic-oriented layout for education and research profiles.", {"template_version": 3, "font_name": "Times-Roman", "font_size": 10, "heading_size": 12, "margin": 54, "accent_color": "#374151", "layout": "single_column", "header_style": "left", "section_style": "title_case", "density": "comfortable"}),
    ("government", "Government", "Formal layout suited to government and public-sector applications.", {"template_version": 3, "font_name": "Times-Roman", "font_size": 10, "heading_size": 12, "margin": 58, "accent_color": "#374151", "layout": "single_column", "header_style": "left", "section_style": "title_case", "density": "comfortable"}),
    ("minimal", "Minimal", "Simple typography-first layout with minimal decoration.", {"template_version": 3, "font_name": "Helvetica", "font_size": 9, "heading_size": 11, "margin": 44, "accent_color": "#111827", "layout": "single_column", "header_style": "compact", "section_style": "minimal", "density": "compact"}),
]


class Command(BaseCommand):
    help = "Create or update the default NPTOR CV templates."

    def handle(self, *args, **options):
        for slug, name, description, config in TEMPLATES:
            CVTemplate.objects.update_or_create(slug=slug, defaults={"name": name, "description": description, "config": config, "is_active": True})
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(TEMPLATES)} CV templates."))
