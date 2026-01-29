from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Course,
    CourseSection,
    Lesson,
    CourseEnrollment,
    LessonProgress,
)


# =========================
# INLINE CONFIGS
# =========================

class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    fields = (
        "title",
        "lesson_type",
        "order",
        "exam",
        "practice_category",
        "video_url",
    )
    ordering = ("order",)


class CourseSectionInline(admin.StackedInline):
    model = CourseSection
    extra = 1
    show_change_link = True
    fields = ("title", "order")
    ordering = ("order",)


# =========================
# MAIN ADMINS
# =========================

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "level",
        "is_published",
        "created_at",
    )
    list_filter = (
        "is_published",
        "level",
        "created_at",
    )
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("subscription_plans",)
    inlines = (CourseSectionInline,)

    fieldsets = (
        ("Basic Info", {
            "fields": (
                "title",
                "slug",
                "description",
                "category",
                "thumbnail",
            )
        }),
        ("Level & Access", {
            "fields": (
                "level",
                "subscription_plans",
                "is_published",
            )
        }),
        ("Meta", {
            "fields": ("created_at",),
        }),
    )

    readonly_fields = ("created_at",)


@admin.register(CourseSection)
class CourseSectionAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "course",
        "order",
    )
    list_filter = ("course",)
    search_fields = ("title",)
    ordering = ("course", "order")
    inlines = (LessonInline,)


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "section",
        "lesson_type",
        "order",
        "linked_resource",
    )
    list_filter = (
        "lesson_type",
        "section__course",
    )
    search_fields = ("title",)
    ordering = ("section", "order")

    def linked_resource(self, obj):
        if obj.lesson_type == "quiz" and obj.exam:
            return f"Quiz: {obj.exam.title}"
        if obj.lesson_type == "practice" and obj.practice_category:
            return f"Practice: {obj.practice_category.name}"
        if obj.lesson_type == "video":
            return "Video"
        if obj.lesson_type == "article":
            return "Article"
        return "—"

    linked_resource.short_description = "Resource"


# =========================
# READ-ONLY / SUPPORT ADMINS
# =========================

@admin.register(CourseEnrollment)
class CourseEnrollmentAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "course",
        "is_active",
        "enrolled_at",
    )
    list_filter = ("is_active", "course")
    search_fields = ("user__username", "course__title")
    readonly_fields = ("enrolled_at",)


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "lesson",
        "completed",
        "completed_at",
    )
    list_filter = ("completed", "lesson__section__course")
    search_fields = ("user__username", "lesson__title")
    readonly_fields = ("completed_at",)
