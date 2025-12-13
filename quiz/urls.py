# quiz/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views

from . import views
from .forms import EmailOrUsernameLoginForm
from .views import CustomerRegisterView

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
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset.html"
        ),
        name="password_reset"
    ),

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
    path("register/", views.register, name="register"),

    # ============================================================
    # DASHBOARD
    # ============================================================
    path("", views.exam_list, name="exam_list"),
    path("dashboard/", views.dashboard_dispatch, name="dashboard"),

    path("dashboard/admin/", views.admin_dashboard, name="admin_dashboard"),
    path("dashboard/student/", views.student_dashboard, name="student_dashboard"),

    # ============================================================
    # USER
    # ============================================================
    path("profile/", views.profile, name="profile"),
    path("users/", views.users_list, name="users_list"),

    # ============================================================
    # EXAMS
    # ============================================================
    path("exam/<int:exam_id>/start/", views.exam_start, name="exam_start"),
    path("exam/<int:user_exam_id>/take/", views.exam_take, name="exam_take"),
    path(
        "exam/<int:user_exam_id>/question/<int:index>/",
        views.exam_question,
        name="exam_question"
    ),
    path("exam/<int:user_exam_id>/autosave/", views.autosave, name="autosave"),
    path("exam/<int:user_exam_id>/submit/", views.exam_submit, name="exam_submit"),
    path("exam/<int:user_exam_id>/result/", views.exam_result, name="exam_result"),

    # ============================================================
    # NOTIFICATIONS
    # ============================================================
    path("notifications/", views.notifications_list, name="notifications_list"),
    path("notifications/mark-all/", views.notifications_mark_all, name="notifications_mark_all"),
    path("notifications/<int:pk>/", views.notification_read, name="notification_detail"),

    # ============================================================
    # AJAX / API
    # ============================================================
    path("api/recent_attempts/", views.recent_attempts_api, name="recent_attempts_api"),

    # ============================================================
    # CUSTOMER
    # ============================================================
    path(
        "customerregister/",
        CustomerRegisterView.as_view(),
        name="customer-register"
    ),


    # PUBLIC
    path("practice/", views.practice, name="practice"),
     path(
        "practice/express/",
        views.practice_express,
        name="practice_express"
    ),

    path(
        "practice/express/next/",
        views.practice_express_next,
        name="practice_express_next"
    ),

    path(
        "practice/express/save/",
        views.practice_express_save,
        name="practice_express_save"
    ),

]
