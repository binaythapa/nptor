# quiz/admin.py
from django.contrib import admin
from django import forms
from django.db import models
from django.forms import widgets
from .models import (
    Category, Question, Choice, Exam,
    UserExam, UserAnswer, ExamCategoryAllocation, Notification,Client
)

import csv
from django.http import HttpResponse

admin.site.register(Client)

# ----------------------------
# Helper: give admin form widgets Bulma-friendly classes
# ----------------------------
# Use `formfield_overrides` on ModelAdmin to add classes to default widgets.
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
    list_display = ('title','created_at')
    search_fields = ('title','message')
    filter_horizontal = ('users',)
    # Apply bulma overrides (so fields have classes)
    formfield_overrides = BULMA_WIDGET_OVERRIDES


# ----------------------------
# Choice inline for Questions
# ----------------------------
class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4
    fields = ('text','is_correct','order')
    formfield_overrides = {
        models.CharField: {'widget': forms.TextInput(attrs={'class': 'input'})},
        models.IntegerField: {'widget': forms.NumberInput(attrs={'class': 'input', 'style':'width:80px'})},
    }


# ----------------------------
# Question admin
# ----------------------------
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id','short_text','question_type','difficulty','category')
    inlines = [ChoiceInline]
    list_filter = ('question_type','difficulty','category')
    search_fields = ('text',)
    fieldsets = (
        (None, {'fields': ('category','text','question_type','difficulty')}),
        ('Advanced (for non-MCQ)', {
            'fields': ('correct_text','numeric_answer','numeric_tolerance','matching_pairs','ordering_items'),
            'classes': ('collapse',)
        }),
    )
    formfield_overrides = BULMA_WIDGET_OVERRIDES

    def short_text(self, obj):
        return obj.text[:60] if obj.text else ''


# ----------------------------
# ExamCategoryAllocation inline
# ----------------------------
class ExamCategoryAllocationInline(admin.TabularInline):
    model = ExamCategoryAllocation
    extra = 1
    fields = ('category','percentage','fixed_count')
    formfield_overrides = {
        models.IntegerField: {'widget': forms.NumberInput(attrs={'class': 'input', 'style':'width:100px'})},
        models.ForeignKey: {'widget': forms.Select(attrs={'class': 'select'})},
    }


# ----------------------------
# Exam admin
# ----------------------------
@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'question_count', 'duration_seconds', 'is_published', 'level', 'passing_score')
    inlines = [ExamCategoryAllocationInline]
    filter_horizontal = ('categories', 'prerequisite_exams')
    fieldsets = (
        (None, {
            'fields': (
                'title',
                'category',
                'categories',
                'question_count',
                'duration_seconds',
                'is_published',
            )
        }),
        ('Progression / Rules', {
            'classes': ('collapse',),
            'fields': ('level','passing_score','prerequisite_exams',),
            'description': 'Configure progression level, passing threshold and explicit prerequisites.'
        }),
    )
    formfield_overrides = BULMA_WIDGET_OVERRIDES


# ----------------------------
# Category admin
# ----------------------------
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name','slug')
    formfield_overrides = BULMA_WIDGET_OVERRIDES


# ----------------------------
# CSV export for UserExam
# ----------------------------
def export_userexams_csv(modeladmin, request, queryset):
    fieldnames = ['id','user','exam','score','started_at','submitted_at']
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="userexams.csv"'
    writer = csv.writer(response)
    writer.writerow(fieldnames)
    for ue in queryset:
        writer.writerow([ue.id, ue.user.username, ue.exam.title, ue.score, ue.started_at, ue.submitted_at])
    return response
export_userexams_csv.short_description = "Export selected user exams to CSV"


@admin.register(UserExam)
class UserExamAdmin(admin.ModelAdmin):
    list_display = ('id','user','exam','score','started_at','submitted_at')
    actions = [export_userexams_csv]
    formfield_overrides = BULMA_WIDGET_OVERRIDES


@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ('id','user_exam','question','choice','is_correct')
    readonly_fields = ('selections','raw_answer')
    formfield_overrides = BULMA_WIDGET_OVERRIDES
