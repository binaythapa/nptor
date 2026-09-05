from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class StudentNavigationDestinationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="navigation-user",
            password="test-pass-123",
        )
        self.client.force_login(self.user)

    def test_dashboard_and_my_learning_are_distinct_pages(self):
        dashboard_response = self.client.get(reverse("quiz:student_dashboard"))
        learning_response = self.client.get(reverse("quiz:learning_hub"))

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertEqual(learning_response.status_code, 200)
        self.assertContains(dashboard_response, "Student Dashboard")
        self.assertContains(learning_response, "My Learning")
        self.assertNotContains(dashboard_response, "Everything you have purchased, subscribed to, been assigned, or saved for later")

    def test_sidebar_uses_clear_certification_and_government_labels(self):
        response = self.client.get(reverse("quiz:student_dashboard"))

        self.assertContains(response, "Certifications")
        self.assertContains(response, "Government Exams")
        self.assertNotContains(response, ">Explore Exams<")
