from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from organizations.models import Organization, OrganizationMember
from organizations.models.role import OrganizationRole
from quiz.models import Exam


User = get_user_model()


class AdminAutocompleteExamTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="teacher", password="test-pass")
        self.other_user = User.objects.create_user(username="other", password="test-pass")
        self.organization = Organization.objects.create(
            name="Test Institute",
            slug="test-institute",
            org_type=Organization.TYPE_INSTITUTE,
            created_by=self.user,
        )
        OrganizationMember.objects.create(
            user=self.user,
            organization=self.organization,
            role=OrganizationRole.STAFF,
            is_active=True,
        )
        self.exam = Exam.objects.create(
            title="Snowflake Engineering",
            organization=self.organization,
            question_count=10,
            duration_seconds=600,
            is_published=True,
        )
        self.global_exam = Exam.objects.create(
            title="SQL Fundamentals",
            organization=None,
            question_count=10,
            duration_seconds=600,
            is_published=True,
        )
        self.url = reverse("quiz:admin_autocomplete")

    def test_organization_teacher_can_search_organization_exams(self):
        self.client.force_login(self.user)
        response = self.client.get(
            self.url,
            {"scope": "exams", "q": "Snow", "organization": self.organization.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()["results"]], [self.exam.pk])

    def test_organization_teacher_can_search_global_exams(self):
        self.client.force_login(self.user)
        response = self.client.get(
            self.url,
            {"scope": "exams", "q": "SQL", "organization": self.organization.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()["results"]], [self.global_exam.pk])

    def test_non_member_cannot_search_organization_exams(self):
        self.client.force_login(self.other_user)
        response = self.client.get(
            self.url,
            {"scope": "exams", "q": "Snow", "organization": self.organization.pk},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["results"], [])
