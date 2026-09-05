from pathlib import Path

from django.test import SimpleTestCase


class DomainHubContractTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        root = Path(__file__).resolve().parent.parent
        cls.template = (root / "templates" / "quiz" / "student" / "domain_hub.html").read_text(encoding="utf-8")
        cls.view = (root / "quiz" / "views" / "learning_marketplace.py").read_text(encoding="utf-8")

    def test_domain_hub_has_product_focused_sections_and_filters(self):
        for hook in (
            'class="domain-hero"', 'class="domain-stats"', 'class="domain-tabs"',
            'class="domain-filter-bar"', 'name="pricing"', 'name="access"',
            'class="resource-grid"', 'class="marketplace-empty"',
        ):
            self.assertIn(hook, self.template)

    def test_domain_hub_preserves_all_catalog_filters_in_navigation(self):
        for name in ("q", "type", "category", "level", "access", "pricing", "page"):
            self.assertIn(f'name="{name}"', self.template)
        for value in ("courses", "tracks", "exams"):
            self.assertIn(value, self.template)

    def test_domain_view_reads_access_and_pricing_filters(self):
        for expression in (
            'request.GET.get("access", "").strip().lower()',
            'request.GET.get("pricing", "").strip().lower()',
            'access=access', 'pricing=pricing',
        ):
            self.assertIn(expression, self.view)

    def test_domain_hub_explains_domain_scope_and_empty_state(self):
        for text in (
            "Explore courses, exam tracks, and practice exams",
            "Learning resources", "No resources match these filters.",
        ):
            self.assertIn(text, self.template)
