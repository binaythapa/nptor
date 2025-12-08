# quiz/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import viewsss
from .forms import EmailOrUsernameLoginForm
from objective_exam_all_types.quiz.viewsss import *
from django.conf.urls.static import static

app_name = "quiz"

urlpatterns = [

    # ============================================================
    # AUTHENTICATION
    # ============================================================
    
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
            authentication_form=EmailOrUsernameLoginForm
        ),
        name="login"
    ),

    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # Password Reset Flow
    path("password-reset/",auth_views.PasswordResetView.as_view(template_name="registration/password_reset.html"),name="password_reset"),

    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done"
    ),

    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html"
        ),
        name="password_reset_confirm"
    ),

    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete"
    ),

    # Registration
    path("register/", viewsss.register, name="register"),

    # ============================================================
    # DASHBOARD
    # ============================================================
    path("", viewsss.exam_list, name="exam_list"),

    path("dashboard/", viewsss.dashboard_dispatch, name="dashboard"),

    # Admin + Student dashboards
    path("dashboard/admin/", viewsss.admin_dashboard, name="admin_dashboard"),
    path("dashboard/student/", viewsss.student_dashboard, name="student_dashboard"),

    # ============================================================
    # USER
    # ============================================================
    path("profile/", viewsss.profile, name="profile"),
    path("users/", viewsss.users_list, name="users_list"),

    # ============================================================
    # EXAMS
    # ============================================================
    path("exam/<int:exam_id>/start/", viewsss.exam_start, name="exam_start"),
    path("exam/<int:user_exam_id>/take/", viewsss.exam_take, name="exam_take"),
    path("exam/<int:user_exam_id>/question/<int:index>/", viewsss.exam_question, name="exam_question"),
    path("exam/<int:user_exam_id>/autosave/", viewsss.autosave, name="autosave"),
    path("exam/<int:user_exam_id>/submit/", viewsss.exam_submit, name="exam_submit"),
    path("exam/<int:user_exam_id>/result/", viewsss.exam_result, name="exam_result"),

    # ============================================================
    # NOTIFICATIONS
    # ============================================================
    path("notifications/", viewsss.notifications_list, name="notifications_list"),
    path("notifications/mark-all/", viewsss.notifications_mark_all, name="notifications_mark_all"),
    path("notifications/<int:pk>/", viewsss.notification_read, name="notification_detail"),

    # ============================================================
    # AJAX API
    # ============================================================
    path("api/recent_attempts/", viewsss.recent_attempts_api, name="recent_attempts_api"),
    path('customerregister/',CustomerRegisterView.as_view(), name='customer-register'),
]
urlpatterns += static(settings.STATIC_URL, document_root= settings.STATIC_ROOT)
urlpatterns +=  static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
