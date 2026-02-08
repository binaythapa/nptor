from django.urls import path, include

# ================= ADMIN VIEWS =================
from organizations.views.admin.dashboard import org_dashboard
from organizations.views.admin.courses import (
    org_courses,
    org_course_attach,
    org_course_detach,
)
from organizations.views.admin.students import (
    org_students,
    org_student_add,
    org_student_update_role,
    org_student_remove,
)
from organizations.views.admin.assignments import (
    org_assignments,
    org_assignment_create,
    org_assignment_remove,
)
from organizations.views.admin.settings import org_settings

# ================= PUBLIC / STUDENT VIEWS =================
from organizations.views.my_courses import my_courses
from organizations.views.switch_org import switch_organization
from organizations.views.public import org_public_page


# =====================================================
# ADMIN URLS (namespaced: organizations_admin:*)
# =====================================================
admin_patterns = [
    # Dashboard
    path("dashboard/", org_dashboard, name="dashboard"),

    # Courses (ATTACH / DETACH)
    path("courses/", org_courses, name="courses"),
    path(
        "courses/attach/<int:course_id>/",
        org_course_attach,
        name="course_attach",
    ),
    path(
        "courses/detach/<int:course_id>/",
        org_course_detach,
        name="course_detach",
    ),

    # Students CRUD
    path("students/", org_students, name="students"),
    path("students/add/", org_student_add, name="student_add"),
    path(
        "students/<int:member_id>/role/",
        org_student_update_role,
        name="student_role",
    ),
    path(
        "students/<int:member_id>/remove/",
        org_student_remove,
        name="student_remove",
    ),

    # Assignments (COURSE → STUDENTS)
    path("assignments/", org_assignments, name="assignments"),
    path(
        "assignments/create/",
        org_assignment_create,
        name="assignment_create",
    ),
    path(
        "assignments/<int:assignment_id>/remove/",
        org_assignment_remove,
        name="assignment_remove",
    ),

    # Settings
    path("settings/", org_settings, name="settings"),
]


# =====================================================
# PUBLIC / STUDENT URLS (namespaced: organizations_public:*)
# =====================================================
public_patterns = [
    path("my-courses/", my_courses, name="my_courses"),
    path("switch-org/<int:org_id>/", switch_organization, name="switch_org"),
    path("<slug:slug>/", org_public_page, name="public_page"),
]


urlpatterns = [
    # -------- Organization Admin --------
    path(
        "admin/",
        include(
            (admin_patterns, "organizations_admin"),
            namespace="organizations_admin",
        ),
    ),

    # -------- Public / Student --------
    path(
        "",
        include(
            (public_patterns, "organizations_public"),
            namespace="organizations_public",
        ),
    ),
]
