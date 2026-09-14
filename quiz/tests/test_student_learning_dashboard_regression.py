from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class StudentLearningDashboardRegressionTests(TestCase):
    def test_dashboard_does_not_reference_removed_exam_primary_category(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="learning-dashboard-user",
            password="pass",
        )
        self.client.login(username="learning-dashboard-user", password="pass")

        response = self.client.get(reverse("quiz:student_dashboard"))

        self.assertEqual(response.status_code, 200)
