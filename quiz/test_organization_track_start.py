from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from organizations.models import Organization, ResourceAccess, ResourceAssignment
from quiz.models import ExamTrack


User = get_user_model()


class OrganizationTrackStartTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="org-track-student",
            password="test-password",
        )
        self.client.force_login(self.user)
        self.organization = Organization.objects.create(
            name="Organization A",
            slug="organization-a",
            org_type=Organization.TYPE_SCHOOL,
        )
        self.track = ExamTrack.objects.create(
            title="Data Analyst Certification",
            slug="data-analyst-certification",
            organization=self.organization,
            is_active=True,
        )

    def _assign_track(self):
        assignment = ResourceAssignment.objects.create(
            student=self.user,
            organization=self.organization,
            resource_type=ResourceAssignment.RESOURCE_TRACK,
            track=self.track,
            status=ResourceAssignment.STATUS_ASSIGNED,
            is_active=True,
        )
        ResourceAccess.objects.create(
            user=self.user,
            resource_type=ResourceAccess.RESOURCE_TRACK,
            track=self.track,
            source=ResourceAccess.SOURCE_ORGANIZATION,
            organization=self.organization,
            assignment=assignment,
            is_active=True,
        )

    def test_assigned_organization_track_opens_learning_page(self):
        self._assign_track()

        response = self.client.get(
            reverse("quiz:learning_track", kwargs={"slug": self.track.slug})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.track.title)
        self.assertContains(response, "You have access")

    def test_unassigned_organization_track_is_not_openable(self):
        response = self.client.get(
            reverse("quiz:learning_track", kwargs={"slug": self.track.slug})
        )

        self.assertEqual(response.status_code, 404)
