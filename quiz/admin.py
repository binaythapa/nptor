# quiz/admin.py
from django.contrib import admin
from django import forms
from django.db import models
from django.forms import widgets
from .models import *
from django.contrib import admin
from .models import Exam, ExamTrack
import csv
from django.http import HttpResponse
from django.contrib import admin
from .models import ExamTrack
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from quiz.models import User, Exam, UserExam



admin.site.register(Client)
admin.site.register(ExamTrackSubscription)

admin.site.register(DiscussionVote)
admin.site.register(DiscussionReport)
admin.site.register(QuestionQualitySignal)



class ExamTrackSubscriptionAdmin(admin.ModelAdmin):
    actions = ["deactivate"]

    def deactivate(self, request, queryset):
        queryset.update(is_active=False)

    deactivate.short_description = "Deactivate subscription"

    def has_delete_permission(self, request, obj=None):
        return False


# ----------------------------
# Helper: give admin form widgets Bulma-friendly classes
# ----------------------------
BULMA_WIDGET_OVERRIDES = {
    models.CharField: {'widget': forms.TextInput(attrs={'class': 'input'})},
    models.TextField: {'widget': forms.Textarea(attrs={'class': 'textarea', 'rows': 3})},
    models.IntegerField: {'widget': forms.NumberInput(attrs={'class': 'input'})},
    models.BooleanField: {'widget': forms.CheckboxInput(attrs={'class': 'checkbox'})},
    models.ForeignKey: {'widget': forms.Select(attrs={'class': 'select'})},
    models.ManyToManyField: {'widget': forms.SelectMultiple(attrs={'class': 'select'})},
}


# ----------------------------
# Notification Admin
# ----------------------------
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at')
    search_fields = ('title', 'message')
    filter_horizontal = ('users',)
    formfield_overrides = BULMA_WIDGET_OVERRIDES


# ----------------------------
# Choice inline for Questions
# ----------------------------
class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4
    fields = ('text', 'is_correct', 'order')
    formfield_overrides = {
        models.CharField: {'widget': forms.TextInput(attrs={'class': 'input'})},
        models.IntegerField: {
            'widget': forms.NumberInput(attrs={'class': 'input', 'style': 'width:80px'})
        },
    }


# ----------------------------
# QuestionFeedback inline (on Question page)
# ----------------------------
class QuestionFeedbackInline(admin.TabularInline):
    model = QuestionFeedback
    extra = 0
    readonly_fields = ('user', 'comment', 'is_answer_incorrect', 'created_at')
    fields = ('user', 'comment', 'is_answer_incorrect', 'status', 'staff_note', 'created_at')
    can_delete = False
    show_change_link = True
    formfield_overrides = BULMA_WIDGET_OVERRIDES


# ----------------------------
# Question admin
# ----------------------------


# ----------------------------
# Question admin
# ----------------------------
from django.contrib import admin
from django.utils import timezone

from .models import Question
# ChoiceInline and QuestionFeedbackInline are assumed to be defined ABOVE


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):

    # ================= LIST VIEW =================
    list_display = (
        'id',
        'short_text',
        'question_type',
        'difficulty',
        'category',
        'feedback_count',
        'created_by',
        'updated_by',
        'updated_at',
    )

    list_filter = ('question_type', 'difficulty', 'category')
    search_fields = ('text',)

    inlines = [ChoiceInline, QuestionFeedbackInline]
    formfield_overrides = BULMA_WIDGET_OVERRIDES

    # ================= READ ONLY =================
    readonly_fields = (
        'feedback_summary',
        'created_at',
        'updated_at',
        'created_by',
        'updated_by',
        'deleted_at',
        'deleted_by',
    )

    # ================= FIELDSETS =================
    fieldsets = (
        (None, {
            'fields': ('category', 'text', 'question_type', 'difficulty')
        }),
        ('Explanation', {
            'fields': ('explanation',),
        }),
        ('Advanced (for non-MCQ)', {
            'fields': (
                'correct_text',
                'numeric_answer',
                'numeric_tolerance',
                'matching_pairs',
                'ordering_items',
            ),
            'classes': ('collapse',)
        }),
        ('Feedback info', {
            'fields': ('feedback_summary',),
        }),
        ('Audit information', {
            'fields': (
                'created_at',
                'created_by',
                'updated_at',
                'updated_by',
            ),
            'classes': ('collapse',),
        }),
        ('Deletion info', {
            'fields': (
                'is_deleted',
                'deleted_at',
                'deleted_by',
            ),
            'classes': ('collapse',),
        }),
    )

    # ================= QUERYSET =================
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(is_deleted=False)

    # ================= SAVE =================
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    # ================= SOFT DELETE =================
    def delete_model(self, request, obj):
        obj.is_deleted = True
        obj.deleted_at = timezone.now()
        obj.deleted_by = request.user
        obj.save()

    def delete_queryset(self, request, queryset):
        queryset.update(
            is_deleted=True,
            deleted_at=timezone.now(),
            deleted_by=request.user
        )

    # ================= HELPERS =================
    def short_text(self, obj):
        return obj.text[:60] + ('...' if len(obj.text) > 60 else '') if obj.text else ''
    short_text.short_description = "Question"

    def feedback_count(self, obj):
        return obj.feedbacks.count()
    feedback_count.short_description = "Feedbacks"

    def feedback_summary(self, obj):
        count = obj.feedbacks.count()
        if count == 0:
            return "This question has no feedback yet."
        elif count == 1:
            return "This question has 1 feedback."
        return f"This question has {count} feedbacks."
    feedback_summary.short_description = "Feedback summary"


    def has_delete_permission(self, request, obj=None):
        """
        Allow delete ONLY for superusers
        """
        return request.user.is_superuser






