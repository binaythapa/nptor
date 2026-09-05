from django.contrib import admin

from cv.models import (
    CareerAchievement,
    CareerCertification,
    CareerEducation,
    CareerExperience,
    CareerProfile,
    CareerProject,
    CareerSkill,
)


@admin.register(CareerProfile)
class CareerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "professional_title", "is_confirmed", "updated_at")
    search_fields = ("user__username", "user__email", "professional_title")


@admin.register(CareerExperience)
class CareerExperienceAdmin(admin.ModelAdmin):
    list_display = ("job_title", "employer", "profile", "is_current", "sort_order")
    list_filter = ("is_current", "is_confirmed")
    search_fields = ("job_title", "employer", "profile__user__username")


@admin.register(CareerEducation)
class CareerEducationAdmin(admin.ModelAdmin):
    list_display = ("qualification", "institution", "profile", "sort_order")
    search_fields = ("qualification", "institution", "profile__user__username")


@admin.register(CareerProject)
class CareerProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "profile", "sort_order", "is_confirmed")
    search_fields = ("name", "profile__user__username")


@admin.register(CareerSkill)
class CareerSkillAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "profile", "sort_order")
    search_fields = ("name", "category", "profile__user__username")


@admin.register(CareerAchievement)
class CareerAchievementAdmin(admin.ModelAdmin):
    list_display = ("title", "profile", "achieved_on", "sort_order")
    search_fields = ("title", "profile__user__username")


@admin.register(CareerCertification)
class CareerCertificationAdmin(admin.ModelAdmin):
    list_display = ("name", "issuer", "profile", "issued_on", "sort_order")
    search_fields = ("name", "issuer", "profile__user__username")
