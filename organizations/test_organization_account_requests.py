from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from organizations.models.organization import Organization
from organizations.models.membership import OrganizationMember
from organizations.models.account_request import OrganizationAccountRequest


User = get_user_model()


class OrganizationAccountRequestWorkflowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="requester",
            email="requester@example.com",
            password="test-password",
        )
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="test-password",
            is_staff=True,
            is_superuser=True,
        )

    def request_payload(self, **overrides):
        payload = {
            "organization_name": "Acme Learning Institute",
            "org_type": Organization.TYPE_INSTITUTE,
            "website": "https://example.com",
            "contact_email": "admin@example.com",
            "contact_phone": "+977-9800000000",
            "address": "Kathmandu",
            "city": "Kathmandu",
            "country": "Nepal",
            "description": "Professional training institute.",
            "reason": "We need an organization workspace for our learners.",
        }
        payload.update(overrides)
        return payload

    def test_user_can_submit_one_pending_organization_account_request(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("accounts:organization-account-request"),
            self.request_payload(),
        )
        self.assertEqual(response.status_code, 302)
        request = OrganizationAccountRequest.objects.get(user=self.user)
        self.assertEqual(request.status, OrganizationAccountRequest.STATUS_PENDING)
        self.assertEqual(request.organization_name, "Acme Learning Institute")
        self.assertFalse(Organization.objects.filter(name="Acme Learning Institute").exists())
        self.assertFalse(OrganizationMember.objects.filter(user=self.user).exists())

    def test_pending_request_is_visible_on_profile(self):
        OrganizationAccountRequest.objects.create(
            user=self.user,
            organization_name="Acme Learning Institute",
            org_type=Organization.TYPE_INSTITUTE,
            contact_email="admin@example.com",
            reason="Need an organization workspace.",
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse("quiz:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Organization Account Request")
        self.assertContains(response, "Pending Review")
        self.assertNotContains(response, "Request Organization Account")

    def test_admin_request_detail_uses_scannable_organization_summary(self):
        request = OrganizationAccountRequest.objects.create(
            user=self.user,
            organization_name="Acme Learning Institute",
            org_type=Organization.TYPE_INSTITUTE,
            website="https://example.com",
            contact_email="admin@example.com",
            contact_phone="+977-9800000000",
            address="Kathmandu",
            city="Kathmandu",
            country="Nepal",
            description="Professional training institute.",
            reason="Need an organization workspace.",
        )
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse(
                "accounts:organization-account-request-detail",
                kwargs={"pk": request.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "request-organization-summary")
        self.assertContains(response, "request-status-badge")
        self.assertContains(response, "request-contact-grid")
        self.assertContains(response, 'href="https://example.com"')
        self.assertContains(response, "Visit website")
        self.assertContains(response, "Contact & Location")
        self.assertContains(response, "Request details")

    def test_admin_approval_creates_active_organization_and_owner_membership(self):
        request = OrganizationAccountRequest.objects.create(
            user=self.user,
            organization_name="Acme Learning Institute",
            org_type=Organization.TYPE_INSTITUTE,
            website="https://example.com",
            contact_email="admin@example.com",
            contact_phone="+977-9800000000",
            address="Kathmandu",
            city="Kathmandu",
            country="Nepal",
            description="Professional training institute.",
            reason="Need an organization workspace.",
        )
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("accounts:organization-account-request-approve", kwargs={"pk": request.pk}),
            {"review_notes": "Approved."},
        )
        self.assertEqual(response.status_code, 302)
        request.refresh_from_db()
        self.assertEqual(request.status, OrganizationAccountRequest.STATUS_APPROVED)
        self.assertEqual(request.reviewed_by, self.admin)
        self.assertIsNotNone(request.reviewed_at)
        organization = Organization.objects.get(name="Acme Learning Institute")
        self.assertTrue(organization.is_active)
        self.assertEqual(organization.org_type, Organization.TYPE_INSTITUTE)
        membership = OrganizationMember.objects.get(user=self.user, organization=organization)
        self.assertEqual(membership.role, OrganizationMember.ROLE_ORG_OWNER)
        self.assertTrue(membership.is_active)

    def test_admin_rejection_does_not_create_organization_membership(self):
        request = OrganizationAccountRequest.objects.create(
            user=self.user,
            organization_name="Acme Learning Institute",
            org_type=Organization.TYPE_INSTITUTE,
            contact_email="admin@example.com",
            reason="Need an organization workspace.",
        )
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("accounts:organization-account-request-reject", kwargs={"pk": request.pk}),
            {"review_notes": "Please provide more information."},
        )
        self.assertEqual(response.status_code, 302)
        request.refresh_from_db()
        self.assertEqual(request.status, OrganizationAccountRequest.STATUS_REJECTED)
        self.assertFalse(OrganizationMember.objects.filter(user=self.user).exists())

    def test_non_admin_cannot_approve_request(self):
        request = OrganizationAccountRequest.objects.create(
            user=self.user,
            organization_name="Acme Learning Institute",
            org_type=Organization.TYPE_INSTITUTE,
            contact_email="admin@example.com",
        )
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("accounts:organization-account-request-approve", kwargs={"pk": request.pk}),
        )
        self.assertIn(response.status_code, (302, 403))
        request.refresh_from_db()
        self.assertEqual(request.status, OrganizationAccountRequest.STATUS_PENDING)
