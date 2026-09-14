from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from organizations.models import Organization, OrganizationMember
from organizations.models.role import OrganizationRole
from quiz.models import ExamTrack


class AdminTrackListUITests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="owner", password="pass")
        self.org = Organization.objects.create(name="School", slug="school")
        OrganizationMember.objects.create(
            user=self.user,
            organization=self.org,
            role=OrganizationRole.OWNER,
            is_active=True,
        )
        self.client.login(username="owner", password="pass")
        self.track = ExamTrack.objects.create(
            organization=self.org,
            title="Data Analyst Certification",
            slug="data-analyst-certification",
            description="Demo certification track",
        )

    def test_track_list_uses_admin_ui_structure(self):
        response = self.client.get(
            reverse(
                "organizations_admin:org_track_list",
                kwargs={"slug": self.org.slug},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "admin-page-header")
        self.assertContains(response, "admin-panel")
        self.assertContains(response, "admin-table")
        self.assertContains(response, "Data Analyst Certification")
        self.assertContains(response, "Edit")
        self.assertContains(response, "Exams &amp; Prerequisites", html=False)

    def test_track_list_keeps_create_action(self):
        response = self.client.get(
            reverse(
                "organizations_admin:org_track_list",
                kwargs={"slug": self.org.slug},
            )
        )
        self.assertContains(response, "Create Track")
        self.assertContains(
            response,
            reverse(
                "organizations_admin:org_track_create",
                kwargs={"slug": self.org.slug},
            ),
            html=False,
        )
