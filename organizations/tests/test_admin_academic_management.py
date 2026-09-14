from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from organizations.models import AcademicYear, ClassSection, Organization, OrganizationClass, OrganizationMember
from organizations.models.role import OrganizationRole


class AdminAcademicManagementTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="owner", password="pass")
        self.org = Organization.objects.create(name="School", slug="school")
        OrganizationMember.objects.create(user=self.user, organization=self.org, role=OrganizationRole.OWNER, is_active=True)
        self.client.login(username="owner", password="pass")
        self.year = AcademicYear.objects.create(organization=self.org, name="2026-2027", start_date="2026-04-01", end_date="2027-03-31")
        self.klass = OrganizationClass.objects.create(organization=self.org, name="Grade 10")
        self.section = ClassSection.objects.create(organization=self.org, academic_year=self.year, class_group=self.klass, name="A")

    def test_academic_dashboard_exposes_master_data(self):
        response = self.client.get(reverse("organizations_admin:academic", kwargs={"slug": self.org.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2026-2027")
        self.assertContains(response, "Grade 10")
        self.assertContains(response, "Section A")

    def test_admin_can_edit_academic_year(self):
        response = self.client.post(reverse("organizations_admin:academic_year_edit", kwargs={"slug": self.org.slug, "year_id": self.year.id}), {"name": "2027-2028", "start_date": "2027-04-01", "end_date": "2028-03-31", "is_current": "on"})
        self.assertRedirects(response, reverse("organizations_admin:academic", kwargs={"slug": self.org.slug}))
        self.year.refresh_from_db()
        self.assertEqual(self.year.name, "2027-2028")

    def test_admin_can_deactivate_class(self):
        response = self.client.post(reverse("organizations_admin:academic_class_toggle", kwargs={"slug": self.org.slug, "class_id": self.klass.id}))
        self.assertRedirects(response, reverse("organizations_admin:academic", kwargs={"slug": self.org.slug}))
        self.klass.refresh_from_db()
        self.assertFalse(self.klass.is_active)

    def test_admin_can_edit_and_deactivate_section(self):
        response = self.client.post(reverse("organizations_admin:academic_section_edit", kwargs={"slug": self.org.slug, "section_id": self.section.id}), {"academic_year": self.year.id, "class_group": self.klass.id, "name": "B", "capacity": "40"})
        self.assertRedirects(response, reverse("organizations_admin:academic", kwargs={"slug": self.org.slug}))
        self.section.refresh_from_db()
        self.assertEqual(self.section.name, "B")
        response = self.client.post(reverse("organizations_admin:academic_section_toggle", kwargs={"slug": self.org.slug, "section_id": self.section.id}))
        self.assertRedirects(response, reverse("organizations_admin:academic", kwargs={"slug": self.org.slug}))
        self.section.refresh_from_db()
        self.assertFalse(self.section.is_active)
