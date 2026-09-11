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

    def track_payload(self, exams, prerequisites=None):
        prerequisites = prerequisites or {}
        data = {
            "title": "Certification Track",
            "slug": "certification-track",
            "description": "Three-stage track",
            "pricing_type": ExamTrack.PRICING_FREE,
            "trial_days": 7,
            "currency": "INR",
            "is_active": "on",
            "track_exams-TOTAL_FORMS": str(len(exams)),
            "track_exams-INITIAL_FORMS": "0",
            "track_exams-MIN_NUM_FORMS": "0",
            "track_exams-MAX_NUM_FORMS": "1000",
        }
        for index, exam in enumerate(exams):
            data.update({
                f"track_exams-{index}-exam": str(exam.pk),
                f"track_exams-{index}-order": str(index + 1),
                f"track_exams-{index}-is_required": "on",
            })
            if prerequisites.get(index):
                data[f"track_exams-{index}-prerequisite_exams"] = [str(item.pk) for item in prerequisites[index]]
        return data

    def test_create_track_accepts_multiple_exams_with_order_and_prerequisites(self):
        exam1 = self.make_exam("Fundamentals")
        exam2 = self.make_exam("Intermediate")
        exam3 = self.make_exam("Advanced")

        response = self.client.post(
            reverse("organizations_admin:org_track_create", kwargs={"slug": self.organization.slug}),
            self.track_payload(exams=[exam1, exam2, exam3], prerequisites={1: [exam1], 2: [exam2]}),
        )

        self.assertEqual(response.status_code, 302)
        track = ExamTrack.objects.get(slug="certification-track", organization=self.organization)
        memberships = TrackExam.objects.filter(track=track).order_by("order")
        self.assertEqual(list(memberships.values_list("exam_id", flat=True)), [exam1.pk, exam2.pk, exam3.pk])
        self.assertEqual(list(memberships.values_list("order", flat=True)), [1, 2, 3])
        self.assertEqual(list(memberships[1].prerequisite_exams.values_list("id", flat=True)), [exam1.pk])
        self.assertEqual(list(memberships[2].prerequisite_exams.values_list("id", flat=True)), [exam2.pk])

    def test_create_track_rejects_prerequisite_not_in_track(self):
        exam1 = self.make_exam("Exam 1")
        exam2 = self.make_exam("Exam 2")
        outside = self.make_exam("Outside")

        response = self.client.post(
            reverse("organizations_admin:org_track_create", kwargs={"slug": self.organization.slug}),
            self.track_payload(exams=[exam1, exam2], prerequisites={1: [outside]}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(ExamTrack.objects.filter(slug="certification-track", organization=self.organization).exists())

    def test_create_track_rejects_circular_prerequisites(self):
        exam1 = self.make_exam("Exam 1")
        exam2 = self.make_exam("Exam 2")

        response = self.client.post(
            reverse("organizations_admin:org_track_create", kwargs={"slug": self.organization.slug}),
            self.track_payload(exams=[exam1, exam2], prerequisites={0: [exam2], 1: [exam1]}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(ExamTrack.objects.filter(slug="certification-track", organization=self.organization).exists())

    def test_platform_admin_track_inline_exposes_prerequisites(self):
        from quiz.admin import ExamTrackAdmin

        self.assertIn("prerequisite_exams", ExamTrackAdmin.inlines[0].fields)
