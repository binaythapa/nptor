from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from courses.models import Course, Lesson
from courses.services.quiz_completion import handle_course_quiz_completion


class QuizCompletionAuthorizationTests(SimpleTestCase):
    def setUp(self):
        self.request = SimpleNamespace(
            user=SimpleNamespace(id=10),
        )

        self.course = SimpleNamespace(
            slug="private-course",
            approval_status=Course.APPROVAL_APPROVED,
            is_published=True,
            is_public=True,
        )
        self.exam = SimpleNamespace(id=99)
        self.lesson = SimpleNamespace(
            section=SimpleNamespace(course=self.course),
            exam_id=99,
            quiz_completion_mode="attempt",
            quiz_min_score=0,
        )
        self.user_exam = SimpleNamespace(
            exam_id=99,
            passed=True,
            score=100,
        )

    @patch("courses.services.quiz_completion.LessonProgress.objects.get_or_create")
    @patch("courses.services.quiz_completion.AccessService.has_access", return_value=False)
    @patch("courses.services.quiz_completion.get_plan_for_course")
    @patch("courses.services.quiz_completion.Lesson.objects.get")
    def test_inaccessible_paid_course_cannot_be_marked_complete(
        self,
        lesson_get,
        get_plan,
        has_access,
        get_or_create,
    ):
        lesson_get.return_value = self.lesson
        get_plan.return_value = SimpleNamespace(price=100)

        handle_course_quiz_completion(
            request=self.request,
            user_exam=self.user_exam,
            context={
                "course_slug": "private-course",
                "lesson_id": 123,
            },
        )

        has_access.assert_called_once()
        get_or_create.assert_not_called()

    @patch("courses.services.quiz_completion.LessonProgress.objects.get_or_create")
    @patch("courses.services.quiz_completion.Lesson.objects.get")
    def test_mismatched_course_context_cannot_complete_lesson(
        self,
        lesson_get,
        get_or_create,
    ):
        lesson_get.return_value = self.lesson

        handle_course_quiz_completion(
            request=self.request,
            user_exam=self.user_exam,
            context={
                "course_slug": "another-course",
                "lesson_id": 123,
            },
        )

        get_or_create.assert_not_called()

    @patch("courses.services.quiz_completion.LessonProgress.objects.get_or_create")
    @patch("courses.services.quiz_completion.Lesson.objects.get")
    def test_mismatched_exam_cannot_complete_lesson(
        self,
        lesson_get,
        get_or_create,
    ):
        lesson_get.return_value = self.lesson
        self.user_exam.exam_id = 1000

        handle_course_quiz_completion(
            request=self.request,
            user_exam=self.user_exam,
            context={
                "course_slug": "private-course",
                "lesson_id": 123,
            },
        )

        get_or_create.assert_not_called()

    @patch("courses.services.quiz_completion.LessonProgress.objects.get_or_create")
    @patch("courses.services.quiz_completion.Lesson.objects.get")
    def test_missing_course_context_does_not_create_progress(
        self,
        lesson_get,
        get_or_create,
    ):
        handle_course_quiz_completion(
            request=self.request,
            user_exam=self.user_exam,
            context={"lesson_id": 123},
        )

        lesson_get.assert_not_called()
        get_or_create.assert_not_called()
