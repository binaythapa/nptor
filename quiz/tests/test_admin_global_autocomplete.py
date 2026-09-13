from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from courses.models import Course
from organizations.models import Organization
from quiz.models import Category, Exam, ExamTrack


User = get_user_model()


class AdminGlobalAutocompleteTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="autocomplete-admin",
            email="admin@example.com",
            password="password",
        )
        self.client.force_login(self.admin)

        User.objects.create_user(username="test-user", email="test@example.com")
        User.objects.create_user(username="alpha-user", email="alpha@example.com")
        Course.objects.create(
            title="Test Python",
            description="Test",
            level="beginner",
            created_by=self.admin,
        )
        Course.objects.create(
            title="Accounting Basics",
            description="Accounting",
            level="beginner",
            created_by=self.admin,
        )
        ExamTrack.objects.create(title="Test Track", slug="test-track")
        ExamTrack.objects.create(title="Accounting Track", slug="accounting-track")
        Exam.objects.create(title="Test Exam", duration_seconds=600, created_by=self.admin)
        Exam.objects.create(title="Accounting Exam", duration_seconds=600, created_by=self.admin)

        self.organization = Organization.objects.create(
            name="Test Organization",
            slug="test-organization",
            org_type=Organization.TYPE_SCHOOL,
        )
        self.other_organization = Organization.objects.create(
            name="Other Organization",
            slug="other-organization",
            org_type=Organization.TYPE_SCHOOL,
        )
        python = Category.objects.create(name="Python", slug="python")
        Category.objects.create(
            name="Django",
            slug="django",
            parent=python,
        )
        Category.objects.create(
            name="Python Testing",
            slug="python-testing",
            organization=self.organization,
        )
        Category.objects.create(
            name="Python Internal",
            slug="python-internal",
            organization=self.other_organization,
        )

    def search(self, scope, query, **params):
        params.update({"scope": scope, "q": query})
        return self.client.get(reverse("quiz:admin_autocomplete"), params)

    def test_users_are_prefix_matched(self):
        response = self.search("users", "test")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([r["label"] for r in response.json()["results"]], ["test-user"])

    def test_courses_are_prefix_matched(self):
        response = self.search("courses", "test")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([r["label"] for r in response.json()["results"]], ["Test Python"])

    def test_tracks_are_prefix_matched(self):
        response = self.search("tracks", "test")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([r["label"] for r in response.json()["results"]], ["Test Track"])

    def test_exams_are_prefix_matched(self):
        response = self.search("exams", "test")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([r["label"] for r in response.json()["results"]], ["Test Exam"])

    def test_categories_are_prefix_matched_and_include_hierarchy(self):
        response = self.search("categories", "djan")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([r["label"] for r in response.json()["results"]], ["Python → Django"])
        self.assertEqual([r["subtitle"] for r in response.json()["results"]], [""])

    def test_categories_are_scoped_to_selected_organization(self):
        response = self.search(
            "categories",
            "python",
            organization=self.organization.id,
        )
        self.assertEqual(response.status_code, 200)
        labels = [r["label"] for r in response.json()["results"]]
        self.assertIn("Python", labels)
        self.assertIn("Python Testing", labels)
        self.assertNotIn("Python Internal", labels)

    def test_unknown_scope_returns_no_results(self):
        response = self.search("unknown", "test")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"], [])

    def test_results_are_capped(self):
        for index in range(25):
            User.objects.create_user(username=f"tester-{index:02d}")
        response = self.search("users", "tester")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 20)
