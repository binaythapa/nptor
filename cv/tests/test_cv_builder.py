from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cv.models import CareerExperience
from cv.models_cv import CV
from cv.models_template import CVTemplate
from cv.models_version import CVVersion
from cv.services.cv_builder import build_cv_payload, create_cv, create_cv_version, duplicate_cv
from cv.services.documents.renderer import build_cv_render_context


class CVBuilderTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="cv-builder-user", email="cv-builder@example.com")
        self.template = CVTemplate.objects.create(slug="test-template", name="Test Template")

    def test_create_cv_requires_no_course_or_exam(self):
        cv = create_cv(self.user, "Software Engineer CV", self.template)
        self.assertEqual(cv.owner_id, self.user.id)
        self.assertEqual(cv.title, "Software Engineer CV")

    def test_builder_payload_uses_selected_profile_records(self):
        cv = create_cv(self.user, "Data Engineer CV", self.template)
        experience = CareerExperience.objects.create(profile=cv.profile, job_title="Data Engineer", employer="Example Ltd")
        cv.selected_sections = {"experiences": [experience.id]}
        cv.save(update_fields=["selected_sections", "updated_at"])
        payload = build_cv_payload(cv)
        self.assertEqual(payload["contact"]["email"], self.user.email)
        self.assertEqual(payload["experiences"][0]["job_title"], "Data Engineer")

    def test_empty_section_selection_excludes_all_records(self):
        cv = create_cv(self.user, "Data Engineer CV", self.template)
        CareerExperience.objects.create(profile=cv.profile, job_title="Data Engineer", employer="Example Ltd")
        cv.selected_sections = {"experiences": []}
        cv.save(update_fields=["selected_sections", "updated_at"])
        self.assertEqual(build_cv_payload(cv)["experiences"], [])

    def test_selected_record_order_is_preserved_in_payload(self):
        cv = create_cv(self.user, "Ordered CV", self.template)
        first = CareerExperience.objects.create(profile=cv.profile, job_title="First Role", employer="First Co")
        second = CareerExperience.objects.create(profile=cv.profile, job_title="Second Role", employer="Second Co")
        cv.selected_sections = {"experiences": [second.pk, first.pk]}
        cv.save(update_fields=["selected_sections", "updated_at"])

        payload = build_cv_payload(cv)

        self.assertEqual([item["id"] for item in payload["experiences"]], [second.pk, first.pk])

    def test_builder_saves_reordered_records(self):
        cv = create_cv(self.user, "Ordered CV", self.template)
        first = CareerExperience.objects.create(profile=cv.profile, job_title="First Role", employer="First Co")
        second = CareerExperience.objects.create(profile=cv.profile, job_title="Second Role", employer="Second Co")
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("cv:cv_builder", kwargs={"pk": cv.pk}),
            {
                "title": cv.title,
                "template": self.template.pk,
                "status": CV.STATUS_DRAFT,
                "professional_title": "",
                "summary": "",
                "linkedin_url": "",
                "portfolio_url": "",
                "experiences": [str(second.pk), str(first.pk)],
                "educations": [],
                "skills": [],
                "certifications": [],
                "projects": [],
                "achievements": [],
            },
        )

        self.assertRedirects(response, reverse("cv:cv_builder", kwargs={"pk": cv.pk}))
        cv.refresh_from_db()
        self.assertEqual(cv.selected_sections["experiences"], [second.pk, first.pk])
        self.assertEqual([item["id"] for item in build_cv_payload(cv)["experiences"]], [second.pk, first.pk])

    def test_duplicate_cv_is_independent(self):
        original = create_cv(self.user, "Original", self.template)
        copy = duplicate_cv(original, "Tailored Version")
        self.assertNotEqual(original.pk, copy.pk)
        self.assertEqual(copy.owner_id, self.user.id)
        self.assertEqual(copy.title, "Tailored Version")
        self.assertEqual(copy.selected_sections, original.selected_sections)
        self.assertEqual(copy.overrides, original.overrides)

    def test_version_is_a_snapshot(self):
        cv = create_cv(self.user, "Versioned CV", self.template)
        version = create_cv_version(cv)
        original_title = version.snapshot["title"]
        cv.title = "Changed Later"
        cv.save(update_fields=["title", "updated_at"])
        version.refresh_from_db()
        self.assertEqual(version.snapshot["title"], original_title)
        self.assertIsInstance(version, CVVersion)

    def test_versions_increment(self):
        cv = create_cv(self.user, "Versioned CV", self.template)
        first = create_cv_version(cv)
        second = create_cv_version(cv)
        self.assertEqual(first.version_number, 1)
        self.assertEqual(second.version_number, 2)

    def test_builder_renders_profile_sections_and_actions(self):
        cv = create_cv(self.user, "Builder CV", self.template)
        self.user.career_profile.professional_title = "Data Engineer"
        self.user.career_profile.summary = "Experienced data engineer."
        self.user.career_profile.save()
        self.client.force_login(self.user)
        response = self.client.get(reverse("cv:cv_builder", kwargs={"pk": cv.pk}))
        self.assertEqual(response.status_code, 200)
        for text in ("Professional summary", "Work experience", "Education", "Skills", "Certifications", "Projects", "Achievements", "Save resume", "Open full preview"):
            self.assertContains(response, text)

    def test_builder_saves_selection_and_overrides(self):
        cv = create_cv(self.user, "Builder CV", self.template)
        experience = CareerExperience.objects.create(profile=cv.profile, job_title="Data Engineer", employer="Example Ltd")
        self.client.force_login(self.user)
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
                "experiences": [str(experience.pk)],
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
        self.assertEqual(cv.selected_sections["experiences"], [experience.pk])
        self.assertEqual(cv.selected_sections["educations"], [])

    def test_builder_rejects_another_users_cv(self):
        other = get_user_model().objects.create_user(username="other-builder", email="other-builder@example.com")
        other_cv = create_cv(other, "Other CV", self.template)
        self.client.force_login(self.user)
        response = self.client.get(reverse("cv:cv_builder", kwargs={"pk": other_cv.pk}))
        self.assertEqual(response.status_code, 404)

    def test_render_context_is_canonical_and_omits_empty_sections(self):
        cv = create_cv(self.user, "Preview CV", self.template)
        cv.profile.professional_title = "Data Engineer"
        cv.profile.summary = "Builds reliable data platforms."
        cv.profile.save(update_fields=["professional_title", "summary", "updated_at"])
        CareerExperience.objects.create(profile=cv.profile, job_title="Data Engineer", employer="Example Ltd")

        context = build_cv_render_context(cv)

        self.assertEqual(context["payload"]["title"], "Preview CV")
        self.assertEqual(context["config"]["layout"], "single_column")
        self.assertEqual([section["key"] for section in context["sections"]], ["summary", "experiences"])
        self.assertEqual(context["sections"][0]["heading"], "Professional Summary")
        self.assertEqual(context["sections"][1]["heading"], "Experience")

    def test_preview_uses_render_context_and_template_configuration(self):
        self.template.config = {
            "layout": "sidebar",
            "header_style": "centered",
            "accent_color": "#123456",
        }
        self.template.save(update_fields=["config"])
        cv = create_cv(self.user, "Preview CV", self.template)
        cv.profile.professional_title = "Data Engineer"
        cv.profile.summary = "Experienced data engineer."
        cv.profile.save(update_fields=["professional_title", "summary", "updated_at"])
        self.client.force_login(self.user)

        response = self.client.get(reverse("cv:cv_preview", kwargs={"pk": cv.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Preview CV")
        self.assertContains(response, "Professional Summary")
        self.assertContains(response, "data-template-layout=\"sidebar\"")
        self.assertContains(response, "#123456")

    def test_preview_rejects_another_users_cv(self):
        other = get_user_model().objects.create_user(username="other-preview", email="other-preview@example.com")
        other_cv = create_cv(other, "Other CV", self.template)
        self.client.force_login(self.user)
        response = self.client.get(reverse("cv:cv_preview", kwargs={"pk": other_cv.pk}))
        self.assertEqual(response.status_code, 404)
