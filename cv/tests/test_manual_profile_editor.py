from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cv.forms import (
    CareerAchievementForm,
    CareerCertificationForm,
    CareerEducationForm,
    CareerExperienceForm,
    CareerProjectForm,
    CareerSkillForm,
)
from cv.models import (
    CareerAchievement,
    CareerCertification,
    CareerEducation,
    CareerExperience,
    CareerProfile,
    CareerProject,
    CareerSkill,
)


class ManualProfileEditorTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="manual-user", password="password")
        self.other_user = User.objects.create_user(username="manual-other", password="password")
        self.profile = CareerProfile.objects.create(user=self.user)
        self.other_profile = CareerProfile.objects.create(user=self.other_user)
        self.client.force_login(self.user)

    def test_profile_page_lists_all_manual_sections(self):
        CareerExperience.objects.create(profile=self.profile, job_title="Engineer", employer="Acme")
        CareerEducation.objects.create(profile=self.profile, institution="Uni", qualification="BSc")
        CareerProject.objects.create(profile=self.profile, name="Project X")
        CareerSkill.objects.create(profile=self.profile, name="Python")
        CareerAchievement.objects.create(profile=self.profile, title="Award")
        CareerCertification.objects.create(profile=self.profile, name="SnowPro")

        response = self.client.get(reverse("cv:profile"))

        self.assertEqual(response.status_code, 200)
        for value in ("Engineer", "BSc", "Project X", "Python", "Award", "SnowPro"):
            self.assertContains(response, value)

    def test_manual_forms_do_not_expose_internal_profile_fields(self):
        forms = (
            CareerExperienceForm(),
            CareerEducationForm(),
            CareerProjectForm(),
            CareerSkillForm(),
            CareerAchievementForm(),
            CareerCertificationForm(),
        )
        for form in forms:
            self.assertNotIn("sort_order", form.fields)
            self.assertNotIn("source", form.fields)
            self.assertNotIn("is_confirmed", form.fields)
            self.assertNotIn("profile", form.fields)

    def test_add_record_supports_every_manual_section(self):
        payloads = {
            "experience": {"job_title": "Data Engineer", "employer": "Acme"},
            "education": {"institution": "University", "qualification": "BSc"},
            "project": {"name": "ETL Platform"},
            "skill": {"name": "Snowflake"},
            "achievement": {"title": "Top Performer"},
            "certification": {"name": "SnowPro Core"},
        }
        models = {
            "experience": CareerExperience,
            "education": CareerEducation,
            "project": CareerProject,
            "skill": CareerSkill,
            "achievement": CareerAchievement,
            "certification": CareerCertification,
        }

        for section, payload in payloads.items():
            response = self.client.post(reverse("cv:profile_record_add", kwargs={"section": section}), payload)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(models[section].objects.filter(profile=self.profile).count(), 1)

    def test_edit_record_updates_owned_record(self):
        record = CareerExperience.objects.create(profile=self.profile, job_title="Engineer", employer="Old Co")

        response = self.client.post(
            reverse("cv:profile_record_edit", kwargs={"section": "experience", "pk": record.pk}),
            {"job_title": "Senior Engineer", "employer": "New Co"},
        )

        self.assertRedirects(response, reverse("cv:profile"))
        record.refresh_from_db()
        self.assertEqual(record.job_title, "Senior Engineer")
        self.assertEqual(record.employer, "New Co")

    def test_delete_record_requires_post(self):
        record = CareerSkill.objects.create(profile=self.profile, name="Python")

        response = self.client.get(
            reverse("cv:profile_record_delete", kwargs={"section": "skill", "pk": record.pk})
        )

        self.assertEqual(response.status_code, 405)
        self.assertTrue(CareerSkill.objects.filter(pk=record.pk).exists())

    def test_delete_record_removes_owned_record(self):
        record = CareerSkill.objects.create(profile=self.profile, name="Python")

        response = self.client.post(
            reverse("cv:profile_record_delete", kwargs={"section": "skill", "pk": record.pk})
        )

        self.assertRedirects(response, reverse("cv:profile"))
        self.assertFalse(CareerSkill.objects.filter(pk=record.pk).exists())

    def test_user_cannot_access_another_users_record(self):
        record = CareerCertification.objects.create(profile=self.other_profile, name="Private Cert")

        edit_response = self.client.get(
            reverse("cv:profile_record_edit", kwargs={"section": "certification", "pk": record.pk})
        )
        delete_response = self.client.post(
            reverse("cv:profile_record_delete", kwargs={"section": "certification", "pk": record.pk})
        )

        self.assertEqual(edit_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)
        self.assertTrue(CareerCertification.objects.filter(pk=record.pk).exists())

    def test_invalid_section_is_not_exposed(self):
        response = self.client.get(reverse("cv:profile_record_add", kwargs={"section": "invalid"}))
        self.assertEqual(response.status_code, 404)

    def test_date_fields_accept_iso_dates(self):
        response = self.client.post(
            reverse("cv:profile_record_add", kwargs={"section": "experience"}),
            {
                "job_title": "Engineer",
                "employer": "Acme",
                "start_date": "2025-01-15",
                "end_date": "2026-02-15",
            },
        )

        self.assertEqual(response.status_code, 302)
        record = CareerExperience.objects.get(profile=self.profile)
        self.assertEqual(record.start_date, date(2025, 1, 15))
        self.assertEqual(record.end_date, date(2026, 2, 15))
