from django.contrib import admin

from .models import (
    ContentVertical,
    Country,
    GovernmentBody,
    GovernmentExamProgram,
    GovernmentExamStage,
    GovernmentExamVersion,
    GovernmentJob,
)


@admin.register(ContentVertical)
class ContentVerticalAdmin(admin.ModelAdmin):
    list_display = ("name", "vertical_type", "is_active")
    list_filter = ("vertical_type", "is_active")
    search_fields = ("name", "code")
    prepopulated_fields = {"code": ("name",)}


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(GovernmentBody)
class GovernmentBodyAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "code", "is_active")
    list_filter = ("country", "is_active")
    search_fields = ("name", "code", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(GovernmentJob)
class GovernmentJobAdmin(admin.ModelAdmin):
    list_display = ("name", "government_body", "country", "code", "is_active")
    list_filter = ("country", "government_body", "is_active")
    search_fields = ("name", "code", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(GovernmentExamProgram)
class GovernmentExamProgramAdmin(admin.ModelAdmin):
    list_display = ("name", "government_body", "country", "code", "is_active")
    list_filter = ("country", "government_body", "content_vertical", "is_active")
    search_fields = ("name", "code", "slug")
    filter_horizontal = ("jobs",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(GovernmentExamVersion)
class GovernmentExamVersionAdmin(admin.ModelAdmin):
    list_display = ("program", "version", "status", "effective_from", "effective_to")
    list_filter = ("status", "program__country", "program__government_body")
    search_fields = ("program__name", "version", "slug")


@admin.register(GovernmentExamStage)
class GovernmentExamStageAdmin(admin.ModelAdmin):
    list_display = ("version", "order", "name", "exam", "is_required", "is_active")
    list_filter = ("is_required", "is_active", "version__program__country")
    search_fields = ("name", "code", "exam__title", "version__program__name")
    ordering = ("version", "order")
