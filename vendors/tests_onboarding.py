from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from vendors.models import VendorBankDetails, VendorProfile

User = get_user_model()


class VendorOnboardingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="applicant", email="applicant@example.com", password="pass")
        self.staff_user = User.objects.create_user(username="staff", email="staff@example.com", password="pass", is_staff=True)
        self.other_user = User.objects.create_user(username="other", email="other@example.com", password="pass")

    def test_anonymous_user_redirected_to_login(self):
        response = self.client.get(reverse("vendors:onboarding"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_authenticated_user_can_submit_onboarding(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("vendors:onboarding"),
            data={
                "store_name": "Lalitpur Crafts",
                "business_email": "info@lalitpurcrafts.com",
                "business_phone": "+977-9801234567",
                "pan_vat_number": "600123456",
                "business_registration_number": "REG-12345",
                "bank_name": "Nabil Bank Ltd",
                "bank_account_name": "Lalitpur Crafts Pvt Ltd",
                "bank_account_number": "001002003004005",
                "bank_branch": "Jawalakhel",
                "is_cod_enabled": True,
            },
        )
        self.assertRedirects(response, reverse("vendors:dashboard"))

        # Verify VendorProfile created with pending status
        profile = VendorProfile.objects.get(user=self.user)
        self.assertEqual(profile.store_name, "Lalitpur Crafts")
        self.assertEqual(profile.slug, "lalitpur-crafts")
        self.assertEqual(profile.status, VendorProfile.STATUS_PENDING)
        self.assertTrue(profile.is_cod_enabled)

        # Verify Bank details created and masked
        bank = VendorBankDetails.objects.get(vendor=profile)
        self.assertEqual(bank.bank_name, "Nabil Bank Ltd")
        self.assertTrue(bank.masked_account_number.endswith("4005"))
        self.assertNotIn("001002003", bank.masked_account_number)
        # Verify encryption at rest: raw database column contains ciphertext, not plaintext
        self.assertNotEqual(bank.encrypted_account_number, "001002003004005")
        self.assertEqual(bank.bank_account_number, "001002003004005")

    def test_staff_can_view_and_approve_vendor_application(self):
        profile = VendorProfile.objects.create(
            user=self.user,
            store_name="Bhaktapur Pottery",
            slug="bhaktapur-pottery",
            business_email="contact@pottery.com",
            business_phone="+977-9812345678",
            status=VendorProfile.STATUS_PENDING,
        )

        # Non-staff denied access
        self.client.force_login(self.other_user)
        res_denied = self.client.get(reverse("vendors:admin_queue"))
        self.assertEqual(res_denied.status_code, 302)

        # Staff can view queue
        self.client.force_login(self.staff_user)
        res_staff = self.client.get(reverse("vendors:admin_queue"))
        self.assertEqual(res_staff.status_code, 200)
        self.assertContains(res_staff, "Bhaktapur Pottery")

        # Staff approves vendor
        res_action = self.client.post(
            reverse("vendors:admin_action", args=[profile.pk]),
            data={"action": "approve"},
        )
        self.assertRedirects(res_action, reverse("vendors:admin_queue"))

        profile.refresh_from_db()
        self.assertEqual(profile.status, VendorProfile.STATUS_ACTIVE)
        self.assertEqual(profile.approved_by, self.staff_user)
        self.assertIsNotNone(profile.approved_at)
