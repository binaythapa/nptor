from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from quiz.views.course_exam_start import _course_access_allows_quiz
from quiz.views.exam_submission import _course_quiz_return_redirect
from quiz.views.practice import _course_practice_return_redirect


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


class CourseExamReturnRedirectTests(SimpleTestCase):
    def test_course_quiz_returns_to_course_lesson(self):
        request = SimpleNamespace(
            session={
                "course_exam_context": {
                    "course_slug": "demo-aws-cloud-course",
                    "lesson_id": 8,
                }
            }
        )

        response = _course_quiz_return_redirect(request)

        self.assertIsNotNone(response)
        self.assertEqual(
            response.url,
            "/courses/demo-aws-cloud-course/learn/8/",
        )

    def test_standalone_exam_has_no_course_return_redirect(self):
        request = SimpleNamespace(session={})

        self.assertIsNone(_course_quiz_return_redirect(request))


class CoursePracticeReturnRedirectTests(SimpleTestCase):
    def test_course_practice_returns_to_course_lesson(self):
        request = SimpleNamespace(
            session={
                "course_practice_context": {
                    "course_slug": "demo-aws-cloud-course",
                    "lesson_id": 7,
                }
            }
        )

        response = _course_practice_return_redirect(request)

        self.assertIsNotNone(response)
        self.assertEqual(
            response.url,
            "/courses/demo-aws-cloud-course/learn/7/",
        )

    def test_standalone_practice_has_no_course_return_redirect(self):
        request = SimpleNamespace(session={})

        self.assertIsNone(_course_practice_return_redirect(request))
