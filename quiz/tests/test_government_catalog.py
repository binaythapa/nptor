from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from quiz.models import (
    ContentVertical,
    Country,
    GovernmentBody,
    GovernmentExamProgram,
    GovernmentJob,
)


class GovernmentCatalogViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="catalog-user",
            password="test-pass-123",
        )
        self.client.force_login(self.user)
        self.vertical = ContentVertical.objects.create(
            name="Government / Competitive Exam",
            code="government-exam",
            vertical_type=ContentVertical.GOVERNMENT_EXAM,
        )
        self.country = Country.objects.create(
            name="Nepal", code="NPL", slug="nepal", is_active=True
        )
        self.body = GovernmentBody.objects.create(
            country=self.country,
            name="Public Service Commission",
            code="psc",
            slug="psc",
            is_active=True,
        )
        self.job = GovernmentJob.objects.create(
            country=self.country,
            government_body=self.body,
            name="Section Officer",
            code="section-officer",
            slug="section-officer",
            is_active=True,
        )
        self.program = GovernmentExamProgram.objects.create(
            country=self.country,
            government_body=self.body,
            content_vertical=self.vertical,
            name="Section Officer Recruitment",
            code="section-officer",
            slug="section-officer",
            is_active=True,
        )
        self.program.jobs.add(self.job)

    def test_country_body_and_program_slug_traversal(self):
        response = self.client.get(
            reverse(
                "quiz:government_program",
                kwargs={
                    "country_slug": "nepal",
                    "body_slug": "psc",
                    "program_slug": "section-officer",
                },
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Section Officer Recruitment")
        self.assertContains(response, "Section Officer")

    def test_inactive_country_is_excluded(self):
        self.country.is_active = False
        self.country.save(update_fields=["is_active"])
        response = self.client.get(reverse("quiz:government_catalog"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Nepal")

    def test_inactive_body_is_excluded_from_country_page(self):
        self.body.is_active = False
        self.body.save(update_fields=["is_active"])
        response = self.client.get(
            reverse("quiz:government_country", kwargs={"country_slug": "nepal"})
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Public Service Commission")

    def test_inactive_program_is_excluded_from_body_page(self):
        self.program.is_active = False
        self.program.save(update_fields=["is_active"])
        response = self.client.get(
            reverse(
                "quiz:government_body",
                kwargs={"country_slug": "nepal", "body_slug": "psc"},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Section Officer Recruitment")
