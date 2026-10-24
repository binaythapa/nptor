from django.contrib import admin
from .models import (
    VendorBankDetails,
    VendorCommission,
    VendorLedger,
    VendorPayout,
    VendorPayoutAllocation,
    VendorProfile,
)


class VendorBankDetailsInline(admin.StackedInline):
    model = VendorBankDetails
    can_delete = False
    extra = 0
    fields = ("bank_name", "bank_account_name", "display_account_number", "bank_branch")
    readonly_fields = ("display_account_number",)

    def display_account_number(self, instance):
        if not instance or not instance.pk:
            return ""
        # Mask account number for security unless superuser
        return instance.masked_account_number

    display_account_number.short_description = "Bank Account (Masked)"


class VendorCommissionInline(admin.TabularInline):
    model = VendorCommission
    extra = 1


@admin.register(VendorProfile)
class VendorProfileAdmin(admin.ModelAdmin):
    list_display = ("store_name", "user", "status", "commission_rate", "is_cod_enabled", "created_at")
    list_filter = ("status", "is_cod_enabled", "rto_fee_liability")
    search_fields = ("store_name", "slug", "business_email", "pan_vat_number")
    prepopulated_fields = {"slug": ("store_name",)}
    inlines = [VendorBankDetailsInline, VendorCommissionInline]
    readonly_fields = ("created_at", "updated_at", "approved_at")


@admin.register(VendorBankDetails)
class VendorBankDetailsAdmin(admin.ModelAdmin):
    list_display = ("vendor", "bank_name", "bank_account_name", "masked_account_display")
    search_fields = ("vendor__store_name", "bank_name", "bank_account_name")
    readonly_fields = ("vendor", "masked_account_display", "created_at", "updated_at")

    def masked_account_display(self, obj):
        return obj.masked_account_number

    masked_account_display.short_description = "Account Number"

    def get_fields(self, request, obj=None):
        fields = ["vendor", "bank_name", "bank_account_name", "masked_account_display", "bank_branch", "created_at", "updated_at"]
        if request.user.is_superuser:
            fields.insert(4, "bank_account_number")
        return fields


@admin.register(VendorLedger)
class VendorLedgerAdmin(admin.ModelAdmin):
    list_display = ("vendor", "entry_type", "amount", "currency", "is_settled", "created_at")
    list_filter = ("entry_type", "is_settled", "currency")
    search_fields = ("vendor__store_name", "reference_id", "idempotency_key")
    readonly_fields = [f.name for f in VendorLedger._meta.get_fields() if hasattr(f, "name")]

    def has_add_permission(self, request):
        return False  # Immutable ledger entries created only via service layer

    def has_delete_permission(self, request, obj=None):
        return False


class VendorPayoutAllocationInline(admin.TabularInline):
    model = VendorPayoutAllocation
    extra = 0
    can_delete = False
    readonly_fields = ("ledger_entry", "allocated_amount", "created_at")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(VendorPayout)
class VendorPayoutAdmin(admin.ModelAdmin):
    list_display = ("payout_reference", "vendor", "net_disbursed", "currency", "status", "created_at")
    list_filter = ("status", "currency")
    search_fields = ("payout_reference", "vendor__store_name", "bank_transaction_reference")
    readonly_fields = ("created_at",)
    inlines = [VendorPayoutAllocationInline]


@admin.register(VendorPayoutAllocation)
class VendorPayoutAllocationAdmin(admin.ModelAdmin):
    list_display = ("payout", "ledger_entry", "allocated_amount", "created_at")
    search_fields = ("payout__payout_reference", "ledger_entry__reference_id")
    readonly_fields = ("payout", "ledger_entry", "allocated_amount", "created_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
