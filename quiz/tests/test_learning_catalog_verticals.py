from django.contrib.auth import get_user_model
from django.test import TestCase

from courses.models import Course
from quiz.models import Category, ContentVertical, Domain
from quiz.services.learning_catalog import build_learning_catalog


class LearningCatalogVerticalTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="catalog-vertical-user",
            password="test-pass-123",
        )
        self.cert_vertical = ContentVertical.objects.create(
            name="Professional Certification",
            code="professional-certification-test",
            vertical_type=ContentVertical.PROFESSIONAL_CERTIFICATION,
        )
        self.academic_vertical = ContentVertical.objects.create(
            name="Academic Exam",
            code="academic-exam-test",
            vertical_type=ContentVertical.ACADEMIC_EXAM,
        )
        self.cert_domain = Domain.objects.create(
            name="Certification Domain",
            slug="certification-domain",
            content_vertical=self.cert_vertical,
        )
        self.academic_domain = Domain.objects.create(
            name="Academic Domain",
            slug="academic-domain",
            content_vertical=self.academic_vertical,
        )
        self.cert_category = Category.objects.create(
            name="Certification Category",
            slug="certification-category",
            domain=self.cert_domain,
        )
        self.academic_category = Category.objects.create(
            name="Academic Category",
            slug="academic-category",
            domain=self.academic_domain,
        )
        Course.objects.create(
            title="Certification Course",
            description="Certification content",
            category=self.cert_category,
            level="beginner",
            is_public=True,
            is_published=True,
            approval_status=Course.APPROVAL_APPROVED,
        )
        Course.objects.create(
            title="Academic Course",
            description="Academic content",
            category=self.academic_category,
            level="beginner",
            is_public=True,
            is_published=True,
            approval_status=Course.APPROVAL_APPROVED,
        )

    def test_academic_catalog_excludes_certification_content(self):
        catalog = build_learning_catalog(
            user=self.user,
            catalog_vertical=ContentVertical.ACADEMIC_EXAM,
        )
        titles = {item["resource"].title for item in catalog["resources"]}
        self.assertEqual(titles, {"Academic Course"})

    def test_certification_catalog_excludes_academic_content(self):
        catalog = build_learning_catalog(
            user=self.user,
            catalog_vertical=ContentVertical.PROFESSIONAL_CERTIFICATION,
        )
        titles = {item["resource"].title for item in catalog["resources"]}
        self.assertEqual(titles, {"Certification Course"})

    def test_catalog_does_not_expose_exams_as_resources(self):
        catalog = build_learning_catalog(user=self.user)
        self.assertNotIn("exam", {item["type"] for item in catalog["resources"]})
