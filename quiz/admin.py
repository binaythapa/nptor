# quiz/admin.py

import csv

from django import forms
from django.contrib import admin, messages
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _

from accounts.models.client import Client

from .models import (
    Domain,
    Category,
    Difficulty,
    Question,
    Choice,
    QuestionFeedback,
    PracticeStat,
    SubscriptionPlan,
    ExamTrack,
    Exam,
    ExamSubscription,
    ExamTrackSubscription,
    Coupon,
    ExamCategoryAllocation,
    UserExam,
    UserAnswer,
    ExamUnlockLog,
    QuestionDiscussion,
    DiscussionVote,
    DiscussionReport,
    QuestionQualitySignal,
    PaymentRecord,
    StudyPlan,
    StudyPlanAnalyticsSnapshot,
    LeaderboardEntry,
)


# ============================================================
# BASIC REGISTRATIONS
# ============================================================

admin.site.register(Client)
admin.site.register(DiscussionVote)
admin.site.register(DiscussionReport)
admin.site.register(QuestionQualitySignal)


# ============================================================
# BULMA FORM WIDGETS
# ============================================================

BULMA_WIDGET_OVERRIDES = {
    models.CharField: {
        "widget": forms.TextInput(
            attrs={
                "class": "input",
            }
        )
    },

    models.TextField: {
        "widget": forms.Textarea(
            attrs={
                "class": "textarea",
                "rows": 3,
            }
        )
    },

    models.IntegerField: {
        "widget": forms.NumberInput(
            attrs={
                "class": "input",
            }
        )
    },

    models.BooleanField: {
        "widget": forms.CheckboxInput(
            attrs={
                "class": "checkbox",
            }
        )
    },

    models.ForeignKey: {
        "widget": forms.Select(
            attrs={
                "class": "select",
            }
        )
    },

    models.ManyToManyField: {
        "widget": forms.SelectMultiple(
            attrs={
                "class": "select",
            }
        )
    },
}


# ============================================================
# EXAM TRACK SUBSCRIPTION
# ============================================================

@admin.register(ExamTrackSubscription)
class ExamTrackSubscriptionAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "track",
        "is_active",
        "is_trial",
        "payment_required",
        "amount",
        "currency",
        "subscribed_at",
        "expires_at",
    )

    list_filter = (
        "is_active",
        "is_trial",
        "payment_required",
        "currency",
        "subscribed_by_admin",
    )

    search_fields = (
        "user__username",
        "user__email",
        "track__title",
        "payment_id",
    )

    readonly_fields = (
        "subscribed_at",
    )

    ordering = (
        "-subscribed_at",
    )

    actions = [
        "deactivate",
    ]

    @admin.action(
        description="Deactivate selected subscriptions"
    )
    def deactivate(
        self,
        request,
        queryset,
    ):
        updated = queryset.update(
            is_active=False
        )

        self.message_user(
            request,
            f"{updated} subscription(s) deactivated.",
            messages.SUCCESS,
        )

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        return False


# ============================================================
# SUBSCRIPTION PLAN
# ============================================================

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "price",
        "duration_days",
        "is_active",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
    )


# ============================================================
# CHOICE INLINE
# ============================================================

class ChoiceInline(admin.TabularInline):

    model = Choice

    extra = 4

    fields = (
        "text",
        "is_correct",
        "order",
    )

    formfield_overrides = {
        models.CharField: {
            "widget": forms.TextInput(
                attrs={
                    "class": "input",
                }
            )
        },

        models.IntegerField: {
            "widget": forms.NumberInput(
                attrs={
                    "class": "input",
                    "style": "width:80px",
                }
            )
        },
    }


# ============================================================
# QUESTION FEEDBACK INLINE
# ============================================================

class QuestionFeedbackInline(
    admin.TabularInline
):

    model = QuestionFeedback

    extra = 0

    readonly_fields = (
        "user",
        "comment",
        "is_answer_incorrect",
        "created_at",
    )

    fields = (
        "user",
        "comment",
        "is_answer_incorrect",
        "status",
        "staff_note",
        "created_at",
    )

    can_delete = False

    show_change_link = True

    formfield_overrides = (
        BULMA_WIDGET_OVERRIDES
    )


