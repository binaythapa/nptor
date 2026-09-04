from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from courses.models import Course, CourseSection, Lesson
from subscriptions.models import SubscriptionPlan


User = get_user_model()


class CourseFreePreviewTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="free-preview-student",
            password="test-password",
        )
        self.owner = User.objects.create_user(
            username="free-preview-owner",
            password="test-password",
        )
        plan = SubscriptionPlan.objects.create(
            name="Preview Paid Plan",
            code="preview-paid-plan",
            duration_days=30,
            price=Decimal("499.00"),
            currency="INR",
            is_active=True,
        )
        self.course = Course.objects.create(
            title="Free Preview Course",
            description="A paid course with a public free preview.",
            level="beginner",
            owner_type=Course.OWNER_PLATFORM,
            is_public=True,
            is_published=True,
            approval_status=Course.APPROVAL_APPROVED,
            created_by=self.owner,
        )
        self.course.subscription_plans.add(plan)
        section = CourseSection.objects.create(
            course=self.course,
            title="Getting Started",
            order=1,
        )
        self.lessons = [
            Lesson.objects.create(
                section=section,
                title=f"Free Lesson {index}",
                lesson_type=Lesson.TYPE_ARTICLE,
                order=index,
                article_content=f"Preview content {index}",
            )
            for index in range(1, 5)
        ]
        self.client.force_login(self.student)

    def test_paid_course_allows_first_three_lessons_as_free_preview(self):
        for lesson in self.lessons[:3]:
            response = self.client.get(
                f"/courses/{self.course.slug}/learn/{lesson.id}/?preview=1"
            )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["is_free_preview"])
            self.assertFalse(response.context["preview_locked"])
            self.assertContains(response, lesson.title)
            self.assertContains(response, f"Preview content {lesson.order}")

    def test_fourth_lesson_is_locked_without_course_access(self):
        lesson = self.lessons[3]

        response = self.client.get(
            f"/courses/{self.course.slug}/learn/{lesson.id}/?preview=1"
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["is_free_preview"])
        self.assertTrue(response.context["preview_locked"])
        self.assertContains(response, "Unlock Full Course")
        self.assertNotContains(response, "Preview content 4")

    def test_preview_entry_starts_with_first_free_lesson(self):
        response = self.client.get(
            f"/courses/{self.course.slug}/learn/?preview=1"
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_free_preview"])
        self.assertEqual(response.context["lesson"], self.lessons[0])

    def test_paid_course_without_preview_flag_remains_protected(self):
        response = self.client.get(
            f"/courses/{self.course.slug}/learn/"
        )

        self.assertEqual(response.status_code, 404)
