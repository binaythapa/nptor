from django.contrib.auth import get_user_model
from django.test import TestCase

from courses.models import Course
from organizations.models import Organization
from quiz.models import Exam, ExamTrack, TrackExam
from quiz.track_forms import TrackExamFormSet


class TrackPrerequisiteIsolationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="track-admin")
        self.org = Organization.objects.create(
            name="Tenant One",
            slug="tenant-one",
            org_type=Organization.TYPE_SCHOOL,
            created_by=self.user,
        )
        self.other_org = Organization.objects.create(
            name="Tenant Two",
            slug="tenant-two",
            org_type=Organization.TYPE_SCHOOL,
            created_by=self.user,
        )
        self.platform_exam = Exam.objects.create(
            title="Platform Exam",
            duration_seconds=600,
            is_published=True,
        )
        self.org_exam = Exam.objects.create(
            title="Tenant Exam",
            organization=self.org,
            duration_seconds=600,
            is_published=True,
        )
        self.other_org_exam = Exam.objects.create(
            title="Other Tenant Exam",
            organization=self.other_org,
            duration_seconds=600,
            is_published=True,
        )

    def test_organization_track_formset_only_exposes_same_organization_exams(self):
        track = ExamTrack.objects.create(title="Tenant Track", slug="tenant-track", organization=self.org)
        formset = TrackExamFormSet(instance=track, organization=self.org, prefix="track_exams")
        exam_queryset = formset.forms[0].fields["exam"].queryset
        self.assertEqual(list(exam_queryset), [self.org_exam])

    def test_platform_track_formset_only_exposes_platform_exams(self):
        track = ExamTrack.objects.create(title="Platform Track", slug="platform-track")
        formset = TrackExamFormSet(instance=track, organization=None, prefix="track_exams")
        exam_queryset = formset.forms[0].fields["exam"].queryset
        self.assertEqual(list(exam_queryset), [self.platform_exam])

    def test_prerequisite_must_be_an_included_exam(self):
        track = ExamTrack.objects.create(title="Tenant Track", slug="tenant-track", organization=self.org)
        data = {
            "track_exams-TOTAL_FORMS": "2",
            "track_exams-INITIAL_FORMS": "0",
            "track_exams-MIN_NUM_FORMS": "0",
            "track_exams-MAX_NUM_FORMS": "1000",
            "track_exams-0-exam": str(self.org_exam.pk),
            "track_exams-0-order": "1",
            "track_exams-0-is_required": "on",
            "track_exams-0-prerequisite_exams": [str(self.other_org_exam.pk)],
            "track_exams-1-exam": "",
            "track_exams-1-order": "2",
            "track_exams-1-is_required": "on",
            "track_exams-1-prerequisite_exams": [],
        }
        formset = TrackExamFormSet(data=data, instance=track, organization=self.org, prefix="track_exams")
        self.assertFalse(formset.is_valid())
        self.assertIn("Prerequisite exams must also be included in this Track.", formset.forms[0].errors["prerequisite_exams"])

    def test_organization_course_cannot_be_public(self):
        course = Course.objects.create(
            title="Tenant Course",
            description="Tenant content",
            level="beginner",
            organization=self.org,
            owner_type=Course.OWNER_ORGANIZATION,
            is_public=True,
        )
        self.assertFalse(course.is_public)
        self.assertFalse(course.is_publicly_available())

    def test_track_exam_prerequisites_are_stored_on_membership(self):
        track = ExamTrack.objects.create(title="Tenant Track", slug="tenant-track", organization=self.org)
        first = TrackExam.objects.create(track=track, exam=self.org_exam, order=1)
        second = TrackExam.objects.create(track=track, exam=self.other_org_exam, order=2)
        second.prerequisite_exams.add(first.exam)
        self.assertEqual(list(second.prerequisite_exams.all()), [first.exam])