# ============================================================
# QUESTION
# ============================================================

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "short_text",
        "question_type",
        "difficulty",
        "category",
        "feedback_count",
        "created_by",
        "updated_by",
        "updated_at",
    )

    list_filter = (
        "question_type",
        "difficulty",
        "category",
    )

    search_fields = (
        "text",
    )

    inlines = [
        ChoiceInline,
        QuestionFeedbackInline,
    ]

    formfield_overrides = (
        BULMA_WIDGET_OVERRIDES
    )

    readonly_fields = (
        "feedback_summary",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "deleted_at",
        "deleted_by",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "category",
                    "text",
                    "question_type",
                    "difficulty",
                )
            },
        ),

        (
            "Explanation",
            {
                "fields": (
                    "explanation",
                ),
            },
        ),

        (
            "Advanced (for non-MCQ)",
            {
                "fields": (
                    "correct_text",
                    "numeric_answer",
                    "numeric_tolerance",
                    "matching_pairs",
                    "ordering_items",
                ),
                "classes": (
                    "collapse",
                ),
            },
        ),

        (
            "Feedback info",
            {
                "fields": (
                    "feedback_summary",
                ),
            },
        ),

        (
            "Audit information",
            {
                "fields": (
                    "created_at",
                    "created_by",
                    "updated_at",
                    "updated_by",
                ),
                "classes": (
                    "collapse",
                ),
            },
        ),

        (
            "Deletion info",
            {
                "fields": (
                    "is_deleted",
                    "deleted_at",
                    "deleted_by",
                ),
                "classes": (
                    "collapse",
                ),
            },
        ),
    )

    def get_queryset(
        self,
        request,
    ):
        return (
            super()
            .get_queryset(request)
            .filter(
                is_deleted=False
            )
        )

    def save_model(
        self,
        request,
        obj,
        form,
        change,
    ):
        if not obj.pk:
            obj.created_by = request.user

        obj.updated_by = request.user

        super().save_model(
            request,
            obj,
            form,
            change,
        )

    def delete_model(
        self,
        request,
        obj,
    ):
        obj.is_deleted = True
        obj.deleted_at = timezone.now()
        obj.deleted_by = request.user

        obj.save(
            update_fields=[
                "is_deleted",
                "deleted_at",
                "deleted_by",
            ]
        )

    def delete_queryset(
        self,
        request,
        queryset,
    ):
        queryset.update(
            is_deleted=True,
            deleted_at=timezone.now(),
            deleted_by=request.user,
        )

    @admin.display(
        description="Question"
    )
    def short_text(
        self,
        obj,
    ):
        if not obj.text:
            return ""

        text = strip_tags(
            obj.text
        )

        return (
            text[:60]
            + (
                "..."
                if len(text) > 60
                else ""
            )
        )

    @admin.display(
        description="Feedbacks"
    )
    def feedback_count(
        self,
        obj,
    ):
        return obj.feedbacks.count()

    @admin.display(
        description="Feedback summary"
    )
    def feedback_summary(
        self,
        obj,
    ):
        count = obj.feedbacks.count()

        if count == 0:
            return (
                "This question has no feedback yet."
            )

        if count == 1:
            return (
                "This question has 1 feedback."
            )

        return (
            f"This question has {count} feedbacks."
        )

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        return request.user.is_superuser


# ============================================================
# EXAM CATEGORY ALLOCATION INLINE
# ============================================================

class ExamCategoryAllocationInline(
    admin.TabularInline
):

    model = ExamCategoryAllocation

    extra = 1

    fields = (
        "category",
        "percentage",
        "fixed_count",
    )

    formfield_overrides = {
        models.IntegerField: {
            "widget": forms.NumberInput(
                attrs={
                    "class": "input",
                    "style": "width:100px",
                }
            )
        },

        models.ForeignKey: {
            "widget": forms.Select(
                attrs={
                    "class": "select",
                }
            )
        },
    }


