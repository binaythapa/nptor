from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from .views import *

app_name = "courses"

urlpatterns = [

# ==================================================
# CERTIFICATE
# ==================================================

path(
    "certificate/<str:certificate_id>/",
    certificate_verify,
    name="certificate_verify",
),

path(
    "certificate/download/<str:certificate_id>/",
    student_views.certificate_download_public,
    name="certificate_download_public",
),

# ==================================================
# STUDENT
# ==================================================

path("", student_views.course_list, name="course_list"),

path(
    "<slug:slug>/learn/",
    student_views.course_learn,
    name="course_learn"
),

path(
    "<slug:slug>/learn/<int:lesson_id>/",
    student_views.course_learn,
    name="course_learn_lesson"
),

path(
    "<slug:slug>/learn/<int:lesson_id>/complete/",
    student_views.mark_lesson_completed,
    name="mark_lesson_completed"
),

path(
    "<slug:slug>/certificate/pdf/",
    student_views.download_certificate_pdf,
    name="course_certificate_pdf"
),

path(
    "video/progress/",
    student_views.track_video_progress,
    name="track_video_progress"
),

path(
    "subscribe/<int:course_id>/",
    student_views.subscribe_course,
    name="subscribe_course"
),

# ==================================================
# INSTRUCTOR
# ==================================================

path(
    "instructor/dashboard/",
    instructor_views.instructor_dashboard,
    name="instructor_dashboard"
),

path(
    "instructor/course/create/",
    instructor_views.course_create,
    name="course_create"
),

path(
    "instructor/course/<slug:slug>/edit/",
    instructor_views.course_edit,
    name="course_edit"
),

path(
    "instructor/course/<slug:slug>/delete/",
    instructor_views.course_delete,
    name="course_delete"
),

path(
    "instructor/course/<slug:slug>/builder/",
    instructor_views.course_builder,
    name="course_builder"
),

path(
    "instructor/course/<slug:slug>/toggle-publish/",
    instructor_views.toggle_publish_course,
    name="toggle_publish_course"
),

path(
    "instructor/lesson/<int:lesson_id>/edit/",
    instructor_views.lesson_edit,
    name="lesson_edit"
),

# ==================================================
# API
# ==================================================

path(
    "api/categories-by-domain/",
    api_views.get_categories_by_domain,
    name="categories_by_domain"
),


path(
    "api/section/create/",
    api_views.create_section,
    name="api_create_section"
),




path(
    "api/section/delete/<int:section_id>/",
    api_views.delete_section,
    name="api_delete_section"
),

path(
    "api/lesson/create/",
    api_views.create_lesson,
    name="api_create_lesson"
),

path(
    "api/lesson/delete/<int:lesson_id>/",
    api_views.delete_lesson,
    name="api_delete_lesson"
),

path(
    "api/lesson/edit/",
    api_views.edit_lesson,
    name="api_edit_lesson"
),

path(
    "api/order/update/",
    api_views.update_order,
    name="api_update_order"
),



# ==================================================
# COURSE DETAIL (KEEP LAST)
# ==================================================

path(
    "<slug:slug>/",
    student_views.course_detail,
    name="course_detail"
),

]

urlpatterns += static(
settings.MEDIA_URL,
document_root=settings.MEDIA_ROOT
)



