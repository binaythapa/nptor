from django.contrib import admin
from .models import StaticPage, Feedback


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
