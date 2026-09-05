from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

from quiz.forms import EmailOrUsernameLoginForm

# ============================================================
# QUIZ VIEWS
# ============================================================

from quiz.views.admin import *
from quiz.views.questions import *
from quiz.views.practice_express import *
from quiz.views.auth import *
from quiz.views.admin_subscription_views import *
from quiz.views.notifications import *
from quiz.views.dashboards import *
from quiz.views.student_dashboard import student_dashboard
from quiz.views.learning_hub import learning_hub
from quiz.views.learning_activity import remove_learning_activity
from quiz.views.learning_marketplace import learning_marketplace, learning_domain
from quiz.views.learning_track import learning_track
from quiz.views.learning_shortlist import learning_shortlist_toggle
from quiz.views.exam_detail import exam_detail
from quiz.views.exam_preview import exam_preview
from quiz.views.exam_access import exam_locked
from quiz.views.exam_submission import exam_submit_dashboard
from quiz.views.mock import *
from quiz.views.exams import *
from quiz.views.exams import exam_start as standard_exam_start
from quiz.views.course_exam_start import course_exam_start
from quiz.views.contextual_exam_attempt import (
    exam_take,
    exam_question,
    autosave,
    exam_submit,
    exam_result,
    exam_expired,
    exam_review,
)
from quiz.views.exam_list import *
from quiz.views.study_plan import *
from quiz.views.government_catalog import (
    government_catalog,
    government_country,
    government_body,
    government_program,
)
from quiz.views.government_dashboard import government_program_dashboard

# ============================================================
# PRACTICE
# ============================================================

from quiz.views.practice import (
    practice,
    practice_feedback_ajax,
    discussion_vote,
    practice_answer_ajax,
    practice_next_ajax,
    discussion_submit_ajax,
    practice_skip_ajax
)

# ============================================================
# PAYMENT CHECKOUT
# ============================================================

from payments.views.checkout import (
    track_checkout,
    exam_checkout,
)

app_name = "quiz"

