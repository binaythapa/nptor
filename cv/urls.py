from django.urls import path

from . import views

app_name = "cv"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("profile/", views.profile, name="profile"),
    path("create/", views.cv_create, name="cv_create"),
    path("<int:pk>/edit/", views.cv_edit, name="cv_edit"),
    path("<int:pk>/duplicate/", views.cv_duplicate, name="cv_duplicate"),
    path("templates/", views.cv_templates, name="cv_templates"),
    path("<int:pk>/preview/", views.cv_preview, name="cv_preview"),
    path("<int:pk>/versions/", views.cv_versions, name="cv_versions"),
    path("import/", views.cv_import, name="cv_import"),
    path("import/<int:pk>/review/", views.cv_import_review, name="cv_import_review"),
]
