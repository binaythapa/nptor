from pathlib import Path

from django.test import SimpleTestCase


class CourseDetailMarketplaceContractTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        root = Path(__file__).resolve().parent.parent
        cls.template = (root / "templates" / "courses" / "student" / "course_detail.html").read_text(encoding="utf-8")
        cls.styles = (root / "static" / "css" / "pages" / "course-detail.css").read_text(encoding="utf-8")

    def test_course_detail_has_sales_and_learning_sections(self):
        for hook in (
            'class="course-detail-hero"',
            'class="course-detail-purchase-card"',
            'class="course-outcomes"',
            'class="course-curriculum-preview"',
            'class="course-related-resources"',
            'class="course-instructor"',
        ):
            self.assertIn(hook, self.template)

    def test_course_detail_explains_access_states_and_preview(self):
        for text in (
            "Free",
            "Premium",
            "You are enrolled",
            "Preview mode",
            "Lifetime access",
            "Certificate included",
        ):
            self.assertIn(text, self.template)

    def test_course_detail_has_conversion_and_related_resource_hooks(self):
        for text in (
            "Get Full Access",
            "Start Learning",
            "Continue Learning",
            "Related certification paths",
            "Related exams",
        ):
            self.assertIn(text, self.template)

    def test_course_detail_is_responsive_and_accessible(self):
        for text in (
            "aria-labelledby=\"course-title\"",
            "aria-label=\"Course curriculum\"",
            "@media (max-width: 900px)",
            "@media (max-width: 640px)",
            "@media (prefers-reduced-motion: reduce)",
        ):
            self.assertIn(text, self.template if text.startswith("aria-") else self.styles)