urlpatterns = [
    path("", learning_marketplace, name="exam_list"),
    path(
        "certifications/",
        learning_marketplace,
        {"catalog_vertical": "professional_certification"},
        name="certifications",
    ),
    path(
        "academic-entrance/",
        learning_marketplace,
        {"catalog_vertical": "academic_exam"},
        name="academic_entrance",
    ),
    path("learning/", learning_marketplace, name="learning_marketplace"),
    path("learning/domain/<slug:slug>/", learning_domain, name="learning_domain"),
    path("learning/track/<slug:slug>/", learning_track, name="learning_track"),
    path("learning/shortlist/<str:resource_type>/<int:resource_id>/", learning_shortlist_toggle, name="learning_shortlist_toggle"),

    path("government-exams/", government_catalog, name="government_catalog"),
    path("government-exams/<slug:country_slug>/", government_country, name="government_country"),
    path("government-exams/<slug:country_slug>/<slug:body_slug>/", government_body, name="government_body"),
    path("government-exams/<slug:country_slug>/<slug:body_slug>/<slug:program_slug>/", government_program, name="government_program"),
    path("government-exams/<slug:country_slug>/<slug:body_slug>/<slug:program_slug>/dashboard/", government_program_dashboard, name="government_program_dashboard"),

    path("dashboard/", dashboard_dispatch, name="dashboard"),
    path("dashboard/admin/", admin_dashboard, name="admin_dashboard"),
    path("dashboard/student/", student_dashboard, name="student_dashboard"),
    path("learning/my/", learning_hub, name="learning_hub"),
    path("dashboard/student/activity/<str:resource_type>/<int:resource_id>/remove/", remove_learning_activity, name="remove_learning_activity"),

    path("profile/", profile, name="profile"),
    path("users/", users_list, name="users_list"),

    path("exam/<int:exam_id>/", exam_detail, name="exam_detail"),
    path("exam/<int:exam_id>/preview/", exam_preview, name="exam_preview"),
    path("exam/<int:exam_id>/start/", course_exam_start, name="exam_start"),
    path("exam/<int:exam_id>/locked/", exam_locked, name="exam_locked"),
    path("exam/attempt/<int:user_exam_id>/", exam_take, name="exam_take"),
    path("exam/attempt/<int:user_exam_id>/question/<int:index>/", exam_question, name="exam_question"),
    path("exam/attempt/<int:user_exam_id>/autosave/", autosave, name="exam_autosave"),
    path("exam/attempt/<int:user_exam_id>/submit/", exam_submit, name="exam_submit"),
    path("exam/attempt/<int:user_exam_id>/result/", exam_result, name="exam_result"),
    path("exam/attempt/<int:user_exam_id>/expired/", exam_expired, name="exam_expired"),
    path("exam/attempt/<int:user_exam_id>/review/", exam_review, name="exam_review"),

    path("practice/", practice, name="practice"),
    path("practice/express/", practice_express, name="practice_express"),
    path("practice/express/next/", practice_express_next, name="practice_express_next"),
    path("practice/express/save/", practice_express_save, name="practice_express_save"),
    path("practice/answer/ajax/", practice_answer_ajax, name="practice_answer_ajax"),
    path("practice/discussion/ajax/", discussion_submit_ajax, name="discussion_submit_ajax"),
    path("practice/discussion/vote/", discussion_vote, name="discussion_vote"),
    path("practice/next/ajax/", practice_next_ajax, name="practice_next_ajax"),
    path("practice/feedback/", practice_feedback_ajax, name="practice_feedback_ajax"),

    path("notifications/", notifications_list, name="notifications_list"),
    path("notifications/mark-all/", notifications_mark_all, name="notifications_mark_all"),
    path("notifications/<int:pk>/", notification_read, name="notification_detail"),

    path("track/<int:track_id>/checkout/", track_checkout, name="track_checkout"),
    path("exam/<int:exam_id>/checkout/", exam_checkout, name="exam_checkout"),

    path("dashboard/admin/subscriptions/", subscription_admin_panel, name="subscription_admin_panel"),
    path("dashboard/admin/subscribe/exam/", admin_subscribe_exam, name="admin_subscribe_exam"),
    path("dashboard/admin/revoke/exam/", admin_revoke_exam, name="admin_revoke_exam"),
    path("dashboard/admin/subscribe/track/", admin_subscribe_track, name="admin_subscribe_track"),
    path("dashboard/admin/revoke/track/", admin_revoke_track, name="admin_revoke_track"),
    path("dashboard/admin/update-expiry/exam/", admin_update_exam_expiry, name="admin_update_expiry_exam"),
    path("dashboard/admin/update-expiry/track/", admin_update_track_expiry, name="admin_update_track_expiry"),
    path("dashboard/admin/add-exam-days/", admin_add_exam_days, name="admin_add_exam_days"),
    path("dashboard/admin/add-track-days/", admin_add_track_days, name="admin_add_track_days"),

    path("dashboard/admin/exams/", admin_exam_list, name="admin_exam_list"),
    path("dashboard/admin/exams/add/", admin_exam_create, name="admin_exam_create"),
    path("dashboard/admin/exams/<int:pk>/edit/", admin_exam_update, name="admin_exam_update"),
    path("dashboard/admin/exams/<int:pk>/delete/", admin_exam_delete, name="admin_exam_delete"),
    path("dashboard/admin/tracks/", admin_track_list, name="admin_track_list"),
    path("dashboard/admin/tracks/add/", admin_track_create, name="admin_track_create"),
    path("dashboard/admin/tracks/<int:pk>/edit/", admin_track_update, name="admin_track_update"),
    path("dashboard/admin/tracks/<int:pk>/delete/", admin_track_delete, name="admin_track_delete"),
    path("dashboard/admin/coupons/", admin_coupon_list, name="admin_coupon_list"),
    path("dashboard/admin/coupons/add/", admin_coupon_create, name="admin_coupon_create"),
    path("dashboard/admin/payments/", admin_payment_list, name="admin_payment_list"),
    path("dashboard/admin/manual-payment/", admin_add_manual_payment, name="admin_add_manual_payment"),
    path("dashboard/admin/update-track-pricing-type/", update_track_pricing_type, name="update_track_pricing_type"),
    path("dashboard/admin/exam/toggle-publish/", toggle_exam_publish, name="toggle_exam_publish"),

    path("dashboard/admin/reset-mock/", reset_mock_attempts, name="reset_mock_attempts"),
    path("dashboard/admin/reset-mock/<int:user_id>/<int:exam_id>/", reset_mock_attempts, name="reset_mock_attempts_user"),
    path("dashboard/admin/mock-attempts/", admin_mock_attempts, name="admin_mock_attempts"),
    path("dashboard/admin/mock-attempts/history/", admin_mock_attempt_history, name="admin_mock_attempt_history"),

    path("dashboard/questions/", question_dashboard, name="question_dashboard"),
    path("dashboard/questions/add/", add_question, name="add_question"),
    path("dashboard/questions/<int:pk>/edit/", edit_question, name="edit_question"),
    path("dashboard/questions/<int:pk>/delete/", delete_question, name="delete_question"),
    path("staff/questions/<int:pk>/review/", question_review, name="question_review"),
    path("ajax/question/toggle/", toggle_question_active, name="toggle_question_active"),
    path("ajax/question/delete/", delete_question_ajax, name="delete_question_ajax"),

    path("ajax/discussion/verify/", verify_discussion, name="verify_discussion"),
    path("ajax/discussion/pin/", pin_discussion, name="pin_discussion"),
    path("ajax/discussion/delete/", delete_discussion, name="delete_discussion"),
    path("review/discussion/resolve/", resolve_discussion, name="resolve_discussion"),
    path("ajax/categories-by-domain/", ajax_categories_by_domain, name="ajax_categories_by_domain"),

    path("study-plan/", study_plan_dashboard, name="study_plan_dashboard"),
    path("study-plan/practice/", study_plan_practice, name="study_plan_practice"),
    path("study-plan/create/", create_study_plan, name="create_study_plan"),
    path("study-plan/clone/<int:plan_id>/", clone_study_plan, name="clone_study_plan"),
    path("study-plan/adaptive/", create_adaptive_plan, name="create_adaptive_plan"),
    path("study-plan/leaderboard/", study_plan_leaderboard, name="study_plan_leaderboard"),
    path("study-plan/completed/<int:plan_id>/", study_plan_completed, name="study_plan_completed"),
    path("study-plan/history/", study_plan_history, name="study_plan_history"),
    path("study-plan/<int:plan_id>/", study_plan_detail, name="study_plan_detail"),
    path("practice/skip/ajax/", practice_skip_ajax, name="practice_skip_ajax"),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
