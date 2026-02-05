from django.urls import path
from django.contrib.auth import views as auth_views

from quiz.forms import EmailOrUsernameLoginForm
from quiz.views.admin import *
from django.conf import settings
from django.conf.urls.static import static

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
from quiz.views.student_dashboards import *
from quiz.views.mock import *
from quiz.views.exams import *



from django.urls import path
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

# ================================
# IMPORT QUIZ VIEWS
# ================================
from quiz.views.questions import *
from quiz.views.views import *
from quiz.views.student import *
from quiz.views.subscription import *
from quiz.views.admin_subscriptions import *
from quiz.views.notifications import *
from quiz.views.student_dashboards import *
from quiz.views.mock import *
from quiz.views.exams import *
from quiz.views.admin import *


app_name = "quiz"

urlpatterns = [

    # ============================================================
    # 🔁 REDIRECT OLD AUTH URLS → ACCOUNTS (BACKWARD COMPATIBILITY)
    # ============================================================
    path(
        "login/",
        RedirectView.as_view(
            pattern_name="accounts:request-login-otp",
            permanent=False,
        ),
    ),
    path(
        "password-reset/",
        RedirectView.as_view(
            pattern_name="accounts:password-reset-request",
            permanent=False,
        ),
    ),

    # ============================================================
    # REGISTRATION (OPTIONAL – KEEP IF YOU USE IT)
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

    # ============================================================
    # PRACTICE
    # ============================================================
    path("practice/", practice, name="practice"),
    path("practice/express/", practice_express, name="practice_express"),
    path("practice/express/next/", practice_express_next, name="practice_express_next"),
    path("practice/express/save/", practice_express_save, name="practice_express_save"),
    path("practice/answer/ajax/", practice_answer_ajax, name="practice_answer_ajax"),
    path("practice/feedback/", practice_feedback_ajax, name="practice_feedback_ajax"),
    path(
        "practice/discussion/ajax/",
        discussion_submit_ajax,
        name="discussion_submit_ajax",
    ),
    path("practice/discussion/vote/", discussion_vote, name="discussion_vote"),
    path("practice/next/ajax/", practice_next_ajax, name="practice_next_ajax"),

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
    # SUBSCRIPTIONS
    # ============================================================
    path("subscriptions/history/", subscription_history, name="subscription_history"),
    path("track/<int:track_id>/checkout/", track_checkout, name="track_checkout"),
    path("subscribe/track/<int:track_id>/", subscribe_track, name="subscribe_track"),
    path("subscribe/exam/<int:exam_id>/", subscribe_exam, name="subscribe_exam"),

    # ============================================================
    # ADMIN – SUBSCRIPTIONS
    # ============================================================
    path(
        "dashboard/admin/subscriptions/",
        subscription_admin_panel,
        name="subscription_admin_panel",
    ),
    path("dashboard/admin/toggle-track/", toggle_track_status, name="toggle_track_status"),
    path("dashboard/admin/toggle-coupon/", toggle_coupon_status, name="toggle_coupon_status"),
    path("dashboard/admin/create-coupon/", create_coupon_ajax, name="create_coupon_ajax"),
    path(
        "dashboard/admin/update-track-pricing-type/",
        update_track_pricing_type,
        name="update_track_pricing_type",
    ),

    # ============================================================
    # ADMIN – EXAMS & TRACKS
    # ============================================================
    path("dashboard/admin/exams/", admin_exam_list, name="admin_exam_list"),
    path("dashboard/admin/exams/add/", admin_exam_create, name="admin_exam_create"),
    path("dashboard/admin/exams/<int:pk>/edit/", admin_exam_update, name="admin_exam_update"),
    path("dashboard/admin/exams/<int:pk>/delete/", admin_exam_delete, name="admin_exam_delete"),

    path("dashboard/admin/tracks/", admin_track_list, name="admin_track_list"),
    path("dashboard/admin/tracks/add/", admin_track_create, name="admin_track_create"),
    path("dashboard/admin/tracks/<int:pk>/edit/", admin_track_update, name="admin_track_update"),
    path("dashboard/admin/tracks/<int:pk>/delete/", admin_track_delete, name="admin_track_delete"),

    # ============================================================
    # QUESTIONS / DISCUSSIONS / ADMIN UTILITIES
    # ============================================================
    path("dashboard/questions/", question_dashboard, name="question_dashboard"),
    path("dashboard/questions/add/", add_question, name="add_question"),
    path("dashboard/questions/<int:pk>/edit/", edit_question, name="edit_question"),
    path("dashboard/questions/<int:pk>/delete/", delete_question, name="delete_question"),

    path("ajax/categories-by-domain/", ajax_categories_by_domain, name="ajax_categories_by_domain"),
    path("ajax/question/toggle/", toggle_question_active, name="toggle_question_active"),
    path("ajax/question/delete/", delete_question_ajax, name="delete_question_ajax"),
    path("ajax/discussion/verify/", verify_discussion, name="verify_discussion"),
    path("ajax/discussion/pin/", pin_discussion, name="pin_discussion"),
    path("ajax/discussion/delete/", delete_discussion, name="delete_discussion"),

    path("log-enrollment-lead/", log_enrollment_lead, name="log_enrollment_lead"),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
