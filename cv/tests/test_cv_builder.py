from django.contrib.auth import get_user_model
from django.test import TestCase

from cv.models import CareerExperience
from cv.models_cv import CV
from cv.models_template import CVTemplate
from cv.models_version import CVVersion
from cv.services.cv_builder import (
    build_cv_payload,
    create_cv,
    create_cv_version,
    duplicate_cv,
)


class CVBuilderTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="cv-builder-user",
            email="cv-builder@example.com",
        )
        self.template = CVTemplate.objects.create(
            slug="test-template",
            name="Test Template",
        )

    def test_create_cv_requires_no_course_or_exam(self):
        cv = create_cv(self.user, "Software Engineer CV", self.template)
        self.assertEqual(cv.owner_id, self.user.id)
        self.assertEqual(cv.title, "Software Engineer CV")

    def test_builder_payload_uses_selected_profile_records(self):
        cv = create_cv(self.user, "Data Engineer CV", self.template)
        profile = cv.profile
        experience = CareerExperience.objects.create(
            profile=profile,
            job_title="Data Engineer",
            employer="Example Ltd",
        )
        cv.selected_sections = {"experiences": [experience.id]}
        cv.save(update_fields=["selected_sections", "updated_at"])

        payload = build_cv_payload(cv)

        self.assertEqual(payload["contact"]["email"], self.user.email)
        self.assertEqual(payload["experiences"][0]["job_title"], "Data Engineer")

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