# ============================================================
# EXAM
# ============================================================

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "question_count",
        "duration_seconds",
        "is_published",
        "level",
        "passing_score",
    )

    inlines = [
        ExamCategoryAllocationInline,
    ]

    filter_horizontal = (
        "categories",
        "prerequisite_exams",
    )

    def save_model(
        self,
        request,
        obj,
        form,
        change,
    ):
        super().save_model(
            request,
            obj,
            form,
            change,
        )

        allocations = (
            obj.allocations.all()
        )

        fixed_total = sum(
            allocation.fixed_count or 0
            for allocation in allocations
        )

        percent_total = sum(
            allocation.percentage
            for allocation in allocations
            if allocation.fixed_count is None
        )

        if fixed_total > obj.question_count:
            raise ValidationError(
                "Fixed allocation exceeds question count."
            )

        if percent_total > 100:
            raise ValidationError(
                "Percentage allocation exceeds 100%."
            )


# ============================================================
# CATEGORY
# ============================================================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "slug",
    )

    formfield_overrides = (
        BULMA_WIDGET_OVERRIDES
    )


# ============================================================
# DOMAIN
# ============================================================

@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "slug",
        "is_active",
    )

    prepopulated_fields = {
        "slug": (
            "name",
        ),
    }


# ============================================================
# DIFFICULTY
# ============================================================

@admin.register(Difficulty)
class DifficultyAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "slug",
    )

    ordering = (
        "name",
    )

    prepopulated_fields = {
        "slug": (
            "name",
        ),
    }


# ============================================================
# USER EXAM CSV EXPORT
# ============================================================

def export_userexams_csv(
    modeladmin,
    request,
    queryset,
):
    fieldnames = [
        "id",
        "user",
        "exam",
        "score",
        "started_at",
        "submitted_at",
    ]

    response = HttpResponse(
        content_type="text/csv"
    )

    response[
        "Content-Disposition"
    ] = (
        'attachment; filename="userexams.csv"'
    )

    writer = csv.writer(
        response
    )

    writer.writerow(
        fieldnames
    )

    for ue in queryset:
        writer.writerow(
            [
                ue.id,
                ue.user.username,
                ue.exam.title,
                ue.score,
                ue.started_at,
                ue.submitted_at,
            ]
        )

    return response


# ============================================================
# USER EXAM
# ============================================================

@admin.register(UserExam)
class UserExamAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user",
        "exam",
        "status",
        "score",
        "started_at",
        "submitted_at",
    )

    list_filter = (
        "status",
        "passed",
        "exam",
    )

    search_fields = (
        "user__username",
        "user__email",
        "exam__title",
    )

    readonly_fields = (
        "user",
        "exam",
        "question_order",
        "started_at",
        "submitted_at",
        "score",
        "passed",
        "status",
        "current_index",
    )

    actions = [
        export_userexams_csv,
    ]

    list_per_page = 50

    def get_queryset(
        self,
        request,
    ):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "user",
                "exam",
            )
        )

    def has_add_permission(
        self,
        request,
    ):
        return request.user.is_superuser

    def delete_queryset(
        self,
        request,
        queryset,
    ):
        count = 0

        with transaction.atomic():

            for obj in queryset:

                try:
                    obj.delete()
                    count += 1

                except Exception as exc:

                    self.message_user(
                        request,
                        _(
                            "Error deleting "
                            "UserExam %(id)s: %(error)s"
                        )
                        % {
                            "id": obj.id,
                            "error": str(exc),
                        },
                        messages.ERROR,
                    )

        if count:
            self.message_user(
                request,
                _(
                    "Successfully deleted "
                    "%(count)d user exam(s)."
                )
                % {
                    "count": count,
                },
                messages.SUCCESS,
            )

    def delete_model(
        self,
        request,
        obj,
    ):
        try:

            obj.delete()

            self.message_user(
                request,
                _(
                    'User exam "%(obj)s" '
                    "was deleted successfully."
                )
                % {
                    "obj": obj,
                },
                messages.SUCCESS,
            )

        except Exception as exc:

            self.message_user(
                request,
                _(
                    "Error deleting "
                    "user exam: %(error)s"
                )
                % {
                    "error": str(exc),
                },
                messages.ERROR,
            )

            raise


