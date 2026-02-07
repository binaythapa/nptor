from django.urls import path, include

from organizations.views.admin import (
    org_dashboard,
    org_courses,
    org_students,
    org_assignments,
    org_settings,
)
from organizations.views.my_courses import my_courses
from organizations.views.switch_org import switch_organization
from organizations.views.public import org_public_page




# =====================================================
# ADMIN URLS (namespaced)
# =====================================================
admin_patterns = [
    path("dashboard/", org_dashboard, name="dashboard"),
    path("courses/", org_courses, name="courses"),
    path("students/", org_students, name="students"),
    path("assignments/", org_assignments, name="assignments"),
    path("settings/", org_settings, name="settings"),
]


# =====================================================
# PUBLIC / STUDENT URLS
# =====================================================
public_patterns = [
    path("my-courses/", my_courses, name="my_courses"),
    path("switch-org/<int:org_id>/", switch_organization, name="switch_org"),
    path("<slug:slug>/", org_public_page, name="public_page"),
]


urlpatterns = [
    # -------- Admin (organizations_admin:*) --------
    path(
        "admin/",
        include(
            (admin_patterns, "organizations_admin"),
            namespace="organizations_admin",
        ),
    ),

    # -------- Public / Student (organizations_public:*) --------
    path(
        "",
        include(
            (public_patterns, "organizations_public"),
            namespace="organizations_public",
        ),
    ),
]
