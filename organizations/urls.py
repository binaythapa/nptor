from django.urls import path, include
from organizations.views.admin.dashboard import org_dashboard
from organizations.views.admin.portfolio import org_portfolio
from organizations.views.admin.tenant_domains import organization_domains, organization_domain_verify, organization_domain_primary
from organizations.views.admin.courses import *
from organizations.views.admin.payment import organization_payment_checkout
from organizations.views.admin.students import org_students, org_student_add, org_student_update_role, org_student_remove, org_student_detail, org_student_detail_edit, org_student_enroll, org_student_enrollment_edit, org_student_enrollment_transfer
from organizations.views.admin.assignments import org_assignments, org_assignment_create, org_assignment_remove
from organizations.views.admin.settings import org_settings
from organizations.views.admin.exams import *
from organizations.views.admin.questions import *
from organizations.views.admin.tracks import *
from organizations.views.my_courses import my_courses
from organizations.views.public import org_public_page
from organizations.views.student_portal import organization_learning
from organizations.views.member_portal import organization_workspace
from organizations.views.admin.domains import *
from organizations.views.admin.categories import *
from organizations.views.admin.academic import academic_dashboard, academic_year_create, academic_year_edit, academic_year_toggle, class_create, class_edit, class_toggle, section_create, section_edit, section_toggle, teacher_assign, student_enroll
from organizations.views.admin.class_assignments import class_assignment_create
from organizations.views.student_profile import organization_student_profile, organization_student_profile_edit, organization_student_profile_admin, organization_student_profile_admin_edit

admin_patterns = [
    path("dashboard/", org_dashboard, name="dashboard"), path("portfolio/", org_portfolio, name="portfolio"),
    path("tenant-domains/", organization_domains, name="tenant_domains"), path("tenant-domains/<int:pk>/verify/", organization_domain_verify, name="tenant_domain_verify"), path("tenant-domains/<int:pk>/primary/", organization_domain_primary, name="tenant_domain_primary"),
    path("courses/", org_courses, name="courses"),
    path("courses/public/subscribe/<int:course_id>/", org_public_course_subscribe, name="public_course_subscribe"),
    path("tracks/public/subscribe/<int:track_id>/", org_public_track_subscribe, name="public_track_subscribe"),
    path("payment-checkout/<int:payment_id>/", organization_payment_checkout, name="organization_payment_checkout"),
    path("courses/attach/<int:course_id>/", org_course_attach, name="course_attach"), path("courses/detach/<int:course_id>/", org_course_detach, name="course_detach"), path("courses/manage/", org_course_list, name="org_course_list"), path("courses/add/", org_course_create, name="org_course_create"), path("courses/<int:pk>/edit/", org_course_edit, name="org_course_edit"), path("courses/<int:pk>/delete/", org_course_delete, name="org_course_delete"),
    path("students/", org_students, name="students"), path("students/add/", org_student_add, name="student_add"), path("students/<int:student_id>/", org_student_detail, name="student_detail"), path("students/<int:student_id>/edit/", org_student_detail_edit, name="student_detail_edit"), path("students/<int:student_id>/enroll/", org_student_enroll, name="student_enroll"), path("students/<int:student_id>/enrollment/<int:enrollment_id>/edit/", org_student_enrollment_edit, name="student_enrollment_edit"), path("students/<int:student_id>/enrollment/<int:enrollment_id>/transfer/", org_student_enrollment_transfer, name="student_enrollment_transfer"), path("students/<int:member_id>/role/", org_student_update_role, name="student_role"), path("students/<int:member_id>/remove/", org_student_remove, name="student_remove"),
    path("academic/", academic_dashboard, name="academic"), path("academic/years/add/", academic_year_create, name="academic_year_create"), path("academic/years/<int:year_id>/edit/", academic_year_edit, name="academic_year_edit"), path("academic/years/<int:year_id>/toggle/", academic_year_toggle, name="academic_year_toggle"), path("academic/classes/add/", class_create, name="academic_class_create"), path("academic/classes/<int:class_id>/edit/", class_edit, name="academic_class_edit"), path("academic/classes/<int:class_id>/toggle/", class_toggle, name="academic_class_toggle"), path("academic/sections/add/", section_create, name="academic_section_create"), path("academic/sections/<int:section_id>/edit/", section_edit, name="academic_section_edit"), path("academic/sections/<int:section_id>/toggle/", section_toggle, name="academic_section_toggle"), path("academic/sections/<int:section_id>/teachers/add/", teacher_assign, name="teacher_assign"), path("academic/students/<int:student_id>/enroll/<int:section_id>/", student_enroll, name="student_enroll_legacy"), path("academic/sections/<int:section_id>/assign-resource/", class_assignment_create, name="class_assignment_create"),
    path("assignments/", org_assignments, name="assignments"), path("assignments/create/", org_assignment_create, name="assignment_create"), path("assignments/<int:assignment_id>/remove/", org_assignment_remove, name="assignment_remove"),
    path("questions/", org_question_dashboard, name="questions"), path("questions/add/", org_add_question, name="question_add"), path("questions/<int:pk>/edit/", org_edit_question, name="question_edit"), path("questions/<int:pk>/deactivate/", org_question_deactivate, name="question_deactivate"), path("questions/<int:pk>/delete/", org_question_delete, name="question_delete"),
    path("tracks/", org_track_list, name="org_track_list"), path("tracks/add/", org_track_create, name="org_track_create"), path("tracks/<int:pk>/edit/", org_track_edit, name="org_track_edit"), path("tracks/<int:pk>/exams/", org_track_exams, name="org_track_exams"), path("tracks/<int:pk>/delete/", org_track_delete, name="org_track_delete"), path("tracks/attach/<int:pk>/", org_track_attach, name="track_attach"), path("tracks/detach/<int:pk>/", org_track_detach, name="track_detach"),
    path("exams/", org_exam_list, name="exams"), path("exams/add/", org_exam_create, name="exam_create"), path("exams/<int:pk>/edit/", org_exam_update, name="exam_update"), path("exams/<int:pk>/delete/", org_exam_delete, name="exam_delete"),
    path("settings/", org_settings, name="settings"), path("domains/", org_domain_list, name="domain_list"), path("domains/add/", org_domain_create, name="domain_create"), path("domains/<int:pk>/edit/", org_domain_edit, name="domain_edit"), path("domains/<int:pk>/delete/", org_domain_delete, name="domain_delete"),
    path("categories/", org_category_list, name="category_list"), path("categories/add/", org_category_create, name="category_add"), path("categories/<int:pk>/edit/", org_category_edit, name="category_edit"), path("categories/<int:pk>/delete/", org_category_delete, name="category_delete"),
]
public_patterns = [
    path("workspace/", organization_workspace, name="workspace"), path("my-courses/", my_courses, name="my_courses"), path("learning/", organization_learning, name="learning"), path("student-profile/", organization_student_profile, name="student_profile"), path("student-profile/edit/", organization_student_profile_edit, name="student_profile_edit"), path("student-profile/<int:student_id>/", organization_student_profile_admin, name="student_profile_admin"), path("student-profile/<int:student_id>/edit/", organization_student_profile_admin_edit, name="student_profile_admin_edit"), path("", org_public_page, name="public_page"),
]
urlpatterns = [path("admin/", include((admin_patterns, "organizations_admin"), namespace="organizations_admin")), path("", include((public_patterns, "organizations_public"), namespace="organizations_public"))]
