from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from store.storage import protected_storage


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    display_order = models.PositiveIntegerField(default=0)
    default_commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Category commission override; NULL inherits vendor baseline.",
    )

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        if self.parent:
            return f"{self.parent} -> {self.name}"
        return self.name


class Product(models.Model):
    TYPE_PHYSICAL = "physical"
    TYPE_DIGITAL = "digital"

    TYPE_CHOICES = (
        (TYPE_PHYSICAL, "Physical Product"),
        (TYPE_DIGITAL, "Digital Download"),
    )

    STATUS_DRAFT = "draft"
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_CHANGES_REQUIRED = "changes_required"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = (
        (STATUS_DRAFT, "Draft"),
        (STATUS_PENDING, "Pending Approval"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_CHANGES_REQUIRED, "Changes Required"),
        (STATUS_REJECTED, "Rejected"),
    )

    vendor = models.ForeignKey(
        "vendors.VendorProfile",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="products",
        help_text="NULL denotes NPTOR Platform-owned product",
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=220, unique=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )
    product_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_PHYSICAL,
        db_index=True,
    )
    description = models.TextField(blank=True, default="")
    specifications = models.JSONField(default=dict, blank=True)
    is_cod_eligible = models.BooleanField(
        default=True,
        help_text="Can this physical product be ordered via Cash on Delivery within Nepal?",
    )
    is_internationally_available = models.BooleanField(
        default=False,
        help_text="Can this product be purchased outside Nepal? (Digital defaults True, physical False for MVP)",
    )
    approval_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        db_index=True,
    )
    is_active = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Seller visibility toggle; only visible on storefront if approved and is_active=True",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_store_products",
    )
    review_notes = models.TextField(blank=True, default="")
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Product"
        verbose_name_plural = "Products"

    def __str__(self):
        prefix = f"[{self.vendor.store_name}] " if self.vendor else "[NPTOR] "
        return f"{prefix}{self.title}"

    @property
    def is_nptor_owned(self):
        return self.vendor_id is None

    @property
    def is_digital(self):
        return self.product_type == self.TYPE_DIGITAL


class ProductVariant(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
    )
    sku = models.CharField(max_length=64, unique=True, db_index=True)
    variant_name = models.CharField(max_length=100, default="Standard")
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    compare_at_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    currency = models.CharField(
        max_length=10,
        default="NPR",
        help_text="Product pricing currency; defaults to NPR for Nepal Store",
    )
    weight_grams = models.PositiveIntegerField(
        default=0,
        help_text="Physical weight in grams for shipping calculation",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Product Variant"
        verbose_name_plural = "Product Variants"

    def __str__(self):
        return f"{self.product.title} - {self.variant_name} ({self.sku})"


class ProductInventory(models.Model):
    variant = models.OneToOneField(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name="inventory",
    )
    quantity = models.IntegerField(default=0)
    reserved_quantity = models.IntegerField(
        default=0,
        help_text="Stock temporarily locked in active checkouts",
    )
    low_stock_threshold = models.PositiveIntegerField(default=5)
    allow_backorder = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product Inventory"
        verbose_name_plural = "Product Inventories"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gte=0),
                name="inventory_quantity_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(reserved_quantity__gte=0),
                name="inventory_reserved_non_negative",
            ),
        ]

    def __str__(self):
        return f"Inventory for {self.variant.sku}: Available {self.available_quantity} (Total {self.quantity}, Reserved {self.reserved_quantity})"

    @property
    def available_quantity(self):
        return max(0, self.quantity - self.reserved_quantity)


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to="store/products/")
    alt_text = models.CharField(max_length=200, blank=True, default="")
    display_order = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "id"]
        verbose_name = "Product Image"
        verbose_name_plural = "Product Images"

    def __str__(self):
        return f"Image for {self.product.title}"


class ProductDigitalAsset(models.Model):
    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name="digital_asset",
    )
    file = models.FileField(storage=protected_storage, upload_to="store/digital_assets/")
    file_name = models.CharField(max_length=255)
    file_size_bytes = models.BigIntegerField(default=0)
    checksum_sha256 = models.CharField(max_length=64, blank=True, default="")
    max_downloads_per_purchase = models.PositiveIntegerField(default=5)
    download_validity_days = models.PositiveIntegerField(default=365)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product Digital Asset"
        verbose_name_plural = "Product Digital Assets"

    def __str__(self):
        return f"Digital Asset: {self.file_name} ({self.product.title})"
