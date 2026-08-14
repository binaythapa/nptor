from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from .views import (
    student_views,
    instructor_views,
    api_views,
    admin_views,
)


# ============================================================
# APP CONFIGURATION
# ============================================================

app_name = "courses"


# ============================================================
# URL PATTERNS
# ============================================================

urlpatterns = [

    # ========================================================
    # STUDENT
    # ========================================================

    path(
        "",
        student_views.course_list,
        name="course_list",
    ),

    path(
        "<slug:slug>/learn/",
        student_views.course_learn,
        name="course_learn",
    ),

    path(
        "<slug:slug>/learn/<int:lesson_id>/",
        student_views.course_learn,
        name="course_learn_lesson",
    ),

    path(
        "<slug:slug>/learn/<int:lesson_id>/complete/",
        student_views.mark_lesson_completed,
        name="mark_lesson_completed",
    ),

    path(
        "<slug:slug>/certificate/pdf/",
        student_views.download_certificate_pdf,
        name="course_certificate_pdf",
    ),

    path(
        "video/progress/",
        student_views.track_video_progress,
        name="track_video_progress",
    ),

    path(
        "subscribe/<int:course_id>/",
        student_views.subscribe_course,
        name="subscribe_course",
    ),

    # --------------------------------------------------------
    # IMPORTANT
    #
    # Keep the generic course detail URL AFTER all specific
    # URLs above.
    # --------------------------------------------------------

    path(
        "<slug:slug>/",
        student_views.course_detail,
        name="course_detail",
    ),


    # ========================================================
    # INSTRUCTOR
    # ========================================================

    path(
        "instructor/dashboard/",
        instructor_views.instructor_dashboard,
        name="instructor_dashboard",
    ),

    path(
        "instructor/course/create/",
        instructor_views.course_create,
        name="course_create",
    ),

    path(
        "instructor/course/<slug:slug>/edit/",
        instructor_views.course_edit,
        name="course_edit",
    ),

    path(
        "instructor/course/<slug:slug>/delete/",
        instructor_views.course_delete,
        name="course_delete",
    ),

    path(
        "instructor/course/<slug:slug>/builder/",
        instructor_views.course_builder,
        name="course_builder",
    ),


    # ========================================================
    # COURSE APPROVAL
    # ========================================================

    path(
        "instructor/course/<slug:slug>/submit-review/",
        instructor_views.submit_course_for_review_view,
        name="submit-course-review",
    ),


    # ========================================================
    # COURSE PUBLISH
    # ========================================================

    path(
        "instructor/course/<slug:slug>/toggle-publish/",
        instructor_views.toggle_publish_course,
        name="toggle_publish_course",
    ),


    # ========================================================
    # LESSON EDIT
    # ========================================================

    path(
        "instructor/lesson/<int:lesson_id>/edit/",
        instructor_views.lesson_edit,
        name="lesson_edit",
    ),


    # ========================================================
    # ADMIN COURSE MODERATION
    # ========================================================

    # --------------------------------------------------------
    # Main Admin Course Dashboard
    #
    # /courses/admin/courses/
    # --------------------------------------------------------

    path(
        "admin/courses/",
        admin_views.course_dashboard,
        name="admin-course-dashboard",
    ),

    # --------------------------------------------------------
    # All Courses
    #
    # /courses/admin/courses/all/
    # --------------------------------------------------------

    path(
        "admin/courses/all/",
        admin_views.all_courses,
        name="admin-all-courses",
    ),

    # --------------------------------------------------------
    # Pending Courses
    #
    # /courses/admin/courses/pending/
    # --------------------------------------------------------

    path(
        "admin/courses/pending/",
        admin_views.pending_courses,
        name="admin-pending-courses",
    ),

    # --------------------------------------------------------
    # Review Course
    #
    # /courses/admin/course/<slug>/review/
    # --------------------------------------------------------

    path(
        "admin/course/<slug:slug>/review/",
        admin_views.review_course,
        name="admin-review-course",
    ),

    # --------------------------------------------------------
    # Approve Course
    #
    # /courses/admin/course/<slug>/approve/
    # --------------------------------------------------------

    path(
        "admin/course/<slug:slug>/approve/",
        admin_views.approve_course_view,
        name="admin-approve-course",
    ),

    # --------------------------------------------------------
    # Request Changes
    #
    # /courses/admin/course/<slug>/request-changes/
    # --------------------------------------------------------

    path(
        "admin/course/<slug:slug>/request-changes/",
        admin_views.request_course_changes_view,
        name="admin-request-course-changes",
    ),

    # --------------------------------------------------------
    # Reject Course
    #
    # /courses/admin/course/<slug>/reject/
    # --------------------------------------------------------

    path(
        "admin/course/<slug:slug>/reject/",
        admin_views.reject_course_view,
        name="admin-reject-course",
    ),

    # --------------------------------------------------------
    # Publish Course
    #
    # /courses/admin/course/<slug>/publish/
    # --------------------------------------------------------

    path(
        "admin/course/<slug:slug>/publish/",
        admin_views.publish_course_view,
        name="admin-publish-course",
    ),

    # --------------------------------------------------------
    # Unpublish Course
    #
    # /courses/admin/course/<slug>/unpublish/
    # --------------------------------------------------------

    path(
        "admin/course/<slug:slug>/unpublish/",
        admin_views.unpublish_course_view,
        name="admin-unpublish-course",
    ),


    # ========================================================
    # API
    # ========================================================

    # --------------------------------------------------------
    # SECTION
    # --------------------------------------------------------

    path(
        "api/section/create/",
        api_views.create_section,
        name="api_create_section",
    ),

    path(
        "api/section/delete/<int:section_id>/",
        api_views.delete_section,
        name="api_delete_section",
    ),

    # --------------------------------------------------------
    # LESSON
    # --------------------------------------------------------

    path(
        "api/lesson/create/",
        api_views.create_lesson,
        name="api_create_lesson",
    ),

    path(
        "api/lesson/delete/<int:lesson_id>/",
        api_views.delete_lesson,
        name="api_delete_lesson",
    ),

    path(
        "api/lesson/edit/",
        api_views.edit_lesson,
        name="api_edit_lesson",
    ),

    # --------------------------------------------------------
    # ORDER
    # --------------------------------------------------------

    path(
        "api/order/update/",
        api_views.update_order,
        name="api_update_order",
    ),
]


# ============================================================
# MEDIA FILES - DEVELOPMENT
# ============================================================

urlpatterns += static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT,
)