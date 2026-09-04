from pathlib import Path

from django.test import SimpleTestCase
from django.urls import resolve
from django.template.loader import get_template


class StudentLibraryUITests(SimpleTestCase):
    def test_student_library_routes_resolve_to_dedicated_views(self):
        expected = {
            "/courses/my-courses/": "my_courses",
            "/courses/continue-learning/": "continue_learning",
            "/courses/completed/": "completed_courses",
        }

        for path, view_name in expected.items():
            self.assertEqual(resolve(path).url_name, view_name)

    def test_student_library_template_has_all_learning_states_and_shared_layout(self):
        template = get_template("courses/student/student_library.html")
        source = Path(template.origin.name).read_text(encoding="utf-8")

        self.assertIn("layouts/student/base.html", source)
        self.assertIn("My Courses", source)
        self.assertIn("Continue Learning", source)
        self.assertIn("Completed Courses", source)
        self.assertIn("course-library-grid", source)
        self.assertIn("course-progress", source)
        self.assertIn("course-mobile.css", source)

    def test_course_catalog_template_uses_shared_student_layout(self):
        template = get_template("courses/student/course_list.html")
        source = Path(template.origin.name).read_text(encoding="utf-8")

        self.assertIn("layouts/student/base.html", source)
        self.assertIn("course-catalog-grid", source)
        self.assertIn("View Course", source)
        self.assertIn("course-catalog.css", source)