# ----------------------------
# ExamCategoryAllocation inline
# ----------------------------
class ExamCategoryAllocationInline(admin.TabularInline):
    model = ExamCategoryAllocation
    extra = 1
    fields = ('category', 'percentage', 'fixed_count')
    formfield_overrides = {
        models.IntegerField: {
            'widget': forms.NumberInput(attrs={'class': 'input', 'style': 'width:100px'})
        },
        models.ForeignKey: {'widget': forms.Select(attrs={'class': 'select'})},
    }


# ================================
# Exam Admin (UPDATED – SAFE)
# ================================
@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'question_count', 'duration_seconds',
        'is_published', 'level', 'passing_score'
    )

    inlines = [ExamCategoryAllocationInline]
    filter_horizontal = ('categories', 'prerequisite_exams')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        allocations = obj.allocations.all()
        fixed_total = sum(a.fixed_count or 0 for a in allocations)
        percent_total = sum(
            a.percentage for a in allocations if a.fixed_count is None
        )

        if fixed_total > obj.question_count:
            raise ValidationError(
                "Fixed allocation exceeds question count."
            )

        if percent_total > 100:
            raise ValidationError(
                "Percentage allocation exceeds 100%."
            )

# ----------------------------
# Category admin
# ----------------------------
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    formfield_overrides = BULMA_WIDGET_OVERRIDES


# ----------------------------
# CSV export for UserExam
# ----------------------------
def export_userexams_csv(modeladmin, request, queryset):
    fieldnames = ['id', 'user', 'exam', 'score', 'started_at', 'submitted_at']
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="userexams.csv"'
    writer = csv.writer(response)
    writer.writerow(fieldnames)
    for ue in queryset:
        writer.writerow([ue.id, ue.user.username, ue.exam.title, ue.score, ue.started_at, ue.submitted_at])
    return response


export_userexams_csv.short_description = "Export selected user exams to CSV"





@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_exam', 'question', 'choice', 'is_correct')
    readonly_fields = ('selections', 'raw_answer')
    formfield_overrides = BULMA_WIDGET_OVERRIDES




# =====================================================
# DOMAIN
# =====================================================
@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active')
    prepopulated_fields = {'slug': ('name',)}


# =====================================================
# DIFFICULTY  ✅ NEW & IMPORTANT
# =====================================================
@admin.register(Difficulty)
class DifficultyAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    ordering = ('name',)
    prepopulated_fields = {'slug': ('name',)}



#####################EXAM################
from django.contrib import admin
from django.db import transaction
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