# ============================================================
# USER ANSWER
# ============================================================

@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user_exam",
        "question",
        "choice",
        "is_correct",
    )

    readonly_fields = (
        "selections",
        "raw_answer",
    )

    formfield_overrides = (
        BULMA_WIDGET_OVERRIDES
    )


# ============================================================
# QUESTION FEEDBACK
# ============================================================

@admin.register(QuestionFeedback)
class QuestionFeedbackAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "question",
        "user",
        "is_answer_incorrect",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "is_answer_incorrect",
        "created_at",
    )

    search_fields = (
        "question__text",
        "user__username",
        "comment",
    )

    autocomplete_fields = (
        "question",
        "user",
        "user_exam",
    )

    date_hierarchy = "created_at"

    list_per_page = 50

    def get_queryset(
        self,
        request,
    ):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "question",
                "user",
                "user_exam",
            )
        )


# ============================================================
# EXAM UNLOCK LOG
# ============================================================

@admin.register(ExamUnlockLog)
class ExamUnlockLogAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "exam",
        "unlocked_at",
        "source",
    )

    list_filter = (
        "exam",
        "source",
    )


# ============================================================
# EXAM SUBSCRIPTION
# ============================================================

@admin.register(ExamSubscription)
class ExamSubscriptionAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "exam",
        "is_active",
        "subscribed_at",
        "expires_at",
    )

    list_filter = (
        "is_active",
        "payment_required",
    )

    search_fields = (
        "user__username",
        "user__email",
        "exam__title",
    )


# ============================================================
# EXAM TRACK
# ============================================================

@admin.register(ExamTrack)
class ExamTrackAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "subscription_scope",
        "is_active",
        "created_at",
    )

    filter_horizontal = (
        "subscription_plans",
    )

    list_filter = (
        "subscription_scope",
        "is_active",
    )

    search_fields = (
        "title",
        "slug",
    )

    prepopulated_fields = {
        "slug": (
            "title",
        ),
    }


# ============================================================
# COUPON
# ============================================================

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):

    list_display = (
        "code",
        "is_active",
        "percent_off",
        "flat_off",
        "used_count",
        "usage_limit",
        "valid_from",
        "valid_to",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "code",
    )

    readonly_fields = (
        "used_count",
    )


# ============================================================
# EXAM CATEGORY ALLOCATION
# ============================================================

@admin.register(ExamCategoryAllocation)
class ExamCategoryAllocationAdmin(
    admin.ModelAdmin
):

    list_display = (
        "exam",
        "category",
        "percentage",
        "fixed_count",
    )

    list_filter = (
        "exam",
        "category",
    )


# ============================================================
# QUESTION DISCUSSION
# ============================================================

@admin.register(QuestionDiscussion)
class QuestionDiscussionAdmin(
    admin.ModelAdmin
):

    list_display = (
        "id",
        "question",
        "user",
        "discussion_type",
        "is_answer_incorrect",
        "is_staff_verified",
        "created_at",
        "content",
    )

    list_filter = (
        "discussion_type",
        "is_answer_incorrect",
        "is_staff_verified",
        "created_at",
    )

    search_fields = (
        "question__text",
        "content",
        "user__username",
    )

    actions = [
        "mark_verified",
        "disable_question",
    ]

    @admin.action(
        description="Mark selected as verified"
    )
    def mark_verified(
        self,
        request,
        queryset,
    ):
        queryset.update(
            is_staff_verified=True
        )

        self.message_user(
            request,
            "Selected reports marked as verified.",
            messages.SUCCESS,
        )

    @admin.action(
        description="Disable related questions"
    )
    def disable_question(
        self,
        request,
        queryset,
    ):
        question_ids = (
            queryset.values_list(
                "question_id",
                flat=True,
            )
        )

        Question.objects.filter(
            id__in=question_ids
        ).update(
            is_active=False
        )

        self.message_user(
            request,
            "Related questions disabled.",
            messages.SUCCESS,
        )


