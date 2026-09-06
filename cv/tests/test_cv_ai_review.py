from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cv.models_cv import CV
from cv.models_template import CVTemplate
from cv.services.cv_builder import create_cv


class CVAIReviewViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="cv-ai-review-user",
            email="cv-ai-review@example.com",
        )
        self.template = CVTemplate.objects.create(slug="ai-review-template", name="AI Review Template")
        self.cv = create_cv(self.user, "Gyanendra Thapa", self.template)
        self.client.force_login(self.user)

    def test_ai_review_heading_has_non_overlapping_spacing_contract(self):
        response = self.client.get(reverse("cv:cv_ai_review", kwargs={"pk": self.cv.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="cv-ai-review-heading"')
        self.assertContains(response, 'class="title mb-1 cv-ai-review-title"')
        self.assertContains(response, 'class="subtitle is-6 mb-0 cv-ai-review-subtitle"')
        self.assertContains(response, 'static/css/pages/cv_ai_review.css')
