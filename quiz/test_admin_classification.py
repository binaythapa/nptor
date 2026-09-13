from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from quiz.models import Category, ContentVertical, Domain


class GlobalClassificationAdminTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="staff", password="test-pass", is_staff=True)
        self.client.force_login(self.user)
        self.vertical = ContentVertical.objects.create(
            name="Professional Certification",
            code="professional-certification",
            vertical_type=ContentVertical.PROFESSIONAL_CERTIFICATION,
        )

    def test_global_classification_routes_require_staff(self):
        self.client.logout()
        for name in ("quiz:admin_domain_list", "quiz:admin_category_list"):
            response = self.client.get(reverse(name))
            self.assertIn(response.status_code, (302, 403))

    def test_global_domain_create_and_update(self):
        response = self.client.post(
            reverse("quiz:admin_domain_create"),
            {"content_vertical": self.vertical.pk, "name": "Data Engineering", "slug": "Data Engineering", "is_active": "on"},
        )
        self.assertRedirects(response, reverse("quiz:admin_domain_list"))
        domain = Domain.objects.get(slug="data-engineering", organization__isnull=True)
        self.assertEqual(domain.content_vertical, self.vertical)

        response = self.client.post(
            reverse("quiz:admin_domain_update", args=[domain.pk]),
            {"content_vertical": self.vertical.pk, "name": "Data Platforms", "slug": "data-platforms", "is_active": "on"},
        )
        self.assertRedirects(response, reverse("quiz:admin_domain_list"))
        domain.refresh_from_db()
        self.assertEqual(domain.name, "Data Platforms")

    def test_global_category_create_enforces_global_ownership(self):
        domain = Domain.objects.create(name="Cloud", slug="cloud", content_vertical=self.vertical)
        response = self.client.post(
            reverse("quiz:admin_category_create"),
            {"domain": domain.pk, "name": "Azure", "slug": "azure", "parent": "", "is_active": "on"},
        )
        self.assertRedirects(response, reverse("quiz:admin_category_list"))
        category = Category.objects.get(slug="azure", organization__isnull=True)
        self.assertEqual(category.domain, domain)

    def test_domain_with_categories_cannot_be_deleted(self):
        domain = Domain.objects.create(name="Cloud", slug="cloud", content_vertical=self.vertical)
        Category.objects.create(name="Azure", slug="azure", domain=domain)
        response = self.client.post(reverse("quiz:admin_domain_delete", args=[domain.pk]))
        self.assertRedirects(response, reverse("quiz:admin_domain_list"))
        self.assertTrue(Domain.objects.filter(pk=domain.pk).exists())

    def test_sidebar_exposes_global_classification_links(self):
        response = self.client.get(reverse("quiz:admin_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("quiz:admin_domain_list"))
        self.assertContains(response, reverse("quiz:admin_category_list"))
