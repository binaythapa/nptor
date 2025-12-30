# quiz/admin.py
from django.contrib import admin
from django import forms
from django.db import models
from django.forms import widgets
from .models import *

import csv
from django.http import HttpResponse

admin.site.register(Client)

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
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'short_text', 'question_type', 'difficulty', 'category', 'feedback_count')
    inlines = [ChoiceInline, QuestionFeedbackInline]
    list_filter = ('question_type', 'difficulty', 'category')
    search_fields = ('text',)
    formfield_overrides = BULMA_WIDGET_OVERRIDES

    # we add a readonly info field for feedback summary
    readonly_fields = ('feedback_summary',)

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
    )

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


# ----------------------------
# Exam admin
# ----------------------------
from django.contrib import admin
from .models import Exam, ExamTrack
#from .admin_inlines import ExamCategoryAllocationInline
#from .widgets import BULMA_WIDGET_OVERRIDES






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
@admin.register(UserExam)
class UserExamAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'exam', 'score', 'started_at', 'submitted_at')
    search_fields = ('user__username', 'exam__title')
    actions = [export_userexams_csv]

    readonly_fields = (
        'user', 'exam', 'question_order',
        'started_at', 'submitted_at',
        'score', 'passed', 'status'
    )

    list_per_page = 50   # 🔥 pagination control

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'exam')

    def has_add_permission(self, request):
        return request.user.is_superuser



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

from django.contrib import admin
from .models import ExamTrack

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

    admin.site.register(ExamTrackSubscription)



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

