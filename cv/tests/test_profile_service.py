from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import UserProfile
from cv.services.profile import account_contact_defaults, get_or_create_career_profile


class CareerProfileServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="profile-user",
            email="profile@example.com",
            password="test-password-123",
            first_name="Binay",
            last_name="Thapa",
        )
        self.account_profile = self.user.profile

    def test_account_contact_defaults_reuse_user_and_account_profile(self):
        self.account_profile.phone = "+919876543210"
        self.account_profile.address = "Bengaluru"
        self.account_profile.save(update_fields=["phone", "address", "updated_at"])

        defaults = account_contact_defaults(self.user)

        self.assertEqual(defaults["first_name"], "Binay")
        self.assertEqual(defaults["last_name"], "Thapa")
        self.assertEqual(defaults["email"], "profile@example.com")
        self.assertEqual(defaults["phone"], self.account_profile.phone)
        self.assertEqual(defaults["location"], "Bengaluru")

    def test_profile_service_is_independent_of_learning(self):
        profile = get_or_create_career_profile(self.user)
        self.assertEqual(profile.user_id, self.user.id)
        self.assertFalse(hasattr(profile, "course"))
        self.assertFalse(hasattr(profile, "exam"))
