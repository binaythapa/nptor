from django.test import SimpleTestCase
from django.template.loader import render_to_string


class CVTemplateRenderingTests(SimpleTestCase):
    def test_base_renderer_exposes_template_style_block(self):
        html = render_to_string(
            "cv/render/base.html",
            {"cv": type("CV", (), {"title": "Test CV"})(), "payload": {}, "config": {}},
        )
        self.assertIn("data-cv-template", html)

    def test_template_variants_have_distinct_visual_markers(self):
        variants = {
            "academic": "cv/render/academic.html",
            "ats_classic": "cv/render/ats_classic.html",
            "executive": "cv/render/executive.html",
            "fresher": "cv/render/fresher.html",
            "government": "cv/render/government.html",
            "minimal": "cv/render/minimal.html",
            "modern_professional": "cv/render/modern_professional.html",
            "technical": "cv/render/technical.html",
        }
        context = {
            "cv": type("CV", (), {"title": "Test CV"})(),
            "payload": {
                "contact": {"first_name": "Alex", "last_name": "Morgan", "email": "alex@example.com", "phone": "555-0100", "location": "New York"},
                "professional_title": "Product Designer",
                "summary": "A concise professional summary.",
                "experiences": [{"job_title": "Senior Designer", "employer": "Northstar", "description": "Led product design."}],
                "educations": [{"qualification": "B.Des", "institution": "State University", "field_of_study": "Design"}],
                "skills": [{"name": "Figma"}, {"name": "UX Research"}],
                "projects": [{"name": "Portfolio", "role": "Designer", "description": "Built a portfolio."}],
                "certifications": [{"name": "Certification", "issuer": "Institute"}],
                "achievements": [{"title": "Award", "description": "Recognized for design."}],
            },
            "config": {
                "font_name": "Helvetica", "font_size": 10, "heading_size": 12,
                "margin": 48, "accent_color": "#111827", "section_gap": 8,
                "layout": "single_column", "header_style": "left",
                "section_style": "uppercase_rule", "density": "comfortable",
            },
        }
        rendered = {slug: render_to_string(name, context) for slug, name in variants.items()}
        self.assertEqual(len(set(rendered.values())), 8)
        for slug in variants:
            self.assertIn(f"template-{slug.replace('_', '-')}", rendered[slug])
