from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cv.models import CareerExperience, CareerProfile, CV, CVTemplate


class CVBuilderTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="builder", password="password")
        self.template = CVTemplate.objects.create(name="Builder Template", slug="builder-template", is_active=True)
        self.profile = CareerProfile.objects.create(user=self.user)
        self.experience = CareerExperience.objects.create(
            profile=self.profile, job_title="Data Engineer", employer="NPTOR", description="Built pipelines."
        )
        self.client.force_login(self.user)

    def test_builder_saves_selection_and_overrides(self):
        cv = CV.objects.create(owner=self.user, profile=self.profile, template=self.template, title="Original CV")
        response = self.client.post(
            reverse("cv:cv_builder", kwargs={"pk": cv.pk}),
            {
                "title": "Tailored Data CV",
                "template": self.template.pk,
                "status": CV.STATUS_DRAFT,
                "professional_title": "Senior Data Engineer",
                "summary": "Cloud data engineering leader.",
                "linkedin_url": "https://linkedin.com/in/example",
                "portfolio_url": "https://example.com",
                "experiences": [str(self.experience.pk)],
                "educations": [],
                "skills": [],
                "certifications": [],
                "projects": [],
                "achievements": [],
            },
        )

        self.assertRedirects(response, reverse("cv:cv_builder", kwargs={"pk": cv.pk}))
        cv.refresh_from_db()
        self.assertEqual(cv.title, "Tailored Data CV")
        self.assertEqual(cv.overrides["professional_title"], "Senior Data Engineer")
        self.assertEqual(cv.overrides["summary"], "Cloud data engineering leader.")
        self.assertEqual(cv.selected_sections["experiences"], [self.experience.pk])
        self.assertEqual(cv.selected_sections["educations"], [])

    def test_builder_rejects_another_users_cv(self):
        other = get_user_model().objects.create_user(username="other-builder", password="password")
        cv = CV.objects.create(owner=other, profile=CareerProfile.objects.create(user=other), template=self.template, title="Private CV")
        response = self.client.get(reverse("cv:cv_builder", kwargs={"pk": cv.pk}))
        self.assertEqual(response.status_code, 404)
