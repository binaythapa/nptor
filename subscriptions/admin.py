from django.contrib import admin

from .models import (
    SubscriptionPlan,
    Subscription,
    SubscriptionEntitlement,
)


# ============================================================
# SUBSCRIPTION PLAN
# ============================================================

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "code",
        "price",
        "currency",
        "duration_days",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
        "currency",
        "duration_days",
        "created_at",
    )

    search_fields = (
        "name",
        "code",
        "description",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )

    list_per_page = 50


# ============================================================
# SUBSCRIPTION
# ============================================================

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user",
        "plan",
        "status",
        "payment_status",
        "amount",
        "currency",
        "starts_at",
        "expires_at",
        "subscribed_by_admin",
        "auto_renew",
        "created_at",
    )

    list_filter = (
        "status",
        "payment_status",
        "subscribed_by_admin",
        "auto_renew",
        "currency",
        "starts_at",
        "expires_at",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__email",
        "payment_id",
        "plan__name",
        "plan__code",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )

    list_per_page = 50


# ============================================================
# SUBSCRIPTION ENTITLEMENT
# ============================================================

@admin.register(SubscriptionEntitlement)
class SubscriptionEntitlementAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "subscription",
        "resource_type",
        "resource_display",
        "is_active",
        "created_at",
    )

    list_filter = (
        "resource_type",
        "is_active",
        "created_at",
    )

    search_fields = (
        "subscription__user__username",
        "subscription__user__email",
        "course__title",
        "track__title",
        "exam__title",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )

    list_per_page = 50

    def resource_display(self, obj):

        if obj.resource_type == (
            SubscriptionEntitlement.RESOURCE_COURSE
        ):
            return (
                str(obj.course)
                if obj.course
                else "-"
            )

        if obj.resource_type == (
            SubscriptionEntitlement.RESOURCE_TRACK
        ):
            return (
                str(obj.track)
                if obj.track
                else "-"
            )

        if obj.resource_type == (
            SubscriptionEntitlement.RESOURCE_EXAM
        ):
            return (
                str(obj.exam)
                if obj.exam
                else "-"
            )

        return "-"

    resource_display.short_description = "Resource"