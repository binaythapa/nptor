from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from quiz.models import ContentVertical, Country, GovernmentBody, GovernmentExamProgram


class GovernmentDashboardViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="government-dashboard-user",
            password="test-pass-123",
        )
        self.client.force_login(self.user)
        vertical = ContentVertical.objects.create(
            name="Government / Competitive Exam",
            code="government-exam",
            vertical_type=ContentVertical.GOVERNMENT_EXAM,
        )
        country = Country.objects.create(
            name="Nepal", code="NPL", slug="nepal", is_active=True
        )
        body = GovernmentBody.objects.create(
            country=country,
            name="Public Service Commission",
            code="psc",
            slug="psc",
            is_active=True,
        )
        self.program = GovernmentExamProgram.objects.create(
            country=country,
            government_body=body,
            content_vertical=vertical,
            name="Section Officer Recruitment",
            code="section-officer",
            slug="section-officer",
            is_active=True,
        )
        self.kwargs = {
            "country_slug": "nepal",
            "body_slug": "psc",
            "program_slug": "section-officer",
        }

    def test_dashboard_renders_for_active_program(self):
        response = self.client.get(
            reverse("quiz:government_program_dashboard", kwargs=self.kwargs)
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Section Officer Recruitment")
        self.assertContains(response, "GOVERNMENT EXAM DASHBOARD")
        self.assertContains(response, "COURSES")
        self.assertContains(response, "MOCK EXAMS")

    def test_dashboard_rejects_inactive_program(self):
        self.program.is_active = False
        self.program.save(update_fields=["is_active"])
        response = self.client.get(
            reverse("quiz:government_program_dashboard", kwargs=self.kwargs)
        )
        self.assertEqual(response.status_code, 404)
