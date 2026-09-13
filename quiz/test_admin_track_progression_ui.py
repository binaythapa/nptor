from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse

from quiz.models import Exam, ExamTrack, TrackExam


User = get_user_model()


class AdminTrackProgressionUITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="admin-track-ui",
            email="admin-track-ui@example.com",
            password="test-pass",
        )
        self.exam1 = Exam.objects.create(
            title="Exam 1",
            question_count=10,
            duration_seconds=600,
            is_published=True,
        )
        self.exam2 = Exam.objects.create(
            title="Exam 2",
            question_count=10,
            duration_seconds=600,
            is_published=True,
        )
        self.track = ExamTrack.objects.create(
            title="Progression Track",
            slug="progression-track",
            is_active=True,
        )
        self.client.force_login(self.user)

    def test_track_form_exposes_progression_configuration(self):
        response = self.client.get(reverse("quiz:admin_track_update", args=[self.track.pk]))
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Prerequisite Exams")
        self.assertContains(response, "Order")
        self.assertContains(response, "+ Add Exam")
        self.assertContains(response, "No exams added yet")
        self.assertNotContains(response, "Select the reusable exams included in this Track")
        self.assertEqual(content.count('id="id_organization"'), 1)

    def test_track_search_templates_are_not_initialized_before_dynamic_clone(self):
        for path, marker in (
            ("js/admin_exam_selector.js", "select.closest(\"#track-exam-empty-form\")"),
            ("js/admin_single_exam_selector.js", "wrapper.closest(\"#track-exam-empty-form\")"),
        ):
            file_path = finders.find(path)
            self.assertIsNotNone(file_path)
            with open(file_path, encoding="utf-8") as source:
                self.assertIn(marker, source.read())

    def test_new_track_exam_defaults_to_next_visible_order(self):
        file_path = finders.find("js/admin_track_exam_formset.js")
        self.assertIsNotNone(file_path)
        with open(file_path, encoding="utf-8") as source:
            script = source.read()
        self.assertIn("const nextOrder = container.querySelectorAll(\".track-exam-row\").length;", script)
        self.assertIn("order.value = nextOrder;", script)

    def test_track_form_saves_order_required_and_prerequisite(self):
        response = self.client.post(
            reverse("quiz:admin_track_update", args=[self.track.pk]),
            {
                "title": self.track.title,
                "slug": self.track.slug,
                "description": "",
                "organization": "",
                "subscription_plans": [],
                "pricing_type": ExamTrack.PRICING_FREE,
                "monthly_price": "",
                "lifetime_price": "",
                "trial_days": 0,
                "currency": "INR",
                "is_active": "on",
                "track_exams-TOTAL_FORMS": "2",
                "track_exams-INITIAL_FORMS": "0",
                "track_exams-MIN_NUM_FORMS": "0",
                "track_exams-MAX_NUM_FORMS": "1000",
                "track_exams-0-exam": str(self.exam1.pk),
                "track_exams-0-order": "1",
                "track_exams-0-is_required": "on",
                "track_exams-0-prerequisite_exams": [],
                "track_exams-1-exam": str(self.exam2.pk),
                "track_exams-1-order": "2",
                "track_exams-1-is_required": "on",
                "track_exams-1-prerequisite_exams": [str(self.exam1.pk)],
            },
        )

        self.assertRedirects(response, reverse("quiz:admin_track_list"))
        membership = TrackExam.objects.get(track=self.track, exam=self.exam2)
        self.assertEqual(membership.order, 2)
        self.assertTrue(membership.is_required)
        self.assertEqual(list(membership.prerequisite_exams.values_list("pk", flat=True)), [self.exam1.pk])
