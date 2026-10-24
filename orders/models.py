from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class ShippingAddress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="store_shipping_addresses",
    )
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30)
    street_address_1 = models.CharField(max_length=255)
    street_address_2 = models.CharField(max_length=255, blank=True, default="")
    city = models.CharField(max_length=100)
    district = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="District in Nepal (e.g. Kathmandu, Lalitpur, Kaski)",
    )
    province = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Province in Nepal (e.g. Bagmati, Gandaki)",
    )
    postal_code = models.CharField(max_length=20, blank=True, default="")
    country = models.CharField(max_length=2, default="NP")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Shipping Address"
        verbose_name_plural = "Shipping Addresses"

    def __str__(self):
        return f"{self.full_name}, {self.city}, {self.country}"


class Order(models.Model):
    PAYMENT_METHOD_ONLINE = "online"
    PAYMENT_METHOD_COD = "cod"

    PAYMENT_METHOD_CHOICES = (
        (PAYMENT_METHOD_ONLINE, "Online Payment Gateway"),
        (PAYMENT_METHOD_COD, "Cash on Delivery"),
    )

    ORDER_STATUS_PENDING = "pending"
    ORDER_STATUS_PROCESSING = "processing"
    ORDER_STATUS_COMPLETED = "completed"
    ORDER_STATUS_CANCELLED = "cancelled"

    ORDER_STATUS_CHOICES = (
        (ORDER_STATUS_PENDING, "Pending Confirmation"),
        (ORDER_STATUS_PROCESSING, "Processing"),
        (ORDER_STATUS_COMPLETED, "Completed"),
        (ORDER_STATUS_CANCELLED, "Cancelled"),
    )

    ONLINE_STATUS_NOT_APPLICABLE = "not_applicable"
    ONLINE_STATUS_UNPAID = "unpaid"
    ONLINE_STATUS_AUTHORIZED = "authorized"
    ONLINE_STATUS_PAID = "paid"
    ONLINE_STATUS_FAILED = "failed"
    ONLINE_STATUS_REFUNDED = "refunded"

    ONLINE_STATUS_CHOICES = (
        (ONLINE_STATUS_NOT_APPLICABLE, "Not Applicable"),
        (ONLINE_STATUS_UNPAID, "Unpaid"),
        (ONLINE_STATUS_AUTHORIZED, "Authorized"),
        (ONLINE_STATUS_PAID, "Paid"),
        (ONLINE_STATUS_FAILED, "Failed"),
        (ONLINE_STATUS_REFUNDED, "Refunded"),
    )

    COD_STATUS_NOT_APPLICABLE = "not_applicable"
    COD_STATUS_PENDING_DELIVERY = "pending_delivery"
    COD_STATUS_COLLECTED_BY_COURIER = "collected_by_courier"
    COD_STATUS_REMITTED_TO_NPTOR = "remitted_to_nptor"
    COD_STATUS_RECONCILED = "reconciled"
    COD_STATUS_DELIVERY_REFUSED = "delivery_refused"

    COD_STATUS_CHOICES = (
        (COD_STATUS_NOT_APPLICABLE, "Not Applicable"),
        (COD_STATUS_PENDING_DELIVERY, "Pending Delivery Collection"),
        (COD_STATUS_COLLECTED_BY_COURIER, "Collected by Courier"),
        (COD_STATUS_REMITTED_TO_NPTOR, "Remitted to NPTOR Bank"),
        (COD_STATUS_RECONCILED, "Reconciled"),
        (COD_STATUS_DELIVERY_REFUSED, "Delivery Refused"),
    )

    order_number = models.CharField(max_length=50, unique=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="store_orders",
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default=PAYMENT_METHOD_ONLINE,
        db_index=True,
    )
    total_items_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    shipping_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    grand_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    currency = models.CharField(max_length=10, default="NPR")
    shipping_address = models.ForeignKey(
        ShippingAddress,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="orders",
    )
    order_status = models.CharField(
        max_length=25,
        choices=ORDER_STATUS_CHOICES,
        default=ORDER_STATUS_PENDING,
        db_index=True,
    )
    online_payment_status = models.CharField(
        max_length=25,
        choices=ONLINE_STATUS_CHOICES,
        default=ONLINE_STATUS_UNPAID,
        db_index=True,
    )
    cod_collection_status = models.CharField(
        max_length=25,
        choices=COD_STATUS_CHOICES,
        default=COD_STATUS_NOT_APPLICABLE,
        db_index=True,
    )
    idempotency_key = models.CharField(
        max_length=120,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Store Order"
        verbose_name_plural = "Store Orders"

    def __str__(self):
        return f"Order {self.order_number} ({self.get_order_status_display()})"


class SubOrder(models.Model):
    FULFILLMENT_PENDING = "pending"
    FULFILLMENT_PROCESSING = "processing"
    FULFILLMENT_SHIPPED = "shipped"
    FULFILLMENT_OUT_FOR_DELIVERY = "out_for_delivery"
    FULFILLMENT_DELIVERED = "delivered"
    FULFILLMENT_FAILED_RTO = "delivery_failed"
    FULFILLMENT_CANCELLED = "cancelled"

    FULFILLMENT_CHOICES = (
        (FULFILLMENT_PENDING, "Pending Allocation"),
        (FULFILLMENT_PROCESSING, "Processing / Packing"),
        (FULFILLMENT_SHIPPED, "Shipped with Courier"),
        (FULFILLMENT_OUT_FOR_DELIVERY, "Out for Delivery"),
        (FULFILLMENT_DELIVERED, "Delivered to Customer"),
        (FULFILLMENT_FAILED_RTO, "Delivery Failed / Returned (RTO)"),
        (FULFILLMENT_CANCELLED, "Cancelled"),
    )

    REFUND_NONE = "none"
    REFUND_REQUESTED = "requested"
    REFUND_APPROVED = "approved"
    REFUND_INSPECTED = "inspected"
    REFUND_COMPLETED = "refunded"
    REFUND_REJECTED = "rejected"

    REFUND_CHOICES = (
        (REFUND_NONE, "No Refund Requested"),
        (REFUND_REQUESTED, "Refund Requested"),
        (REFUND_APPROVED, "Refund Approved"),
        (REFUND_INSPECTED, "Return Inspected"),
        (REFUND_COMPLETED, "Refund Completed"),
        (REFUND_REJECTED, "Refund Rejected"),
    )

    PAYABLE_HOLDING = "holding"
    PAYABLE_ELIGIBLE = "eligible"
    PAYABLE_QUEUED = "queued"
    PAYABLE_PAID = "paid"
    PAYABLE_FORFEITED = "forfeited"

    PAYABLE_CHOICES = (
        (PAYABLE_HOLDING, "Holding Period Active"),
        (PAYABLE_ELIGIBLE, "Eligible for Payout"),
        (PAYABLE_QUEUED, "Queued in Payout Batch"),
        (PAYABLE_PAID, "Paid Out to Seller"),
        (PAYABLE_FORFEITED, "Forfeited / Returned"),
    )

    master_order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="suborders",
    )
    suborder_number = models.CharField(max_length=60, unique=True, db_index=True)
    vendor = models.ForeignKey(
        "vendors.VendorProfile",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="suborders",
        help_text="NULL denotes NPTOR Platform-owned fulfillment",
    )
    items_subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    customer_shipping_charge = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    actual_courier_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    actual_rto_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    platform_commission = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    vendor_payout_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    fulfillment_status = models.CharField(
        max_length=25,
        choices=FULFILLMENT_CHOICES,
        default=FULFILLMENT_PENDING,
        db_index=True,
    )
    refund_status = models.CharField(
        max_length=25,
        choices=REFUND_CHOICES,
        default=REFUND_NONE,
        db_index=True,
    )
    seller_payable_status = models.CharField(
        max_length=25,
        choices=PAYABLE_CHOICES,
        default=PAYABLE_HOLDING,
        db_index=True,
    )
    shipping_carrier = models.CharField(max_length=100, blank=True, default="")
    tracking_number = models.CharField(max_length=100, blank=True, default="")
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    settlement_hold_until = models.DateTimeField(null=True, blank=True, db_index=True)
    cancellation_reason = models.TextField(blank=True, default="")
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cancelled_suborders",
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Seller SubOrder"
        verbose_name_plural = "Seller SubOrders"

    def __str__(self):
        vendor_name = self.vendor.store_name if self.vendor else "NPTOR"
        return f"SubOrder {self.suborder_number} [{vendor_name}]"


