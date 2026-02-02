from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

app_name = "courses"

urlpatterns = [
    path("", views.course_list, name="course_list"),

    # learning routes FIRST
    path("<slug:slug>/learn/", views.course_learn, name="course_learn"),
    path("<slug:slug>/learn/<int:lesson_id>/", views.course_learn, name="course_learn_lesson"),
    path(
        "<slug:slug>/learn/<int:lesson_id>/complete/",
        views.mark_lesson_completed,
        name="mark_lesson_completed"
    ),

    path(
        "<slug:slug>/certificate/pdf/",
        views.download_certificate_pdf,
        name="course_certificate_pdf"
    ),

    # detail LAST
    path("<slug:slug>/", views.course_detail, name="course_detail"),

    # courses/urls.py
    path(
        "video/progress/",
        views.track_video_progress,
        name="track_video_progress"
    ),

]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
