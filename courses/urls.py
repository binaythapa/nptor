from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from .views import (
    student_views,
    instructor_views,
    api_views,
    admin_views,
)
from courses.views.student_preview import course_preview
from courses.views.student_library import (
    my_courses,
    continue_learning,
    completed_courses,
)
from courses.views.student_enrollment import enroll_free_course
from courses.views.certificate import certificate_verify

from courses.views.instructor_views import update_order
from courses.permissions import (
    course_detail_access_required,
    course_learning_access_required,
    course_entitlement_required,
    lesson_course_access_required,
    video_progress_access_required,
)
from courses.services.permissions import (
    instructor_dashboard_access_required,
    course_creation_access_required,
)
from payments.views.checkout import course_checkout

# ============================================================
# APP CONFIGURATION
# ============================================================

app_name = "courses"


# ============================================================
# URL PATTERNS
# ============================================================

urlpatterns = [
    path("", student_views.course_list, name="course_list"),

    # Public certificate verification
    path(
        "certificate/<str:certificate_id>/",
        certificate_verify,
        name="certificate_verify",
    ),

    # Student learning library
    path("my-courses/", my_courses, name="my_courses"),
    path("continue-learning/", continue_learning, name="continue_learning"),
    path("completed/", completed_courses, name="completed_courses"),
    path("<slug:slug>/enroll-free/", enroll_free_course, name="enroll_free_course"),

    path(
        "<slug:slug>/preview/",
        course_preview,
        name="course_preview",
    ),
    path(
        "<slug:slug>/learn/",
        course_learning_access_required(student_views.course_learn),
        name="course_learn",
    ),
    path(
        "<slug:slug>/learn/<int:lesson_id>/",
        course_learning_access_required(student_views.course_learn),
        name="course_learn_lesson",
    ),
    path(
        "<slug:slug>/learn/<int:lesson_id>/complete/",
        lesson_course_access_required(student_views.mark_lesson_completed),
        name="mark_lesson_completed",
    ),
    path(
        "<slug:slug>/certificate/pdf/",
        course_entitlement_required(student_views.download_certificate_pdf),
        name="course_certificate_pdf",
    ),
    path(
        "video/progress/",
        video_progress_access_required(student_views.track_video_progress),
        name="track_video_progress",
    ),

    # Paid course checkout is owned by the payment application.
    path(
        "subscribe/<int:course_id>/",
        course_checkout,
        name="subscribe_course",
    ),

    path(
        "<slug:slug>/",
        course_detail_access_required(student_views.course_detail),
        name="course_detail",
    ),

    path(
        "instructor/dashboard/",
        instructor_dashboard_access_required(instructor_views.instructor_dashboard),
        name="instructor_dashboard",
    ),
    path(
        "instructor/course/create/",
        course_creation_access_required(instructor_views.course_create),
        name="course_create",
    ),
    path("instructor/course/<slug:slug>/edit/", instructor_views.course_edit, name="course_edit"),
    path("instructor/course/<slug:slug>/delete/", instructor_views.course_delete, name="course_delete"),
    path("instructor/course/<slug:slug>/builder/", instructor_views.course_builder, name="course_builder"),
    path("instructor/course/<slug:slug>/update-order/", update_order, name="update_order"),
    path("instructor/course/<slug:slug>/submit-review/", instructor_views.submit_course_for_review_view, name="submit-course-review"),
    path("instructor/course/<slug:slug>/toggle-publish/", instructor_views.toggle_publish_course, name="toggle_publish_course"),
    path("instructor/lesson/<int:lesson_id>/edit/", instructor_views.lesson_edit, name="lesson_edit"),

    path("admin/courses/", admin_views.course_dashboard, name="admin-course-dashboard"),
    path("admin/courses/all/", admin_views.all_courses, name="admin-all-courses"),
    path("admin/courses/pending/", admin_views.pending_courses, name="admin-pending-courses"),
    path("admin/course/<slug:slug>/review/", admin_views.review_course, name="admin-review-course"),
    path("admin/course/<slug:slug>/approve/", admin_views.approve_course_view, name="admin-approve-course"),
    path("admin/course/<slug:slug>/request-changes/", admin_views.request_course_changes_view, name="admin-request-course-changes"),
    path("admin/course/<slug:slug>/reject/", admin_views.reject_course_view, name="admin-reject-course"),
    path("admin/course/<slug:slug>/publish/", admin_views.publish_course_view, name="admin-publish-course"),
    path("admin/course/<slug:slug>/unpublish/", admin_views.unpublish_course_view, name="admin-unpublish-course"),

    path("api/section/create/", api_views.create_section, name="api_create_section"),
    path("api/section/delete/<int:section_id>/", api_views.delete_section, name="api_delete_section"),
    path("api/lesson/create/", api_views.create_lesson, name="api_create_lesson"),
    path("api/lesson/delete/<int:lesson_id>/", api_views.delete_lesson, name="api_delete_lesson"),
    path("api/lesson/edit/", api_views.edit_lesson, name="api_edit_lesson"),
    path("api/order/update/", api_views.update_order, name="api_update_order"),
]


urlpatterns += static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT,
)
