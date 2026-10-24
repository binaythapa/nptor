from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class HomePageRedesignTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="student_tester",
            email="student_tester@example.com",
            password="testpassword123",
        )

    def test_homepage_anonymous_access(self):
        """Anonymous first-time visitors should receive HTTP 200 with the service-first layout."""
        response = self.client.get(reverse("pages:home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/home.html")

    def test_homepage_authenticated_redirect(self):
        """Authenticated users should be redirected to their student dashboard."""
        self.client.force_login(self.user)
        response = self.client.get(reverse("pages:home"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("quiz:dashboard"))

    def test_compact_hero_content(self):
        """Hero must present the exact requested headline, supporting copy, and CTAs."""
        response = self.client.get(reverse("pages:home"))
        content = response.content.decode("utf-8")

        self.assertIn("Everything you need to move forward.", content)
        self.assertIn(
            "Practice skills, prepare for exams, explore courses, and build your career with NPTOR.",
            content,
        )
        self.assertIn("Start Practicing", content)
        self.assertIn("Explore Services", content)
        self.assertIn(reverse("quiz:practice"), content)
        self.assertIn("#services", content)

    def test_service_grid_cards_and_links(self):
        """Service grid must include the exact 6 service cards with accurate URLs."""
        response = self.client.get(reverse("pages:home"))
        content = response.content.decode("utf-8")

        self.assertIn("What would you like to do?", content)

        # 1. Practice & Learn
        self.assertIn("Practice &amp; Learn", content)
        self.assertIn(reverse("quiz:practice"), content)

        # 2. Certification Prep
        self.assertIn("Certification Prep", content)
        self.assertIn(reverse("quiz:certifications"), content)

        # 3. Government Exams
        self.assertIn("Government Exams", content)
        self.assertIn(reverse("quiz:government_catalog"), content)

        # 4. Academic & Entrance
        self.assertIn("Academic &amp; Entrance", content)
        self.assertIn(reverse("quiz:academic_entrance"), content)

        # 5. Courses & Organizations
        self.assertIn("Courses &amp; Organizations", content)
        self.assertIn(reverse("courses:course_list"), content)

        # 6. AI CV Builder
        self.assertIn("AI CV Builder", content)
        self.assertIn(reverse("cv:dashboard"), content)

    def test_store_visibility_banner_and_link(self):
        """Homepage must feature a distinct NPTOR Store entry with shopping bag icon and link to catalog."""
        response = self.client.get(reverse("pages:home"))
        content = response.content.decode("utf-8")

        self.assertIn("NPTOR Store", content)
        self.assertIn("Browse educational products and study essentials.", content)
        self.assertIn("fa-bag-shopping", content)
        self.assertIn(reverse("store:product_list"), content)
