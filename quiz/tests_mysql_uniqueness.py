from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from courses.models import Course
from quiz.models import Exam, LearningShortlist, UserExam


class MySQLSafeQuizUniquenessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="mysql-safe-user")
        self.course = Course.objects.create(
            title="MySQL Safe Course",
            description="Test course",
            level="beginner",
            created_by=self.user,
        )
        self.exam = Exam.objects.create(
            title="MySQL Safe Exam",
            question_count=1,
            duration_seconds=60,
        )

    def test_shortlist_rejects_duplicate_course(self):
        LearningShortlist.objects.create(
            user=self.user,
            resource_type=LearningShortlist.RESOURCE_COURSE,
            course=self.course,
        )
        with self.assertRaises(ValidationError):
            LearningShortlist.objects.create(
                user=self.user,
                resource_type=LearningShortlist.RESOURCE_COURSE,
                course=self.course,
            )

    def test_shortlist_for_resource_is_idempotent(self):
        first, created = LearningShortlist.for_resource(
            user=self.user,
            resource_type=LearningShortlist.RESOURCE_COURSE,
            resource=self.course,
        )
        second, created_again = LearningShortlist.for_resource(
            user=self.user,
            resource_type=LearningShortlist.RESOURCE_COURSE,
            resource=self.course,
        )
        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(first.pk, second.pk)

    def test_user_exam_rejects_second_active_attempt(self):
        UserExam.objects.create(
            user=self.user,
            exam=self.exam,
            question_order=[],
        )
        with self.assertRaises(ValidationError):
            UserExam.objects.create(
                user=self.user,
                exam=self.exam,
                question_order=[],
            )

    def test_user_exam_allows_new_attempt_after_submission(self):
        first = UserExam.objects.create(
            user=self.user,
            exam=self.exam,
            question_order=[],
        )
        first.submit(score=80)
        second = UserExam.objects.create(
            user=self.user,
            exam=self.exam,
            question_order=[],
        )
        self.assertNotEqual(first.pk, second.pk)
