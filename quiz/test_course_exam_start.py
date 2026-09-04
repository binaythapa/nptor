from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from quiz.views.course_exam_start import _course_access_allows_quiz


class CourseExamAccessTests(SimpleTestCase):
    @patch("quiz.views.course_exam_start.get_plan_for_course")
    def test_free_course_allows_quiz_without_separate_exam_entitlement(self, get_plan):
        get_plan.return_value = SimpleNamespace(price=0)

        self.assertTrue(
            _course_access_allows_quiz(
                SimpleNamespace(),
                SimpleNamespace(),
            )
        )

    @patch("quiz.views.course_exam_start.AccessService.has_access", return_value=True)
    @patch("quiz.views.course_exam_start.get_plan_for_course")
    def test_paid_course_access_allows_course_quiz(self, get_plan, has_access):
        get_plan.return_value = SimpleNamespace(price=100)
        user = SimpleNamespace(id=1)
        course = SimpleNamespace(id=2)

        self.assertTrue(_course_access_allows_quiz(user, course))
        has_access.assert_called_once()

    @patch("quiz.views.course_exam_start.AccessService.has_access", return_value=False)
    @patch("quiz.views.course_exam_start.get_plan_for_course")
    def test_paid_course_without_access_denies_course_quiz(self, get_plan, has_access):
        get_plan.return_value = SimpleNamespace(price=100)
        user = SimpleNamespace(id=1)
        course = SimpleNamespace(id=2)

        self.assertFalse(_course_access_allows_quiz(user, course))
        has_access.assert_called_once()
