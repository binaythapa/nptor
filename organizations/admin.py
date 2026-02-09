from django.contrib import admin
from django.shortcuts import redirect, render

# Explicit model imports (IMPORTANT)
from organizations.models.organization import Organization
from organizations.models.membership import OrganizationMember
from organizations.models.assignment import CourseAssignment
from organizations.models.subscription import OrganizationCourseSubscription
from organizations.models.access import CourseAccess

from courses.models import Course
from organizations.permissions import org_admin_required


# =========================
# ORGANIZATION
# =========================
@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "org_type", "is_active", "created_at")
    list_filter = ("org_type", "is_active")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


# =========================
# ORGANIZATION MEMBERS
# =========================
@admin.register(OrganizationMember)
class OrganizationMemberAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "role", "is_active", "joined_at")
    list_filter = ("organization", "role", "is_active")
    search_fields = ("user__username", "organization__name")


# =========================
# COURSE ASSIGNMENTS
# =========================
@admin.register(CourseAssignment)
class CourseAssignmentAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "organization", "assigned_at")
    list_filter = ("organization",)
    search_fields = ("student__username", "course__title")
    autocomplete_fields = ("student", "course", "organization")


# =========================
# ORGANIZATION COURSE SUBSCRIPTIONS
# =========================
@admin.register(OrganizationCourseSubscription)
class OrganizationCourseSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "organization",
        "course",
        "is_active",
        "subscribed_at",
        "expires_at",
        "payment_required",
    )
    list_filter = ("is_active", "organization")
    search_fields = ("organization__name", "course__title")
    autocomplete_fields = ("organization", "course")
    readonly_fields = ("subscribed_at",)


# =========================
# COURSE ACCESS
# =========================
@admin.register(CourseAccess)
class CourseAccessAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "course",
        "source",
        "organization",
        "is_active",
        "granted_at",
    )
    list_filter = ("source", "is_active", "organization")
    search_fields = (
        "user__username",
        "course__title",
        "organization__name",
    )
    autocomplete_fields = ("user", "course", "organization")
    readonly_fields = ("granted_at",)


# =========================
# ADMIN COURSE CREATE (custom)
# =========================
@org_admin_required
def course_create(request):
    if request.method == "POST":
        Course.objects.create(
            organization=request.active_org,
            title=request.POST["title"],
            description=request.POST["description"],
        )
        return redirect("organizations:courses")

    return render(request, "organizations/admin/course_form.html")
