from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from courses.models import Course
from organizations.models import Organization, OrganizationDomain, OrganizationMember, OrganizationPortalConfig
from organizations.models.assignment import ResourceAssignment
from organizations.models.role import OrganizationRole
from organizations.services.assignments import assign_resource
from organizations.services.domains import OrganizationDomainService
from organizations.services.portal import OrganizationPortalService
from organizations.services.tenant import TenantResolver
from quiz.models import Domain


User = get_user_model()


class OrganizationPortalTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Portal School",
            slug="portal-school",
            org_type=Organization.TYPE_SCHOOL,
            is_active=True,
        )
        self.other_org = Organization.objects.create(
            name="Other School",
            slug="other-school",
            org_type=Organization.TYPE_SCHOOL,
            is_active=True,
        )
        self.admin = User.objects.create_user(username="portal-admin", password="password")
        self.student = User.objects.create_user(username="portal-student", password="password")
        self.other_student = User.objects.create_user(username="other-student", password="password")
        OrganizationMember.objects.create(user=self.admin, organization=self.org, role=OrganizationRole.ORG_ADMIN)
        OrganizationMember.objects.create(user=self.student, organization=self.org, role=OrganizationRole.STUDENT)
        OrganizationMember.objects.create(user=self.other_student, organization=self.other_org, role=OrganizationRole.STUDENT)
        self.client = Client()

    def test_new_organization_gets_portal_defaults(self):
        self.assertEqual(self.org.profile.display_name, "Portal School")
        self.assertEqual(self.org.portal_config.hero_title, "Portal School")
        self.assertFalse(self.org.portal_config.is_published)

    def test_unpublished_portal_is_not_public(self):
        self.assertFalse(OrganizationPortalService.is_published(self.org))
        response = self.client.get("/org/portal-school/")
        self.assertEqual(response.status_code, 404)

    def test_published_portal_shows_only_public_approved_courses(self):
        OrganizationPortalConfig.objects.filter(organization=self.org).update(is_published=True)
        Course.objects.create(
            title="Visible Course", description="Public course", level="beginner",
            owner_type=Course.OWNER_ORGANIZATION, organization=self.org,
            is_public=True, is_published=True, approval_status=Course.APPROVAL_APPROVED,
            created_by=self.admin,
        )
        Course.objects.create(
            title="Draft Course", description="Not public yet", level="beginner",
            owner_type=Course.OWNER_ORGANIZATION, organization=self.org,
            is_public=True, is_published=True, approval_status=Course.APPROVAL_DRAFT,
            created_by=self.admin,
        )
        response = self.client.get("/org/portal-school/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Visible Course")
        self.assertNotContains(response, "Draft Course")

    def test_student_learning_is_scoped_to_current_organization(self):
        course = Course.objects.create(
            title="Assigned Course", description="Assigned course", level="beginner",
            owner_type=Course.OWNER_ORGANIZATION, organization=self.org, created_by=self.admin,
        )
        assign_resource(
            actor=self.admin, organization=self.org, student=self.student,
            resource_type=ResourceAssignment.RESOURCE_COURSE, resource_id=course.id,
        )
        self.client.force_login(self.student)
        response = self.client.get("/org/portal-school/learning/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Assigned Course")

    def test_student_from_other_organization_cannot_access_portal_learning(self):
        self.client.force_login(self.other_student)
        response = self.client.get("/org/portal-school/learning/")
        self.assertEqual(response.status_code, 403)


class TenantResolverTests(TestCase):
    def setUp(self):
        self.org_a = Organization.objects.create(name="Alpha", slug="alpha", org_type=Organization.TYPE_SCHOOL)
        self.org_b = Organization.objects.create(name="Beta", slug="beta", org_type=Organization.TYPE_SCHOOL)

    def test_organization_domain_reverse_accessor_does_not_clash_with_quiz_domain(self):
        organization_domain = OrganizationDomain.objects.create(
            organization=self.org_a,
            domain="learn.example.com",
            is_verified=True,
        )
        quiz_domain = Domain.objects.create(
            organization=self.org_a,
            name="Snowflake",
            slug="snowflake",
        )

        self.assertEqual(list(self.org_a.organization_domains.all()), [organization_domain])
        self.assertEqual(list(self.org_a.domains.all()), [quiz_domain])

    def test_slug_resolution_returns_active_tenant(self):
        self.assertEqual(TenantResolver.by_slug("alpha"), self.org_a)
        self.assertIsNone(TenantResolver.by_slug("missing"))

    def test_inactive_tenant_is_not_resolved(self):
        self.org_a.is_active = False
        self.org_a.save(update_fields=["is_active"])
        self.assertIsNone(TenantResolver.by_slug("alpha"))

    def test_verified_host_resolution_is_case_insensitive(self):
        OrganizationDomain.objects.create(organization=self.org_a, domain="learn.example.com", is_verified=True)
        self.assertEqual(TenantResolver.by_host("LEARN.EXAMPLE.COM:443"), self.org_a)

    def test_unverified_host_does_not_resolve(self):
        OrganizationDomain.objects.create(organization=self.org_a, domain="pending.example.com", is_verified=False)
        self.assertIsNone(TenantResolver.by_host("pending.example.com"))

    @patch("organizations.services.domains.dns.resolver.resolve")
    def test_custom_domain_verification_requires_expected_txt_token(self, resolve):
        record = OrganizationDomainService.create(self.org_a, "learn.example.com")

        class Answer:
            strings = [record.verification_token.encode()]

        resolve.return_value = [Answer()]
        OrganizationDomainService.verify(record)
        record.refresh_from_db()
        self.assertTrue(record.is_verified)

    def test_custom_domain_cannot_be_primary_before_verification(self):
        record = OrganizationDomainService.create(self.org_a, "learn.example.com")
        with self.assertRaises(ValidationError):
            OrganizationDomainService.set_primary(record)

    def test_organization_cannot_have_two_primary_domains(self):
        OrganizationDomain.objects.create(
            organization=self.org_a,
            domain="primary.example.com",
            domain_type=OrganizationDomain.DOMAIN_TYPE_SUBDOMAIN,
            is_primary=True,
            is_verified=True,
        )

        with self.assertRaises(ValidationError):
            OrganizationDomain.objects.create(
                organization=self.org_a,
                domain="second-primary.example.com",
                domain_type=OrganizationDomain.DOMAIN_TYPE_SUBDOMAIN,
                is_primary=True,
                is_verified=True,
            )

    def test_set_primary_switches_to_another_verified_domain(self):
        current = OrganizationDomain.objects.create(
            organization=self.org_a,
            domain="current.example.com",
            domain_type=OrganizationDomain.DOMAIN_TYPE_SUBDOMAIN,
            is_primary=True,
            is_verified=True,
        )
        replacement = OrganizationDomain.objects.create(
            organization=self.org_a,
            domain="replacement.example.com",
            domain_type=OrganizationDomain.DOMAIN_TYPE_SUBDOMAIN,
            is_verified=True,
        )

        OrganizationDomainService.set_primary(replacement)

        current.refresh_from_db()
        replacement.refresh_from_db()
        self.assertFalse(current.is_primary)
        self.assertTrue(replacement.is_primary)

    def test_membership_does_not_cross_tenant(self):
        user = User.objects.create_user(username="tenant-user", password="password")
        OrganizationMember.objects.create(user=user, organization=self.org_a, role=OrganizationRole.STUDENT)
        self.assertFalse(OrganizationMember.objects.filter(user=user, organization=self.org_b, is_active=True).exists())
