from pathlib import Path

from django.test import SimpleTestCase
from django.template.loader import get_template


class CourseStudentResponsiveTemplateTests(SimpleTestCase):
    def test_course_player_contains_mobile_navigation_hooks(self):
        template = get_template("courses/student/course_player.html")
        source = Path(template.origin.name).read_text(encoding="utf-8")

        self.assertIn('class="mobile-menu-btn"', source)
        self.assertIn('id="courseSidebar"', source)
        self.assertIn('id="sidebarBackdrop"', source)
        self.assertIn('class="lesson-navigation"', source)
        self.assertIn('class="lesson-nav-prev"', source)
        self.assertIn('class="lesson-nav-next"', source)
        self.assertIn("course-mobile.css", source)

    def test_course_detail_contains_responsive_structure(self):
        template = get_template("courses/student/course_detail.html")
        source = Path(template.origin.name).read_text(encoding="utf-8")

        self.assertIn('class="course-detail-card"', source)
        self.assertIn('class="course-detail-actions"', source)
        self.assertIn("course-mobile.css", source)


class PreviousLessonHelperTests(SimpleTestCase):
    def test_previous_lesson_helper_is_exposed_by_progress_service(self):
        from courses.services.progress import get_previous_lesson

        self.assertTrue(callable(get_previous_lesson))
