from django.contrib import admin

from accounts.models import (
    UserProfile,
    EmailOTP,
    Notification,
    EnrollmentLead,
    Payment,
    ContactMethod,
)

# ============================================================
# USER PROFILE
# ============================================================

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "phone",
        "accepted_policy",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__email",
        "phone",
    )

    list_filter = (
        "accepted_policy",
        "created_at",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )


# ============================================================
# EMAIL OTP
# ============================================================

@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "purpose",
        "code",
        "is_used",
        "expires_at",
        "created_at",
    )

    list_filter = (
        "purpose",
        "is_used",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__email",
        "code",
    )

    readonly_fields = (
        "user",
        "code",
        "purpose",
        "created_at",
        "expires_at",
    )

    ordering = (
        "-created_at",
    )


# ============================================================
# NOTIFICATIONS
# ============================================================

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "recipient_count",
        "created_at",
    )

    search_fields = (
        "title",
        "message",
    )

    list_filter = (
        "created_at",
    )

    readonly_fields = (
        "read_by",
        "created_at",
    )

    filter_horizontal = (
        "recipients",
    )

    ordering = (
        "-created_at",
    )

    def recipient_count(self, obj):
        return obj.recipients.count()

    recipient_count.short_description = "Recipients"


# ============================================================
# ENROLLMENT LEADS
# ============================================================

@admin.register(EnrollmentLead)
class EnrollmentLeadAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "exam",
        "track",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "exam",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__email",
        "exam__title",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )


# ============================================================
# PAYMENTS (IMMUTABLE)
# ============================================================

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "target_name",
        "amount",
        "currency",
        "payment_method",
        "paid_at",
        "created_by_admin",
    )

    list_filter = (
        "payment_method",
        "currency",
        "created_by_admin",
        "paid_at",
    )

    search_fields = (
        "user__username",
        "user__email",
        "reference_id",
    )

    readonly_fields = (
        "user",
        "track",
        "exam",
        "amount",
        "currency",
        "payment_method",
        "reference_id",
        "paid_at",
        "created_by_admin",
    )

    ordering = (
        "-paid_at",
    )


# ============================================================
# CONTACT METHODS (MASTER DATA)
# ============================================================

@admin.register(ContactMethod)
class ContactMethodAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "is_active",
    )

    search_fields = (
        "name",
        "code",
    )

    list_filter = (
        "is_active",
    )

    list_editable = (
        "is_active",
    )

    ordering = (
        "name",
    )
