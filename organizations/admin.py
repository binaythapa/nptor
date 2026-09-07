from django.contrib import admin
from django.shortcuts import redirect, render

from organizations.models.organization import Organization
from organizations.models.membership import OrganizationMember
from organizations.models.assignment import ResourceAssignment
from organizations.models.subscription import OrganizationCourseSubscription
from organizations.models.access import ResourceAccess
from organizations.models.profile import OrganizationProfile
from organizations.models.portal import OrganizationPortalConfig
from organizations.models.domain import OrganizationDomain
from organizations.models.portfolio import OrganizationPortfolioSection
from organizations.models.audit import OrganizationAuditLog
from courses.models import Course
from organizations.permissions import org_admin_required


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "org_type", "is_active", "created_at")
    list_filter = ("org_type", "is_active")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(OrganizationMember)
class OrganizationMemberAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "role", "is_active", "joined_at")
    list_filter = ("organization", "role", "is_active")
    search_fields = ("user__username", "organization__name")


@admin.register(ResourceAssignment)
class CourseAssignmentAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "organization", "assigned_at")
    list_filter = ("organization",)
    search_fields = ("student__username", "course__title")
    autocomplete_fields = ("student", "course", "organization")


@admin.register(OrganizationCourseSubscription)
class OrganizationCourseSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("organization", "course", "is_active", "subscribed_at", "expires_at", "payment_required")
    list_filter = ("is_active", "organization")
    search_fields = ("organization__name", "course__title")
    autocomplete_fields = ("organization", "course")
    readonly_fields = ("subscribed_at",)


@admin.register(ResourceAccess)
class CourseAccessAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "source", "organization", "is_active", "granted_at")
    list_filter = ("source", "is_active", "organization")
    search_fields = ("user__username", "course__title", "organization__name")
    autocomplete_fields = ("user", "course", "organization")
    readonly_fields = ("granted_at",)


@admin.register(OrganizationProfile)
class OrganizationProfileAdmin(admin.ModelAdmin):
    list_display = ("organization", "display_name", "city", "country", "updated_at")
    search_fields = ("organization__name", "display_name", "city", "country")


@admin.register(OrganizationPortalConfig)
class OrganizationPortalConfigAdmin(admin.ModelAdmin):
    list_display = ("organization", "is_published", "primary_color", "updated_at")
    list_filter = ("is_published",)


@admin.register(OrganizationDomain)
class OrganizationDomainAdmin(admin.ModelAdmin):
    list_display = ("domain", "organization", "is_verified", "is_primary", "ssl_status")
    list_filter = ("is_verified", "is_primary", "ssl_status")
    search_fields = ("domain", "organization__name")


@admin.register(OrganizationPortfolioSection)
class OrganizationPortfolioSectionAdmin(admin.ModelAdmin):
    list_display = ("organization", "section_type", "display_order", "is_enabled")
    list_filter = ("section_type", "is_enabled")
    search_fields = ("organization__name", "title")


@admin.register(OrganizationAuditLog)
class OrganizationAuditLogAdmin(admin.ModelAdmin):
    list_display = ("organization", "actor", "action", "target_type", "created_at")
    list_filter = ("action", "organization")
    search_fields = ("organization__name", "actor__username", "action")
    readonly_fields = ("organization", "actor", "action", "target_type", "target_id", "metadata", "created_at")


@org_admin_required
def course_create(request):
    if request.method == "POST":
        Course.objects.create(organization=request.active_org, title=request.POST["title"], description=request.POST["description"])
        return redirect("organizations:courses")
    return render(request, "organizations/admin/course_form.html")
