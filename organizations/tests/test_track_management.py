from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from organizations.models import Organization, OrganizationMember
from organizations.models.role import OrganizationRole
from quiz.models import Exam, ExamTrack, TrackExam


class OrganizationTrackManagementTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(username="track-owner", password="test-password")
        self.organization = Organization.objects.create(
            name="Track School",
            slug="track-school",
            org_type=Organization.TYPE_SCHOOL,
            created_by=self.owner,
        )
        OrganizationMember.objects.create(
            user=self.owner,
            organization=self.organization,
            role=OrganizationRole.ORG_OWNER,
            is_active=True,
        )
        self.client = Client()
        self.client.force_login(self.owner)

    def make_exam(self, title):
        return Exam.objects.create(
            title=title,
            organization=self.organization,
            question_count=10,
            duration_seconds=600,
            is_published=True,
        )

    def test_create_track_accepts_multiple_exams_with_order_and_prerequisites(self):
        exam1 = self.make_exam("Fundamentals")
        exam2 = self.make_exam("Intermediate")
        exam3 = self.make_exam("Advanced")

        response = self.client.post(
            reverse("organizations_admin:org_track_create", kwargs={"slug": self.organization.slug}),
            {
                "title": "Certification Track",
                "slug": "certification-track",
                "description": "Three-stage track",
                "pricing_type": ExamTrack.PRICING_FREE,
                "trial_days": 7,
                "currency": "INR",
                "is_active": "on",
                "track_exam-TOTAL_FORMS": "3",
                "track_exam-INITIAL_FORMS": "0",
                "track_exam-MIN_NUM_FORMS": "0",
                "track_exam-MAX_NUM_FORMS": "1000",
                "track_exam-0-exam": str(exam1.pk),
                "track_exam-0-order": "1",
                "track_exam-0-is_required": "on",
                "track_exam-1-exam": str(exam2.pk),
                "track_exam-1-order": "2",
                "track_exam-1-is_required": "on",
                "track_exam-1-prerequisite_exams": str(exam1.pk),
                "track_exam-2-exam": str(exam3.pk),
                "track_exam-2-order": "3",
                "track_exam-2-is_required": "on",
                "track_exam-2-prerequisite_exams": str(exam2.pk),
            },
        )

        self.assertEqual(response.status_code, 302)
        track = ExamTrack.objects.get(slug="certification-track", organization=self.organization)
        memberships = TrackExam.objects.filter(track=track).order_by("order")
        self.assertEqual(list(memberships.values_list("exam_id", flat=True)), [exam1.pk, exam2.pk, exam3.pk])
        self.assertEqual(list(memberships.values_list("order", flat=True)), [1, 2, 3])
        self.assertEqual(list(memberships[1].prerequisite_exams.values_list("id", flat=True)), [exam1.pk])
        self.assertEqual(list(memberships[2].prerequisite_exams.values_list("id", flat=True)), [exam2.pk])

    def test_track_exam_prerequisite_must_be_in_same_track(self):
        track = ExamTrack.objects.create(
            title="Track",
            slug="track",
            organization=self.organization,
        )
        exam1 = self.make_exam("Exam 1")
        exam2 = self.make_exam("Exam 2")
        outside = self.make_exam("Outside")
        membership1 = TrackExam.objects.create(track=track, exam=exam1, order=1)
        membership2 = TrackExam.objects.create(track=track, exam=exam2, order=2)
        membership2.prerequisite_exams.add(outside)

        self.assertFalse(
            membership2.prerequisite_exams.filter(
                track_memberships__track=track
            ).exists()
        )
        self.assertEqual(membership1.order, 1)

    def test_platform_admin_track_inline_exposes_prerequisites(self):
        from quiz.admin import ExamTrackAdmin

        self.assertIn("prerequisite_exams", ExamTrackAdmin.inlines[0].fields)
