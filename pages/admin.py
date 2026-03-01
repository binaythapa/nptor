from django.contrib import admin
from .models import *


@admin.register(StaticPage)
class StaticPageAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "slug",
        "is_published",
        "updated_at",
    )
    list_filter = ("is_published",)
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("title",)

    fieldsets = (
        ("Page Info", {
            "fields": ("title", "slug", "is_published"),
        }),
        ("Content", {
            "fields": ("content",),
        }),
    )


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "user",
        "is_resolved",
        "created_at",
    )
    list_filter = ("is_resolved", "created_at")
    search_fields = ("email", "message")
    readonly_fields = ("email", "user", "message", "created_at")
    ordering = ("-created_at",)

    actions = ["mark_as_resolved"]

    @admin.action(description="Mark selected feedback as resolved")
    def mark_as_resolved(self, request, queryset):
        queryset.update(is_resolved=True)



from django.contrib import admin
from .models import Testimonial


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):

    # Columns shown in list view
    list_display = (
        "name",
        "user",
        "exam_track",
        "course",
        "study_plan",
        "rating",
        "is_approved",
        "is_featured",
        "created_at",
    )

    # Filters on right side
    list_filter = (
        "is_approved",
        "is_featured",
        "rating",
        "exam_track",
        "course",
        "study_plan",
        "created_at",
    )

    # Search box
    search_fields = (
        "name",
        "message",
        "user__username",
        "user__email",
    )

    # Read-only fields
    readonly_fields = ("created_at",)

    # Default ordering
    ordering = ("-created_at",)

    # Admin form layout
    fieldsets = (
        ("User Info", {
            "fields": ("user", "name", "role")
        }),
        ("Content", {
            "fields": ("message", "rating")
        }),
        ("Related To", {
            "fields": ("exam_track", "course", "study_plan")
        }),
        ("Status", {
            "fields": ("is_approved", "is_featured")
        }),
        ("Metadata", {
            "fields": ("created_at",)
        }),
    )

    # Bulk approve action
    actions = ["approve_testimonials"]

    def approve_testimonials(self, request, queryset):
        queryset.update(is_approved=True)

    approve_testimonials.short_description = "Approve selected testimonials"
