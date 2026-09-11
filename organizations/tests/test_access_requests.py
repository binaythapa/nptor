from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from organizations.models.organization import Organization
from organizations.models.membership import OrganizationMember
from organizations.models.role import OrganizationRole
from organizations.models.access_request import OrganizationAccessRequest
from organizations.services.access_requests import (
    approve_access_request,
    reject_access_request,
    submit_access_request,
)


class OrganizationAccessRequestServiceTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="requester", email="requester@example.com", password="test-password")
        self.admin = User.objects.create_user(username="reviewer", email="reviewer@example.com", password="test-password", is_superuser=True, is_staff=True)
        self.organization = Organization.objects.create(name="Demo School", slug="demo-school", created_by=self.admin)

    def test_submit_creates_pending_request(self):
        request = submit_access_request(self.user, self.organization, "ORGANIZATION_ACCESS", OrganizationRole.STUDENT, "Need access")
        self.assertEqual(request.status, OrganizationAccessRequest.STATUS_PENDING)
        self.assertFalse(OrganizationMember.objects.filter(user=self.user, organization=self.organization).exists())

    def test_duplicate_pending_request_is_reused(self):
        first = submit_access_request(self.user, self.organization)
        second = submit_access_request(self.user, self.organization)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(OrganizationAccessRequest.objects.filter(user=self.user, organization=self.organization, status=OrganizationAccessRequest.STATUS_PENDING).count(), 1)

    def test_approve_activates_membership_idempotently(self):
        request = submit_access_request(self.user, self.organization, requested_role=OrganizationRole.STUDENT)
        approved = approve_access_request(request, self.admin)
        self.assertEqual(approved.status, OrganizationAccessRequest.STATUS_APPROVED)
        member = OrganizationMember.objects.get(user=self.user, organization=self.organization)
        self.assertEqual(member.role, OrganizationRole.STUDENT)
        self.assertTrue(member.is_active)
        self.assertEqual(approve_access_request(request, self.admin).pk, request.pk)
        self.assertEqual(OrganizationMember.objects.filter(user=self.user, organization=self.organization).count(), 1)

    def test_reject_does_not_create_membership(self):
        request = submit_access_request(self.user, self.organization)
        reject_access_request(request, self.admin, "Not eligible")
        request.refresh_from_db()
        self.assertEqual(request.status, OrganizationAccessRequest.STATUS_REJECTED)
        self.assertFalse(OrganizationMember.objects.filter(user=self.user, organization=self.organization).exists())


class OrganizationAccessRequestViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="requester", email="requester@example.com", password="test-password")
        self.organization = Organization.objects.create(name="Demo School", slug="demo-school", created_by=self.user)

    def test_anonymous_user_is_redirected(self):
        response = self.client.get(reverse("organizations_public:request_access"))
        self.assertEqual(response.status_code, 302)

    def test_authenticated_user_can_submit(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("organizations_public:request_access"), {"organization": self.organization.pk, "service": "ORGANIZATION_ACCESS", "requested_role": OrganizationRole.STUDENT, "reason": "Please approve"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(OrganizationAccessRequest.objects.filter(user=self.user, organization=self.organization, status=OrganizationAccessRequest.STATUS_PENDING).exists())
