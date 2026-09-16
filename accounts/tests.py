from django.template.loader import get_template
from django.test import SimpleTestCase


class AdminBaseTemplateTests(SimpleTestCase):
    def test_admin_base_loads_bulma_stylesheet(self):
        template = get_template("layouts/admin/base_admin.html")

        self.assertIn(
            'https://cdn.jsdelivr.net/npm/bulma@0.9.4/css/bulma.min.css',
            template.template.source,
        )
