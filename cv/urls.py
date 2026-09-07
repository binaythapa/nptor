from django.urls import path

from . import views

app_name = "cv"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("profile/", views.profile, name="profile"),
    path("profile/records/<str:section>/add/", views.profile_record_add, name="profile_record_add"),
    path("profile/records/<str:section>/<int:pk>/edit/", views.profile_record_edit, name="profile_record_edit"),
    path("profile/records/<str:section>/<int:pk>/delete/", views.profile_record_delete, name="profile_record_delete"),
    path("profile/interview/", views.career_interview, name="career_interview"),
    path("profile/interview/<int:conversation_id>/", views.career_interview, name="career_interview_conversation"),
    path("profile/interview/extraction/<int:pk>/confirm/", views.career_interview_confirm, name="career_interview_confirm"),
    path("create/", views.cv_create, name="cv_create"),
    path("<int:pk>/builder/", views.cv_builder, name="cv_builder"),
    path("<int:pk>/builder/autosave/", views.cv_builder_autosave, name="cv_builder_autosave"),
    path("<int:pk>/builder/ai/", views.cv_builder_ai, name="cv_builder_ai"),
    path("<int:pk>/builder/ats/", views.cv_builder_ats, name="cv_builder_ats"),
    path("<int:pk>/edit/", views.cv_edit, name="cv_edit"),
    path("<int:pk>/duplicate/", views.cv_duplicate, name="cv_duplicate"),
    path("<int:pk>/delete/", views.cv_delete, name="cv_delete"),
    path("templates/", views.cv_templates, name="cv_templates"),
    path("<int:pk>/preview/", views.cv_preview, name="cv_preview"),
    path("<int:pk>/versions/", views.cv_versions, name="cv_versions"),
    path("<int:pk>/ai/review/", views.cv_ai_review, name="cv_ai_review"),
    path("<int:pk>/ai/ats/", views.cv_ats_analysis, name="cv_ats_analysis"),
    path("<int:pk>/ai/tailor/", views.cv_ai_tailor, name="cv_ai_tailor"),
    path("ai/suggestion/<int:pk>/accept/", views.cv_ai_suggestion_accept, name="cv_ai_suggestion_accept"),
    path("ai/suggestion/<int:pk>/reject/", views.cv_ai_suggestion_reject, name="cv_ai_suggestion_reject"),
    path("<int:pk>/export/pdf/", views.cv_export_pdf, name="cv_export_pdf"),
    path("<int:pk>/export/docx/", views.cv_export_docx, name="cv_export_docx"),
    path("import/", views.cv_import, name="cv_import"),
    path("import/<int:pk>/review/", views.cv_import_review, name="cv_import_review"),
]