class OrderItem(models.Model):
    suborder = models.ForeignKey(
        SubOrder,
        on_delete=models.CASCADE,
        related_name="items",
    )
    variant = models.ForeignKey(
        "store.ProductVariant",
        on_delete=models.PROTECT,
        related_name="order_items",
    )
    product_title_snapshot = models.CharField(max_length=255)
    sku_snapshot = models.CharField(max_length=64)
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )
    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    commission_rate_snapshot = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("10.00"),
    )

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"

    def __str__(self):
        return f"{self.quantity}x {self.product_title_snapshot} ({self.sku_snapshot})"


class OrderPayment(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_SUCCESSFUL = "successful"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_SUCCESSFUL, "Successful"),
        (STATUS_FAILED, "Failed"),
        (STATUS_CANCELLED, "Cancelled"),
    )

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    payment_method = models.CharField(max_length=20, default="online")
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    currency = models.CharField(max_length=10, default="NPR")
    status = models.CharField(
        max_length=25,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    gateway_name = models.CharField(max_length=50, blank=True, default="dummy")
    gateway_order_id = models.CharField(max_length=255, blank=True, default="", db_index=True)
    gateway_payment_id = models.CharField(max_length=255, blank=True, default="", db_index=True)
    idempotency_key = models.CharField(
        max_length=120,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
    )
    raw_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Order Payment"
        verbose_name_plural = "Order Payments"

    def __str__(self):
        return f"Payment {self.id} for Order {self.order.order_number} ({self.status})"


class DigitalDelivery(models.Model):
    order_item = models.OneToOneField(
        OrderItem,
        on_delete=models.CASCADE,
        related_name="digital_delivery",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="store_digital_deliveries",
    )
    digital_asset = models.ForeignKey(
        "store.ProductDigitalAsset",
        on_delete=models.PROTECT,
        related_name="deliveries",
    )
    download_token = models.CharField(max_length=64, unique=True, db_index=True)
    download_count = models.PositiveIntegerField(default=0)
    max_downloads = models.PositiveIntegerField(default=5)
    expires_at = models.DateTimeField(db_index=True)
    is_revoked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Digital Delivery"
        verbose_name_plural = "Digital Deliveries"

    def __str__(self):
        return f"Delivery Token for {self.order_item.product_title_snapshot}"


class OrderReturnRequest(models.Model):
    REASON_DEFECTIVE = "defective"
    REASON_WRONG_ITEM = "wrong_item"
    REASON_NOT_AS_DESCRIBED = "not_as_described"
    REASON_CHANGED_MIND = "changed_mind"

    REASON_CHOICES = (
        (REASON_DEFECTIVE, "Defective / Damaged"),
        (REASON_WRONG_ITEM, "Wrong Item Received"),
        (REASON_NOT_AS_DESCRIBED, "Not As Described"),
        (REASON_CHANGED_MIND, "Changed Mind"),
    )

    STATUS_REQUESTED = "requested"
    STATUS_APPROVED = "approved"
    STATUS_INSPECTED_OK = "inspected_ok"
    STATUS_INSPECTED_FAILED = "inspected_failed"
    STATUS_REFUNDED = "refunded"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = (
        (STATUS_REQUESTED, "Requested"),
        (STATUS_APPROVED, "Approved for Return"),
        (STATUS_INSPECTED_OK, "Inspected - Passed"),
        (STATUS_INSPECTED_FAILED, "Inspected - Failed"),
        (STATUS_REFUNDED, "Refunded"),
        (STATUS_REJECTED, "Rejected"),
    )

    suborder = models.ForeignKey(
        SubOrder,
        on_delete=models.CASCADE,
        related_name="return_requests",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="store_return_requests",
    )
    reason = models.CharField(max_length=50, choices=REASON_CHOICES)
    status = models.CharField(
        max_length=25,
        choices=STATUS_CHOICES,
        default=STATUS_REQUESTED,
        db_index=True,
    )
    explanation = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Order Return Request"
        verbose_name_plural = "Order Return Requests"

    def __str__(self):
        return f"Return Request #{self.id} for SubOrder {self.suborder.suborder_number}"
