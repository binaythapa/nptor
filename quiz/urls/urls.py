from django.urls import path
from django.contrib.auth import views as auth_views

from quiz.forms import EmailOrUsernameLoginForm
from quiz.views.admin import *

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
from quiz.views.mock import *
from quiz.views.exams import *






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
        "dashboard/admin/tracks/add/",
        admin_track_create,
        name="admin_track_create"
    ),

    
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


# ================= ADMIN – SUBSCRIPTION MANAGEMENT =================

path(
    "dashboard/admin/exams/",
    admin_exam_list,
    name="admin_exam_list",
),
path(
    "dashboard/admin/exams/add/",
    admin_exam_create,
    name="admin_exam_create",
),
path(
    "dashboard/admin/exams/<int:pk>/edit/",
    admin_exam_update,
    name="admin_exam_update",
),
path(
    "dashboard/admin/exams/<int:pk>/delete/",
    admin_exam_delete,
    name="admin_exam_delete",
),

path(
    "dashboard/admin/tracks/",
    admin_track_list,
    name="admin_track_list",
),
path(
    "dashboard/admin/tracks/add/",
    admin_track_create,
    name="admin_track_create",
),
path(
    "dashboard/admin/tracks/<int:pk>/edit/",
    admin_track_update,
    name="admin_track_update",
),


path(
    "dashboard/admin/tracks/<int:pk>/delete/",
    admin_track_delete,
    name="admin_track_delete",
),

path(
    "dashboard/admin/coupons/",
    admin_coupon_list,
    name="admin_coupon_list",
),
path(
    "dashboard/admin/coupons/add/",
    admin_coupon_create,
    name="admin_coupon_create",
),

path(
    "dashboard/admin/payments/",
    admin_payment_list,
    name="admin_payment_list",
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


    path(
    "log-enrollment-lead/",
    log_enrollment_lead,
    name="log_enrollment_lead"
),

    # Question Review

    path("staff/questions/<int:pk>/review/",
     question_review,
     name="question_review"),

    path("ajax/question/toggle/",
     toggle_question_active,
     name="toggle_question_active"),

    path("ajax/question/delete/",
     delete_question_ajax,
     name="delete_question_ajax"),

    path("ajax/discussion/verify/",
     verify_discussion,
     name="verify_discussion"),

    path("ajax/discussion/pin/",
     pin_discussion,
     name="pin_discussion"),

    path("ajax/discussion/delete/",
     delete_discussion,
     name="delete_discussion"),

     path(
    "review/discussion/resolve/",
    resolve_discussion,
    name="resolve_discussion"),

    path(
    "dashboard/admin/exam/toggle-publish/",
    toggle_exam_publish,
    name="toggle_exam_publish",
),



# ---------------- ADMIN MOCK RESET ----------------
    path(
    "dashboard/admin/reset-mock/",
    reset_mock_attempts,
    name="reset_mock_attempts",
),
    path(
    "dashboard/admin/mock-attempts/",
    admin_mock_attempts,
    name="admin_mock_attempts",
),


path(
    "dashboard/admin/mock-attempts/history/",
    admin_mock_attempt_history,
    name="admin_mock_attempt_history",
),

########PAYMENT#######

path(
    "dashboard/admin/manual-payment/",
    admin_add_manual_payment,
    name="admin_add_manual_payment",
),
    

]