# ============================================================
# STUDY PLAN
# ============================================================

@admin.register(StudyPlan)
class StudyPlanAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user",
        "plan_type",
        "domain",
        "is_active",
        "is_completed",
        "start_date",
        "extension_days",
    )

    list_filter = (
        "plan_type",
        "is_active",
        "is_completed",
        "domain",
        "start_date",
    )

    search_fields = (
        "user__username",
        "user__email",
    )

    readonly_fields = (
        "created_at",
        "question_count",
        "progress_summary",
        "question_ids_pretty",
    )

    ordering = (
        "-created_at",
    )

    @admin.display(
        description="Total Questions"
    )
    def question_count(
        self,
        obj,
    ):
        return len(
            obj.question_ids or []
        )

    @admin.display(
        description="Progress"
    )
    def progress_summary(
        self,
        obj,
    ):
        total_done = sum(
            (
                obj.daily_progress or {}
            ).values()
        )

        total_needed = (
            obj.total_questions()
        )

        return (
            f"{total_done} / "
            f"{total_needed}"
        )

    @admin.display(
        description="First 20 Question IDs"
    )
    def question_ids_pretty(
        self,
        obj,
    ):
        if not obj.question_ids:
            return "—"

        ids = obj.question_ids[:20]

        suffix = (
            " ..."
            if len(obj.question_ids) > 20
            else ""
        )

        return (
            ", ".join(
                map(str, ids)
            )
            + suffix
        )


# ============================================================
# STUDY PLAN ANALYTICS SNAPSHOT
# ============================================================

@admin.register(
    StudyPlanAnalyticsSnapshot
)
class StudyPlanAnalyticsSnapshotAdmin(
    admin.ModelAdmin
):

    list_display = (
        "plan",
        "date",
        "accuracy",
        "readiness",
        "mastery",
        "predicted_score",
        "pass_probability",
        "volatility",
        "xp",
        "level",
    )

    list_filter = (
        "date",
    )

    ordering = (
        "-date",
    )


# ============================================================
# LEADERBOARD
# ============================================================

@admin.register(LeaderboardEntry)
class LeaderboardEntryAdmin(
    admin.ModelAdmin
):

    list_display = (
        "user",
        "score",
        "rank",
        "updated_at",
    )

    search_fields = (
        "user__username",
        "user__email",
    )

    ordering = (
        "rank",
    )


# ============================================================
# PAYMENT RECORD
# ============================================================

@admin.register(PaymentRecord)
class PaymentRecordAdmin(
    admin.ModelAdmin
):

    list_display = (
        "user",
        "target_name",
        "amount",
        "currency",
        "payment_method",
        "created_by_admin",
        "paid_at",
    )

    list_filter = (
        "payment_method",
        "currency",
        "created_by_admin",
    )

    search_fields = (
        "user__username",
        "user__email",
        "reference_id",
    )

    readonly_fields = (
        "paid_at",
    )


# ============================================================
# RESET MOCK ATTEMPTS
#
# This is a view and should ultimately live in
# quiz/views/admin.py. It is intentionally NOT registered
# as a ModelAdmin action here.
# ============================================================

@admin.action(
    description="Reset selected mock attempts"
)
def reset_mock_attempts_action(
    modeladmin,
    request,
    queryset,
):
    """
    Reset submitted mock attempts.

    This action is intentionally conservative:
    only attempts where passed IS NULL and
    submitted_at IS NOT NULL are deleted.
    """

    count = 0

    with transaction.atomic():

        for user_exam in queryset:

            if (
                user_exam.passed is None
                and user_exam.submitted_at is not None
            ):
                user_exam.delete()
                count += 1

    if count:
        modeladmin.message_user(
            request,
            f"{count} mock attempt(s) reset.",
            messages.SUCCESS,
        )
    else:
        modeladmin.message_user(
            request,
            "No mock attempts found to reset.",
            messages.INFO,
        )


# Add the action to UserExamAdmin.
UserExamAdmin.actions = [
    export_userexams_csv,
    reset_mock_attempts_action,
]