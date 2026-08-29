from django.contrib import admin

from .models import (
    PaymentOrder,
    PaymentTransaction,
)


# ============================================================
# PAYMENT ORDER
# ============================================================

@admin.register(PaymentOrder)
class PaymentOrderAdmin(admin.ModelAdmin):

    list_display = (
        "order_number",
        "user",
        "resource_type",
        "resource_display",
        "amount",
        "currency",
        "status",
        "gateway",
        "gateway_order_id",
        "gateway_payment_id",
        "paid_at",
        "created_at",
    )

    list_filter = (
        "status",
        "gateway",
        "resource_type",
        "currency",
        "created_at",
        "paid_at",
    )

    search_fields = (
        "order_number",
        "user__username",
        "user__email",
        "gateway_order_id",
        "gateway_payment_id",
    )

    readonly_fields = (
        "order_number",
        "created_at",
        "updated_at",
        "gateway_order_id",
        "gateway_payment_id",
        "paid_at",
    )

    ordering = (
        "-created_at",
    )

    list_per_page = 50

    def resource_display(self, obj):
        resource = obj.get_resource()

        if resource:
            return str(resource)

        return "-"

    resource_display.short_description = "Resource"


# ============================================================
# PAYMENT TRANSACTION
# ============================================================

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "order",
        "gateway",
        "gateway_transaction_id",
        "amount",
        "currency",
        "status",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "status",
        "gateway",
        "currency",
        "created_at",
    )

    search_fields = (
        "order__order_number",
        "order__user__username",
        "order__user__email",
        "gateway_transaction_id",
        "failure_reason",
    )

    readonly_fields = (
        "order",
        "gateway",
        "gateway_transaction_id",
        "amount",
        "currency",
        "status",
        "failure_reason",
        "raw_response",
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )

    list_per_page = 50