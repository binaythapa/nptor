from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase


class StudentSidebarTests(TestCase):
    def test_student_sidebar_uses_clear_learning_and_government_labels(self):
        user = get_user_model().objects.create_user(
            username="sidebar-user",
            password="test-pass-123",
        )
        request = RequestFactory().get("/quiz/dashboard/student/")
        request.user = user

        html = render_to_string(
            "layouts/student/sidebar.html",
            {
                "request": request,
                "user": user,
                "is_from_course": False,
            },
        )

        self.assertIn("My Learning", html)
        self.assertIn("Government Exams", html)
        self.assertIn("My Content", html)
        self.assertNotIn('<span class="nav-label">Learning</span>', html)
