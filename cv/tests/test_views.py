from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cv.models import CareerProfile, CV, CVTemplate


class CVViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="cv-view-user", email="cvview@example.com", password="password"
        )
        self.other_user = get_user_model().objects.create_user(
            username="cv-other-user", email="other@example.com", password="password"
        )
        self.template = CVTemplate.objects.create(slug="ats-classic", name="ATS Classic", config={"style": "classic"})

    def test_anonymous_user_is_redirected(self):
        response = self.client.get(reverse("cv:dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_profile_page_prefills_account_data(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("cv:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cvview@example.com")

    def test_cv_can_be_created_without_learning_data(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("cv:cv_create"), {"title": "My CV"})
        self.assertEqual(response.status_code, 302)
        cv = CV.objects.get(owner=self.user)
        self.assertEqual(cv.title, "My CV")
        self.assertTrue(CareerProfile.objects.filter(user=self.user).exists())

    def test_user_cannot_edit_another_users_cv(self):
        self.client.force_login(self.other_user)
        cv = CV.objects.create(
            owner=self.user,
            profile=CareerProfile.objects.create(user=self.user),
            template=self.template,
            title="Private CV",
        )
        response = self.client.get(reverse("cv:cv_edit", args=[cv.pk]))
        self.assertEqual(response.status_code, 404)

    def test_edit_owned_cv_redirects_to_builder(self):
        self.client.force_login(self.user)
        cv = CV.objects.create(
            owner=self.user,
            profile=CareerProfile.objects.create(user=self.user),
            template=self.template,
            title="My CV",
        )
        response = self.client.get(reverse("cv:cv_edit", args=[cv.pk]))
        self.assertRedirects(response, reverse("cv:cv_builder", kwargs={"pk": cv.pk}))

    def test_dashboard_lists_only_owned_cvs(self):
        CV.objects.create(owner=self.user, profile=CareerProfile.objects.create(user=self.user), template=self.template, title="My CV")
        CV.objects.create(owner=self.other_user, profile=CareerProfile.objects.create(user=self.other_user), template=self.template, title="Other CV")
        self.client.force_login(self.user)
        response = self.client.get(reverse("cv:dashboard"))
        self.assertContains(response, "My CV")
        self.assertNotContains(response, "Other CV")
