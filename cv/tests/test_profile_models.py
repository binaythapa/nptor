from django.contrib.auth import get_user_model
from django.test import TestCase

from cv.models import (
    CareerAchievement,
    CareerCertification,
    CareerEducation,
    CareerExperience,
    CareerProfile,
    CareerProject,
    CareerSkill,
)
from cv.services.profile import get_or_create_career_profile


class CareerProfileTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="career-user",
            email="career@example.com",
            password="test-password-123",
            first_name="Career",
            last_name="User",
        )

    def test_profile_is_one_per_user(self):
        profile = get_or_create_career_profile(self.user)
        same_profile = get_or_create_career_profile(self.user)

        self.assertEqual(profile.pk, same_profile.pk)
        self.assertEqual(CareerProfile.objects.filter(user=self.user).count(), 1)

    def test_profile_does_not_require_learning_enrollment(self):
        profile = get_or_create_career_profile(self.user)
        self.assertIsNotNone(profile.pk)

    def test_child_records_are_owned_through_profile(self):
        profile = get_or_create_career_profile(self.user)

        experience = CareerExperience.objects.create(
            profile=profile,
            job_title="Data Engineer",
            employer="Example Ltd",
        )
        education = CareerEducation.objects.create(
            profile=profile,
            institution="Example University",
            qualification="BSc",
        )
        project = CareerProject.objects.create(
            profile=profile,
            name="Analytics Platform",
        )
        skill = CareerSkill.objects.create(profile=profile, name="Python")
        achievement = CareerAchievement.objects.create(
            profile=profile,
            title="Employee of the Year",
        )
        certification = CareerCertification.objects.create(
            profile=profile,
            name="Professional Certification",
        )

        self.assertEqual(experience.profile_id, profile.pk)
        self.assertEqual(education.profile_id, profile.pk)
        self.assertEqual(project.profile_id, profile.pk)
        self.assertEqual(skill.profile_id, profile.pk)
        self.assertEqual(achievement.profile_id, profile.pk)
        self.assertEqual(certification.profile_id, profile.pk)
