from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from courses.models import Course
from quiz.models import Category, Domain, Exam, ExamTrack, LearningShortlist


User = get_user_model()


class LearningShortlistModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="shortlist-user",
            password="test-password",
        )
        self.domain = Domain.objects.create(
            name="Snowflake",
            slug="snowflake",
            is_active=True,
        )
        self.category = Category.objects.create(
            name="Snowflake Core",
            slug="snowflake-core",
            domain=self.domain,
            is_active=True,
        )
        self.course = Course.objects.create(
            title="Snowflake Fundamentals",
            description="Learn Snowflake.",
            category=self.category,
            level="beginner",
            is_public=True,
            is_published=True,
            approval_status=Course.APPROVAL_APPROVED,
        )
        self.track = ExamTrack.objects.create(
            title="SnowPro Core Track",
            slug="snowpro-core",
            is_active=True,
        )
        self.exam = Exam.objects.create(
            title="Snowflake Core Exam",
            track=self.track,
            primary_category=self.category,
            question_count=10,
            duration_seconds=1800,
            is_published=True,
            is_free=False,
        )

    def test_for_resource_creates_and_reuses_a_single_course_entry(self):
        first_item, first_created = LearningShortlist.for_resource(
            user=self.user,
            resource_type=LearningShortlist.RESOURCE_COURSE,
            resource=self.course,
        )
        second_item, second_created = LearningShortlist.for_resource(
            user=self.user,
            resource_type=LearningShortlist.RESOURCE_COURSE,
            resource=self.course,
        )

        self.assertTrue(first_created)
        self.assertFalse(second_created)
        self.assertEqual(first_item.pk, second_item.pk)
        self.assertEqual(LearningShortlist.objects.count(), 1)

    def test_resource_type_must_match_the_selected_resource(self):
        item = LearningShortlist(
            user=self.user,
            resource_type=LearningShortlist.RESOURCE_EXAM,
            course=self.course,
        )

        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_each_user_can_shortlist_course_exam_and_track_independently(self):
        LearningShortlist.for_resource(
            user=self.user,
            resource_type=LearningShortlist.RESOURCE_COURSE,
            resource=self.course,
        )
        LearningShortlist.for_resource(
            user=self.user,
            resource_type=LearningShortlist.RESOURCE_TRACK,
            resource=self.track,
        )
        LearningShortlist.for_resource(
            user=self.user,
            resource_type=LearningShortlist.RESOURCE_EXAM,
            resource=self.exam,
        )

        self.assertEqual(LearningShortlist.objects.count(), 3)

    def test_remove_for_resource_deletes_only_the_selected_item(self):
        LearningShortlist.for_resource(
            user=self.user,
            resource_type=LearningShortlist.RESOURCE_COURSE,
            resource=self.course,
        )
        LearningShortlist.for_resource(
            user=self.user,
            resource_type=LearningShortlist.RESOURCE_EXAM,
            resource=self.exam,
        )

        removed = LearningShortlist.remove_for_resource(
            user=self.user,
            resource_type=LearningShortlist.RESOURCE_COURSE,
            resource=self.course,
        )

        self.assertTrue(removed)
        self.assertEqual(LearningShortlist.objects.count(), 1)
        self.assertFalse(
            LearningShortlist.objects.filter(course=self.course).exists()
        )
