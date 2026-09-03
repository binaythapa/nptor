from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from organizations.models.membership import OrganizationMember
from organizations.models.organization import Organization
from organizations.models.role import OrganizationRole
from quiz.models import Exam, UserExam


User = get_user_model()


class OrganizationExamMutationSecurityTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Exam Security School",
            slug="exam-security-school",
            org_type=Organization.TYPE_SCHOOL,
            is_active=True,
        )
        self.admin = User.objects.create_user(
            username="exam-admin",
            email="exam-admin@example.com",
            password="password",
        )
        self.student = User.objects.create_user(
            username="exam-student",
            email="exam-student@example.com",
            password="password",
        )
        OrganizationMember.objects.create(
            user=self.admin,
            organization=self.organization,
            role=OrganizationRole.ORG_ADMIN,
            is_active=True,
        )
        self.exam = Exam.objects.create(
            title="Protected Exam",
            organization=self.organization,
            duration_seconds=60,
            is_free=False,
            price=100,
            is_published=False,
        )

    def _url(self, name, **kwargs):
        return reverse(
            f"organizations_admin:{name}",
            kwargs={"slug": self.organization.slug, **kwargs},
        )

    def test_org_admin_cannot_publish_exam_during_create(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            self._url("exam_create"),
            {
                "title": "Published Too Early",
                "question_count": 10,
                "duration_seconds": 60,
                "level": 1,
                "passing_score": 50,
                "is_free": "on",
                "is_published": "on",
                "max_mock_attempts": 3,
                "allow_review": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        created = Exam.objects.get(title="Published Too Early")
        self.assertFalse(created.is_published)

    def test_org_admin_cannot_update_published_exam(self):
        self.exam.is_published = True
        self.exam.save(update_fields=["is_published"])
        self.client.force_login(self.admin)

        response = self.client.post(
            self._url("exam_update", pk=self.exam.pk),
            {
                "title": "Tampered Published Exam",
                "question_count": 99,
                "duration_seconds": 3600,
                "level": 1,
                "passing_score": 10,
                "is_free": "on",
                "is_published": "on",
                "max_mock_attempts": 3,
                "allow_review": "on",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.exam.refresh_from_db()
        self.assertEqual(self.exam.title, "Protected Exam")
        self.assertEqual(self.exam.question_count, 10)

    def test_org_admin_cannot_delete_exam_with_attempt_history(self):
        UserExam.objects.create(
            user=self.student,
            exam=self.exam,
        )
        self.client.force_login(self.admin)

        response = self.client.post(
            self._url("exam_delete", pk=self.exam.pk),
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Exam.objects.filter(pk=self.exam.pk).exists())
