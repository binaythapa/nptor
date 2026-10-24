from decimal import Decimal
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from vendors.crypto import decrypt_bank_account, encrypt_bank_account


class VendorProfile(models.Model):
    STATUS_PENDING = "pending"
    STATUS_ACTIVE = "active"
    STATUS_SUSPENDED = "suspended"
    STATUS_CLOSED = "closed"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending Verification"),
        (STATUS_ACTIVE, "Active Approved"),
        (STATUS_SUSPENDED, "Suspended"),
        (STATUS_CLOSED, "Closed"),
    )

    RTO_VENDOR_ABSORBS = "vendor_absorbs"
    RTO_PLATFORM_ABSORBS = "platform_absorbs"
    RTO_SPLIT_50_50 = "split_50_50"

    RTO_CHOICES = (
        (RTO_VENDOR_ABSORBS, "Vendor Absorbs RTO Shipping"),
        (RTO_PLATFORM_ABSORBS, "Platform Absorbs RTO Shipping"),
        (RTO_SPLIT_50_50, "50/50 Split"),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="vendor_profile",
    )
    store_name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=160, unique=True)
    business_email = models.EmailField()
    business_phone = models.CharField(max_length=30)
    pan_vat_number = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Permanent Account Number (PAN) or VAT registration in Nepal",
    )
    business_registration_number = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Department of Commerce / Office of the Company Registrar number",
    )
    is_cod_enabled = models.BooleanField(
        default=True,
        help_text="Seller permission to participate in Nepal COD orders",
    )
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("10.00"),
        validators=[MinValueValidator(Decimal("0.00")), MaxValueValidator(Decimal("100.00"))],
        help_text="Default platform commission percentage; provisional baseline",
    )
    settlement_holding_days = models.PositiveIntegerField(
        default=7,
        help_text="Internal settlement holding period in calendar days post-delivery",
    )
    rto_fee_liability = models.CharField(
        max_length=20,
        choices=RTO_CHOICES,
        default=RTO_VENDOR_ABSORBS,
        help_text="Configurable liability policy for failed COD return shipping",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="vendors_approved",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Vendor Profile"
        verbose_name_plural = "Vendor Profiles"

    def __str__(self):
        return self.store_name


class VendorBankDetails(models.Model):
    vendor = models.OneToOneField(
        VendorProfile,
        on_delete=models.CASCADE,
        related_name="bank_details",
    )
    bank_name = models.CharField(max_length=100, help_text="Licensed commercial bank in Nepal")
    bank_account_name = models.CharField(max_length=150)
    encrypted_account_number = models.CharField(max_length=255, blank=True, default="", help_text="Fernet AES-encrypted account number at rest")
    last_four_digits = models.CharField(max_length=4, blank=True, default="", help_text="Last 4 digits stored unencrypted for masking")
    bank_branch = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Vendor Bank Details"
        verbose_name_plural = "Vendor Bank Details"

    def __init__(self, *args, **kwargs):
        plain_account = kwargs.pop("bank_account_number", None)
        super().__init__(*args, **kwargs)
        if plain_account:
            self.bank_account_number = plain_account

    def __str__(self):
        return f"{self.vendor.store_name} - {self.bank_name}"

    @property
    def bank_account_number(self):
        if not self.encrypted_account_number:
            return ""
        return decrypt_bank_account(self.encrypted_account_number)

    @bank_account_number.setter
    def bank_account_number(self, value):
        if value:
            clean = str(value).strip()
            self.encrypted_account_number = encrypt_bank_account(clean)
            self.last_four_digits = clean[-4:] if len(clean) >= 4 else clean
        else:
            self.encrypted_account_number = ""
            self.last_four_digits = ""

    @property
    def masked_account_number(self):
        if not self.last_four_digits:
            return ""
        return f"************{self.last_four_digits}"


class VendorCommission(models.Model):
    vendor = models.ForeignKey(
        VendorProfile,
        on_delete=models.CASCADE,
        related_name="category_commissions",
    )
    category = models.ForeignKey(
        "store.Category",
        on_delete=models.CASCADE,
        related_name="vendor_commissions",
    )
    rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00")), MaxValueValidator(Decimal("100.00"))],
        help_text="Category commission override percentage for this vendor",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("vendor", "category")
        verbose_name = "Vendor Category Commission"
        verbose_name_plural = "Vendor Category Commissions"

    def __str__(self):
        return f"{self.vendor.store_name} - {self.category.name}: {self.rate}%"


class VendorLedger(models.Model):
    ENTRY_CREDIT_ORDER_SALE = "credit_order_sale"
    ENTRY_CREDIT_SHIPPING_COLLECTED = "credit_shipping_collected"
    ENTRY_DEBIT_COMMISSION = "debit_platform_commission"
    ENTRY_DEBIT_COURIER_SHIPPING = "debit_courier_shipping_cost"
    ENTRY_DEBIT_RTO_SHIPPING = "debit_rto_shipping_penalty"
    ENTRY_DEBIT_REFUND = "debit_customer_refund"
    ENTRY_CREDIT_COMMISSION_REVERSAL = "credit_commission_reversal"
    ENTRY_DEBIT_PAYOUT = "debit_payout_disbursement"
    ENTRY_CREDIT_COD_REMITTED = "credit_cod_cash_remitted"
    ENTRY_ADJUSTMENT = "adjustment_dispute"

    ENTRY_TYPE_CHOICES = (
        (ENTRY_CREDIT_ORDER_SALE, "Gross Product Sale Value"),
        (ENTRY_CREDIT_SHIPPING_COLLECTED, "Shipping Fee Collected from Customer"),
        (ENTRY_DEBIT_COMMISSION, "Platform Commission Deduction"),
        (ENTRY_DEBIT_COURIER_SHIPPING, "Courier Shipping Fee Paid on Behalf of Seller"),
        (ENTRY_DEBIT_RTO_SHIPPING, "Return-to-Origin Courier Charge for Failed Delivery"),
        (ENTRY_DEBIT_REFUND, "Customer Refund Deduction"),
        (ENTRY_CREDIT_COMMISSION_REVERSAL, "Commission Reversal on Refunded Order"),
        (ENTRY_DEBIT_PAYOUT, "Payout Disbursed via Bank Transfer / ConnectIPS"),
        (ENTRY_CREDIT_COD_REMITTED, "Reconciled Cash Remitted by Courier"),
        (ENTRY_ADJUSTMENT, "Administrative Dispute Adjustment"),
    )

    vendor = models.ForeignKey(
        VendorProfile,
        on_delete=models.PROTECT,
        related_name="ledger_entries",
    )
    suborder = models.ForeignKey(
        "orders.SubOrder",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ledger_entries",
    )
    entry_type = models.CharField(
        max_length=40,
        choices=ENTRY_TYPE_CHOICES,
        db_index=True,
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Positive for credit to seller; negative for debit",
    )
    currency = models.CharField(max_length=10, default="NPR")
    is_settled = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Has this entry passed the settlement hold and been paid out?",
    )
    unlocks_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Timestamp when settlement hold expires",
    )
    reference_id = models.CharField(
        max_length=100,
        blank=True,
        default="",
        db_index=True,
        help_text="Unique event reference for idempotency",
    )
    idempotency_key = models.CharField(
        max_length=120,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Vendor Ledger Entry"
        verbose_name_plural = "Vendor Ledger Entries"
        constraints = [
            models.UniqueConstraint(
                fields=["vendor", "entry_type", "reference_id"],
                name="unique_vendor_ledger_event",
            ),
        ]

    def __str__(self):
        return f"{self.vendor.store_name} - {self.entry_type}: {self.amount} {self.currency}"


class VendorPayout(models.Model):
    STATUS_PROPOSED = "proposed"
    STATUS_APPROVED = "approved"
    STATUS_SUBMITTED = "submitted"
    STATUS_CONFIRMED = "confirmed"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = (
        (STATUS_PROPOSED, "Proposed"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_SUBMITTED, "Submitted to Bank"),
        (STATUS_CONFIRMED, "Confirmed Disbursed"),
        (STATUS_FAILED, "Failed Reverted"),
    )

    vendor = models.ForeignKey(
        VendorProfile,
        on_delete=models.PROTECT,
        related_name="payouts",
    )
    payout_reference = models.CharField(max_length=100, unique=True, db_index=True)
    gross_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    commission_deducted = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    shipping_deducted = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    rto_penalties_deducted = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    net_disbursed = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    currency = models.CharField(max_length=10, default="NPR")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PROPOSED,
        db_index=True,
    )
    bank_transaction_reference = models.CharField(
        max_length=150,
        blank=True,
        default="",
        help_text="ConnectIPS or NCHL bank transfer reference number",
    )
    disbursed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="payouts_disbursed",
    )
    disbursed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Vendor Payout"
        verbose_name_plural = "Vendor Payouts"

    def __str__(self):
        return f"Payout {self.payout_reference} for {self.vendor.store_name} ({self.status})"


class VendorPayoutAllocation(models.Model):
    payout = models.ForeignKey(
        VendorPayout,
        on_delete=models.CASCADE,
        related_name="allocations",
    )
    ledger_entry = models.ForeignKey(
        VendorLedger,
        on_delete=models.PROTECT,
        related_name="payout_allocations",
    )
    allocated_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Amount allocated from this ledger entry to the payout batch",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Vendor Payout Allocation"
        verbose_name_plural = "Vendor Payout Allocations"
        constraints = [
            models.UniqueConstraint(
                fields=["payout", "ledger_entry"],
                name="unique_payout_ledger_allocation",
            ),
        ]

    def __str__(self):
        return f"Allocation: Ledger #{self.ledger_entry_id} -> Payout {self.payout.payout_reference} ({self.allocated_amount})"