@admin.register(UserExam)
class UserExamAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'exam', 'status', 'score', 'started_at', 'submitted_at')
    list_filter = ('status', 'passed', 'exam')
    search_fields = ('user__username', 'user__email', 'exam__title')
    readonly_fields = (
        'user', 'exam', 'question_order',
        'started_at', 'submitted_at',
        'score', 'passed', 'status',
        'current_index'
    )
    actions = [export_userexams_csv]
    list_per_page = 50

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'exam')

    def has_add_permission(self, request):
        return request.user.is_superuser

    def delete_queryset(self, request, queryset):
        """
        Handle bulk deletion to avoid constraint violations
        """
        count = 0
        with transaction.atomic():
            for obj in queryset:
                try:
                    obj.delete()
                    count += 1
                except Exception as e:
                    self.message_user(
                        request,
                        _('Error deleting UserExam %(id)s: %(error)s') % {
                            'id': obj.id,
                            'error': str(e)
                        },
                        messages.ERROR
                    )
        
        if count > 0:
            self.message_user(
                request,
                _('Successfully deleted %(count)d user exam(s).') % {'count': count},
                messages.SUCCESS
            )

    def delete_model(self, request, obj):
        """
        Handle single object deletion from admin
        """
        try:
            obj.delete()
            self.message_user(
                request,
                _('User exam "%(obj)s" was deleted successfully.') % {'obj': obj},
                messages.SUCCESS
            )
        except Exception as e:
            self.message_user(
                request,
                _('Error deleting user exam: %(error)s') % {'error': str(e)},
                messages.ERROR
            )
            raise



@admin.register(QuestionFeedback)
class QuestionFeedbackAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'question', 'user',
        'is_answer_incorrect', 'status', 'created_at'
    )
    list_filter = ('status', 'is_answer_incorrect', 'created_at')
    search_fields = ('question__text', 'user__username', 'comment')
    autocomplete_fields = ('question', 'user', 'user_exam')
    date_hierarchy = 'created_at'
    list_per_page = 50
    date_hierarchy = None


    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('question', 'user', 'user_exam')
    

@admin.register(ExamUnlockLog)
class ExamUnlockLogAdmin(admin.ModelAdmin):
    list_display = ("user", "exam", "unlocked_at", "source")
    list_filter = ("exam", "source")

@admin.register(ExamSubscription)
class ExamSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "exam", "is_active", "subscribed_at", "expires_at")
    list_filter = ("is_active", "payment_required")
    search_fields = ("user__username", "exam__title")



@admin.register(ExamTrack)
class ExamTrackAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "subscription_scope",
        "is_active",
        "created_at",
    )
    list_filter = (
        "subscription_scope",
        "is_active",
    )
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}

# =====================================================
# COUPONS (NEW)
# =====================================================

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
    list_filter = ("is_active",)
    search_fields = ("code",)
    readonly_fields = ("used_count",)



@staff_member_required
def reset_mock_attempts(request, user_id, exam_id):
    """
    Admin-only:
    Reset ALL mock attempts for a user on a given exam
    (mock = passed IS NULL)
    """

    user = get_object_or_404(User, id=user_id)
    exam = get_object_or_404(Exam, id=exam_id)

    deleted_count, _ = UserExam.objects.filter(
        user=user,
        exam=exam,
        passed__isnull=True,
        submitted_at__isnull=False
    ).delete()

    if deleted_count:
        messages.success(
            request,
            f"Mock attempts reset for {user.username} on '{exam.title}'."
        )
    else:
        messages.info(
            request,
            "No mock attempts found to reset."
        )

    return redirect("quiz:admin_dashboard")


from django.contrib import admin
from .models import QuestionDiscussion, Question


@admin.register(QuestionDiscussion)
class QuestionDiscussionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "question",
        "user",
        "discussion_type",
        "is_answer_incorrect",
        "is_staff_verified",
        "created_at",
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

    def mark_verified(self, request, queryset):
        queryset.update(is_staff_verified=True)
        self.message_user(request, "Selected reports marked as verified.")

    mark_verified.short_description = "✅ Mark selected as verified"

    def disable_question(self, request, queryset):
        question_ids = queryset.values_list("question_id", flat=True)
        Question.objects.filter(id__in=question_ids).update(is_active=False)
        self.message_user(request, "🚫 Related questions disabled.")

    disable_question.short_description = "🚫 Disable related questions"



    ##################################################################################

@admin.register(ContactMethod)
class ContactMethodAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")


@admin.register(EnrollmentLead)
class EnrollmentLeadAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "target_name",
        "contact_method",
        "is_converted",
        "created_at",
    )
    list_filter = ("contact_method", "is_converted", "created_at")
    search_fields = ("user__username",)

    def target_name(self, obj):
        return obj.target_name()


@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "target_name",
        "amount",
        "currency",
        "payment_method",
        "paid_at",
    )
    list_filter = ("payment_method", "currency")
    search_fields = ("user__username", "reference_id")

    def target_name(self, obj):
        return obj.target_name()

