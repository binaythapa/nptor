from django.test import TestCase

from cv.forms import CVForm


class CVCreateFormTests(TestCase):
    def test_create_form_hides_internal_overrides_field(self):
        form = CVForm()

        self.assertNotIn("overrides", form.fields)
        self.assertEqual(
            list(form.fields),
            ["title", "template", "status"],
        )
