from django.db import migrations


TEMPLATES = {
    "ats-classic": {
        "name": "ATS Classic",
        "description": "Clean, ATS-friendly single-column layout.",
        "config": {"template_version": 3, "font_name": "Helvetica", "font_size": 10, "heading_size": 12, "margin": 48, "accent_color": "#111827", "layout": "single_column", "header_style": "left", "section_style": "uppercase_rule", "density": "comfortable"},
    },
    "modern-professional": {
        "name": "Modern Professional",
        "description": "Contemporary two-column layout with a visual skills rail.",
        "config": {"template_version": 3, "font_name": "Helvetica", "font_size": 10, "heading_size": 12, "margin": 44, "accent_color": "#2563eb", "layout": "sidebar", "header_style": "left", "section_style": "uppercase_rule", "density": "comfortable"},
    },
    "executive": {
        "name": "Executive",
        "description": "Leadership-focused layout for senior professionals.",
        "config": {"template_version": 3, "font_name": "Times-Roman", "font_size": 10, "heading_size": 13, "margin": 52, "accent_color": "#1f2937", "layout": "single_column", "header_style": "centered", "section_style": "title_case", "density": "comfortable"},
    },
    "technical": {
        "name": "Technical",
        "description": "Skills and project-focused layout for technical roles.",
        "config": {"template_version": 3, "font_name": "Helvetica", "font_size": 9, "heading_size": 11, "margin": 42, "accent_color": "#0f766e", "layout": "sidebar", "header_style": "compact", "section_style": "minimal", "density": "compact"},
    },
    "fresher": {
        "name": "Fresher",
        "description": "Entry-level layout emphasizing education, skills, and projects.",
        "config": {"template_version": 3, "font_name": "Helvetica", "font_size": 10, "heading_size": 12, "margin": 46, "accent_color": "#7c3aed", "layout": "single_column", "header_style": "centered", "section_style": "uppercase_rule", "density": "comfortable"},
    },
    "academic": {
        "name": "Academic",
        "description": "Academic-oriented layout for education and research profiles.",
        "config": {"template_version": 3, "font_name": "Times-Roman", "font_size": 10, "heading_size": 12, "margin": 54, "accent_color": "#374151", "layout": "single_column", "header_style": "left", "section_style": "title_case", "density": "comfortable"},
    },
    "government": {
        "name": "Government",
        "description": "Formal layout suited to government and public-sector applications.",
        "config": {"template_version": 3, "font_name": "Times-Roman", "font_size": 10, "heading_size": 12, "margin": 58, "accent_color": "#374151", "layout": "single_column", "header_style": "left", "section_style": "title_case", "density": "comfortable"},
    },
    "minimal": {
        "name": "Minimal",
        "description": "Simple typography-first layout with minimal decoration.",
        "config": {"template_version": 3, "font_name": "Helvetica", "font_size": 9, "heading_size": 11, "margin": 44, "accent_color": "#111827", "layout": "single_column", "header_style": "compact", "section_style": "minimal", "density": "compact"},
    },
}


def seed_templates(apps, schema_editor):
    CVTemplate = apps.get_model("cv", "CVTemplate")
    for slug, values in TEMPLATES.items():
        CVTemplate.objects.update_or_create(slug=slug, defaults={**values, "is_active": True})


def unseed_templates(apps, schema_editor):
    CVTemplate = apps.get_model("cv", "CVTemplate")
    CVTemplate.objects.filter(slug__in=TEMPLATES).delete()


class Migration(migrations.Migration):
    dependencies = [("cv", "0010_ats_job_description")]

    operations = [migrations.RunPython(seed_templates, unseed_templates)]
