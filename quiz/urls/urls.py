from django.urls import path
from django.contrib.auth import views as auth_views

from quiz.forms import EmailOrUsernameLoginForm
from quiz.views.admin import reset_mock_attempts

# ================================
# IMPORT VIEWS (FROM views.py)
# ================================
from quiz.views.questions import *
from quiz.views.views import *
from quiz.views.student import *
from quiz.views.auth import *
from quiz.views.subscription import *
from quiz.views.admin_subscriptions import *
from quiz.views.notifications import *
from quiz.views.dashboards import *
from quiz.views.exams import *
from quiz.views.admin import reset_mock_attempts





app_name = "quiz"

urlpatterns = [

    # ============================================================
    # AUTH
    # ============================================================
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
            authentication_form=EmailOrUsernameLoginForm,
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # Password reset
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset.html"
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),

    # ============================================================
    # REGISTRATION
    # ============================================================
    path("register/", register, name="register"),
    path(
        "customerregister/",
        CustomerRegisterView.as_view(),
        name="customer_register",
    ),

    # ============================================================
    # DASHBOARD
    # ============================================================
    path("", exam_list, name="exam_list"),
    path("dashboard/", dashboard_dispatch, name="dashboard"),
    path("dashboard/admin/", admin_dashboard, name="admin_dashboard"),
    path("dashboard/student/", student_dashboard, name="student_dashboard"),

    # ============================================================
    # USER
    # ============================================================
    path("profile/", profile, name="profile"),
    path("users/", users_list, name="users_list"),

    # ============================================================
    # EXAMS
    # ============================================================
    path("exam/<int:exam_id>/start/", exam_start, name="exam_start"),
    path("exam/<int:exam_id>/resume/", exam_resume, name="exam_resume"),
    path("exam/<int:exam_id>/locked/", exam_locked, name="exam_locked"),

    path("exam/attempt/<int:user_exam_id>/", exam_take, name="exam_take"),
    path(
        "exam/attempt/<int:user_exam_id>/question/<int:index>/",
        exam_question,
        name="exam_question",
    ),
    path(
        "exam/attempt/<int:user_exam_id>/autosave/",
        autosave,
        name="exam_autosave",
    ),
    path(
        "exam/attempt/<int:user_exam_id>/submit/",
        exam_submit,
        name="exam_submit",
    ),
    path(
        "exam/attempt/<int:user_exam_id>/result/",
        exam_result,
        name="exam_result",
    ),
    path(
        "exam/attempt/<int:user_exam_id>/expired/",
        exam_expired,
        name="exam_expired",
    ),

    path("exam/<int:exam_id>/mock/", mock_exam_start, name="mock_exam_start"),

    path("practice/feedback/", practice_feedback_ajax, name="practice_feedback_ajax"),


    # ============================================================
    # NOTIFICATIONS
    # ============================================================
    path("notifications/", notifications_list, name="notifications_list"),
    path(
        "notifications/mark-all/",
        notifications_mark_all,
        name="notifications_mark_all",
    ),
    path(
        "notifications/<int:pk>/",
        notification_read,
        name="notification_detail",
    ),

    # ============================================================
    # PRACTICE
    # ============================================================
    path("practice/", practice, name="practice"),
    path("practice/express/", practice_express, name="practice_express"),
    path(
        "practice/express/next/",
        practice_express_next,
        name="practice_express_next",
    ),
    path(
        "practice/express/save/",
        practice_express_save,
        name="practice_express_save",
    ),

    path("practice/answer/ajax/", practice_answer_ajax, name="practice_answer_ajax"),
    path("practice/discussion/ajax/",discussion_submit_ajax, name="discussion_submit_ajax"),

    path(
    "practice/discussion/vote/",
    discussion_vote,
    name="discussion_vote"
    ),

    path(
    "practice/next/ajax/",
    practice_next_ajax,
    name="practice_next_ajax"
),



    # ============================================================
    # SUBSCRIPTIONS
    # ============================================================
    path(
        "subscribe/track/<int:track_id>/",
        subscribe_track,
        name="subscribe_track",
    ),
    path(
        "subscribe/exam/<int:exam_id>/",
        subscribe_exam,
        name="subscribe_exam",
    ),
    path(
        "dashboard/admin/subscriptions/",
        subscription_admin_panel,
        name="subscription_admin_panel",
    ),
    path(
        "dashboard/admin/toggle-track/",
        toggle_track_status,
        name="toggle_track_status",
    ),
    path(
        "dashboard/admin/toggle-coupon/",
        toggle_coupon_status,
        name="toggle_coupon_status",
    ),
    path(
        "dashboard/admin/create-coupon/",
        create_coupon_ajax,
        name="create_coupon_ajax",
    ),
    
    path(
        "dashboard/admin/update-track-pricing-type/",
        update_track_pricing_type,
        name="update_track_pricing_type",
    ),
    path(
    "ajax/categories-by-domain/",
    ajax_categories_by_domain,
    name="ajax_categories_by_domain",
),

path(
    "dashboard/admin/reset-mock/<int:user_id>/<int:exam_id>/",
    reset_mock_attempts,
    name="reset_mock_attempts",
),



# ============================================================
# ADMIN – MANUAL SUBSCRIPTIONS
# ============================================================
path(
    "dashboard/admin/subscribe/exam/",
    admin_subscribe_exam,
    name="admin_subscribe_exam",
),
path(
    "dashboard/admin/revoke/exam/",
    admin_revoke_exam,
    name="admin_revoke_exam",
),
path(
    "dashboard/admin/subscribe/track/",
    admin_subscribe_track,
    name="admin_subscribe_track",
),
path(
    "dashboard/admin/revoke/track/",
    admin_revoke_track,
    name="admin_revoke_track",
),


path(
    "dashboard/admin/update-expiry/exam/",
    admin_update_exam_expiry,
    name="admin_update_exam_expiry",
),
path(
    "dashboard/admin/update-expiry/track/",
    admin_update_track_expiry,
    name="admin_update_track_expiry",
),


path(
    "dashboard/admin/add-exam-days/",
    admin_add_exam_days,
    name="admin_add_exam_days",
),

path(
    "dashboard/admin/add-track-days/",
    admin_add_track_days,
    name="admin_add_track_days",
),




# ---------------- ADMIN MOCK RESET ----------------
path(
    "dashboard/admin/reset-mock/",
    reset_mock_attempts,
    name="reset_mock_attempts",
),


# ================= QUESTIONS DASHBOARD =================
    path(
        "dashboard/questions/",
        question_dashboard,
        name="question_dashboard",
    ),
    path(
        "dashboard/questions/add/",
        add_question,
        name="add_question",
    ),
    path(
        "dashboard/questions/<int:pk>/edit/",
        edit_question,
        name="edit_question",
    ),
    path(
        "dashboard/questions/<int:pk>/delete/",
        delete_question,
        name="delete_question",
    ),

]
