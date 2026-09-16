from django.test import SimpleTestCase
from django.template.loader import render_to_string


class AdminBaseTemplateTests(SimpleTestCase):
    def test_admin_base_loads_bulma_stylesheet(self):
        html = render_to_string("layouts/admin/base_admin.html")

        self.assertIn(
            'https://cdn.jsdelivr.net/npm/bulma@0.9.4/css/bulma.min.css',
            html,
        )
