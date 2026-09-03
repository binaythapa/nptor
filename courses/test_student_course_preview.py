from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from courses.models import Course, CourseSection, Lesson
from quiz.models import Category, Domain


User = get_user_model()


class StudentCoursePreviewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="course-preview-user",
            password="test-password",
        )
        domain = Domain.objects.create(
            name="AWS",
            slug="aws",
            is_active=True,
        )
        category = Category.objects.create(
            name="Cloud Fundamentals",
            slug="cloud-fundamentals",
            domain=domain,
            is_active=True,
        )
        self.course = Course.objects.create(
            title="AWS Fundamentals",
            slug="aws-fundamentals",
            description="Learn AWS fundamentals.",
            category=category,
            level="beginner",
            is_public=True,
            is_published=True,
            approval_status=Course.APPROVAL_APPROVED,
        )
        section = CourseSection.objects.create(
            course=self.course,
            title="Getting Started",
            order=1,
        )
        self.preview_lesson = Lesson.objects.create(
            section=section,
            title="What is AWS?",
            lesson_type=Lesson.TYPE_ARTICLE,
            order=1,
            article_content="AWS is a cloud platform.",
        )
        self.locked_lesson = Lesson.objects.create(
            section=section,
            title="Advanced AWS",
            lesson_type=Lesson.TYPE_ARTICLE,
            order=2,
            article_content="Advanced content.",
        )

    def test_preview_requires_login(self):
        response = self.client.get(
            reverse("courses:course_preview", args=[self.course.slug])
        )
        self.assertEqual(response.status_code, 302)

    def test_preview_exposes_only_the_first_lesson_as_preview(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("courses:course_preview", args=[self.course.slug])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["preview_lesson"], self.preview_lesson)
        self.assertContains(response, self.preview_lesson.title)
        self.assertContains(response, "Get full access")
        self.assertNotContains(response, self.locked_lesson.article_content)
