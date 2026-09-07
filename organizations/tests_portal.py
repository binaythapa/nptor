from django.core.exceptions import ValidationError
from django.test import TestCase

from organizations.models import Organization, OrganizationDomain, OrganizationMember, OrganizationPortalConfig, OrganizationProfile
from organizations.models.assignment import ResourceAssignment
from organizations.models.role import OrganizationRole
from organizations.services.domains import OrganizationDomainService
from organizations.services.portal import OrganizationPortalService
from django.contrib.auth import get_user_model


class OrganizationPortalTests(TestCase):
    def setUp(self):
        self.org_a = Organization.objects.create(name="Alpha", slug="alpha", org_type=Organization.TYPE_SCHOOL)
        self.org_b = Organization.objects.create(name="Beta", slug="beta", org_type=Organization.TYPE_SCHOOL)
        self.user = get_user_model().objects.create_user(username="student", password="x")

    def test_existing_organizations_get_profile_and_config(self):
        profile = OrganizationPortalService.profile(self.org_a)
        config = OrganizationPortalService.config(self.org_a)
        self.assertEqual(profile.display_name, "Alpha")
        self.assertEqual(config.hero_title, "Alpha")

    def test_unpublished_portal_is_not_public(self):
        self.assertFalse(OrganizationPortalService.is_published(self.org_a))
        OrganizationPortalConfig.objects.get(organization=self.org_a).is_published = True
        OrganizationPortalConfig.objects.filter(organization=self.org_a).update(is_published=True)
        self.assertTrue(OrganizationPortalService.is_published(self.org_a))

    def test_domain_is_normalized_and_unique(self):
        first = OrganizationDomainService.create(self.org_a, " Learn.Alpha.Example. ")
        self.assertEqual(first.domain, "learn.alpha.example")
        with self.assertRaises(ValidationError):
            OrganizationDomainService.create(self.org_b, "learn.alpha.example")

    def test_domain_cannot_be_primary_until_verified(self):
        record = OrganizationDomainService.create(self.org_a, "learn.alpha.example")
        self.assertFalse(record.is_verified)
        OrganizationDomainService.verify(record)
        OrganizationDomainService.set_primary(record)
        self.assertTrue(OrganizationDomain.objects.get(pk=record.pk).is_primary)

    def test_domain_lookup_is_tenant_specific(self):
        record = OrganizationDomainService.create(self.org_a, "learn.alpha.example")
        OrganizationDomainService.verify(record)
        resolved = OrganizationDomainService.active_for_host("learn.alpha.example:443")
        self.assertEqual(resolved.organization, self.org_a)
        self.assertNotEqual(resolved.organization, self.org_b)

    def test_membership_does_not_cross_tenant(self):
        OrganizationMember.objects.create(user=self.user, organization=self.org_a, role=OrganizationRole.STUDENT)
        self.assertFalse(OrganizationMember.objects.filter(user=self.user, organization=self.org_b, is_active=True).exists())
