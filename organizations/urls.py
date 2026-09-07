from django.urls import path, include

from organizations.views.admin.dashboard import org_dashboard
from organizations.views.admin.portfolio import org_portfolio
from organizations.views.admin.courses import *
from organizations.views.admin.students import org_students, org_student_add, org_student_update_role, org_student_remove
from organizations.views.admin.assignments import org_assignments, org_assignment_create, org_assignment_remove
from organizations.views.admin.settings import org_settings
from organizations.views.admin.exams import *
from organizations.views.admin.questions import *
from organizations.views.admin.tracks import *
from organizations.views.my_courses import my_courses
from organizations.views.public import org_public_page
from organizations.views.student_portal import organization_learning
from organizations.views.admin.domains import *
from organizations.views.admin.categories import *

admin_patterns = [
    path("dashboard/", org_dashboard, name="dashboard"),
    path("portfolio/", org_portfolio, name="portfolio"),
    path("courses/", org_courses, name="courses"),
    path("courses/attach/<int:course_id>/", org_course_attach, name="course_attach"),
    path("courses/detach/<int:course_id>/", org_course_detach, name="course_detach"),
    path("courses/manage/", org_course_list, name="org_course_list"),
    path("courses/add/", org_course_create, name="org_course_create"),
    path("courses/<int:pk>/edit/", org_course_edit, name="org_course_edit"),
    path("courses/<int:pk>/delete/", org_course_delete, name="org_course_delete"),
    path("students/", org_students, name="students"),
    path("students/add/", org_student_add, name="student_add"),
    path("students/<int:member_id>/role/", org_student_update_role, name="student_role"),
    path("students/<int:member_id>/remove/", org_student_remove, name="student_remove"),
    path("assignments/", org_assignments, name="assignments"),
    path("assignments/create/", org_assignment_create, name="assignment_create"),
    path("assignments/<int:assignment_id>/remove/", org_assignment_remove, name="assignment_remove"),
    path("questions/", org_question_dashboard, name="questions"),
    path("questions/add/", org_add_question, name="question_add"),
    path("questions/<int:pk>/edit/", org_edit_question, name="question_edit"),
    path("questions/<int:pk>/deactivate/", org_question_deactivate, name="question_deactivate"),
    path("questions/<int:pk>/delete/", org_question_delete, name="question_delete"),
    path("tracks/", org_track_list, name="org_track_list"),
    path("tracks/add/", org_track_create, name="org_track_create"),
    path("tracks/<int:pk>/edit/", org_track_edit, name="org_track_edit"),
    path("tracks/<int:pk>/delete/", org_track_delete, name="org_track_delete"),
    path("tracks/attach/<int:pk>/", org_track_attach, name="track_attach"),
    path("tracks/detach/<int:pk>/", org_track_detach, name="track_detach"),
    path("exams/", org_exam_list, name="exams"),
    path("exams/add/", org_exam_create, name="exam_create"),
    path("exams/<int:pk>/edit/", org_exam_update, name="exam_update"),
    path("exams/<int:pk>/delete/", org_exam_delete, name="exam_delete"),
    path("exams/attach/<int:pk>/", org_exam_attach, name="exam_attach"),
    path("exams/detach/<int:pk>/", org_exam_detach, name="exam_detach"),
    path("settings/", org_settings, name="settings"),
    path("domains/", org_domain_list, name="domain_list"),
    path("domains/add/", org_domain_create, name="domain_create"),
    path("domains/<int:pk>/edit/", org_domain_edit, name="domain_edit"),
    path("domains/<int:pk>/delete/", org_domain_delete, name="domain_delete"),
    path("categories/", org_category_list, name="category_list"),
    path("categories/add/", org_category_create, name="category_create"),
    path("categories/<int:pk>/edit/", org_category_edit, name="category_edit"),
    path("categories/<int:pk>/delete/", org_category_delete, name="category_delete"),
]

public_patterns = [
    path("my-courses/", my_courses, name="my_courses"),
    path("learning/", organization_learning, name="learning"),
    path("", org_public_page, name="public_page"),
]

urlpatterns = [
    path("admin/", include((admin_patterns, "organizations_admin"), namespace="organizations_admin")),
    path("", include((public_patterns, "organizations_public"), namespace="organizations_public")),
]
