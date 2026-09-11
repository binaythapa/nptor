from pathlib import Path

from django.test import SimpleTestCase


class CourseTemplateRegressionTests(SimpleTestCase):
    def test_course_base_has_only_one_content_block(self):
        template = Path("templates/courses/base.html").read_text(encoding="utf-8")
        self.assertEqual(template.count("{% block content %}"), 1)
