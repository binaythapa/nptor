from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
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

    @property
    def primary_image(self):
        """Returns the primary product image or the first available image."""
        try:
            imgs = list(self.images.all())
            for img in imgs:
                if img.is_primary:
                    return img
            return imgs[0] if imgs else None
        except Exception:
            return None

    @property
    def is_demo(self):
        """Returns True if the product is demonstration/sample showcase data."""
        if self.specifications and self.specifications.get("is_demo"):
            return True
        if self.slug and self.slug.startswith("demo-"):
            return True
        if self.title and self.title.startswith("[Demo"):
            return True
        return False

    @property
    def average_rating(self):
        """Returns average approved rating (float rounded to 1 decimal) or None."""
        try:
            approved = self.reviews.filter(status=ProductReview.STATUS_APPROVED)
            if approved.exists():
                from django.db.models import Avg
                val = approved.aggregate(Avg("rating"))["rating__avg"]
                return round(val, 1) if val is not None else None
            return None
        except Exception:
            return None

    @property
    def review_count(self):
        """Returns count of approved customer reviews."""
        try:
            return self.reviews.filter(status=ProductReview.STATUS_APPROVED).count()
        except Exception:
            return 0

    @property
    def rating_distribution(self):
        """Returns distribution of 1-5 star percentages for approved customer reviews."""
        try:
            approved = list(self.reviews.filter(status=ProductReview.STATUS_APPROVED).values_list("rating", flat=True))
            total = len(approved)
            if total == 0:
                return {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
            dist = {}
            for star in range(5, 0, -1):
                count = approved.count(star)
                dist[star] = int(round((count / total) * 100))
            return dist
        except Exception:
            return {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}

    @property
    def brand_name(self):
        if self.specifications and isinstance(self.specifications, dict):
            return self.specifications.get("brand") or self.specifications.get("Brand")
        return None


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
    attributes = models.JSONField(
        default=dict,
        blank=True,
        help_text="Configurable key-value variant attributes, e.g. {'size': '42', 'color': 'Navy'}",
    )
    image = models.ForeignKey(
        "ProductImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="variants",
        help_text="Specific image representing this variant",
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

class ProductVideo(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="videos",
    )
    video_url = models.URLField(
        blank=True,
        default="",
        help_text="Direct MP4/WebM video URL or authorized video stream link",
    )
    video_file = models.FileField(
        upload_to="store/videos/",
        blank=True,
        null=True,
    )
    poster_image = models.ImageField(
        upload_to="store/videos/posters/",
        blank=True,
        null=True,
    )
    title = models.CharField(max_length=200, blank=True, default="")
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "id"]
        verbose_name = "Product Video"
        verbose_name_plural = "Product Videos"

    def __str__(self):
        return f"Video for {self.product.title}: {self.title or 'Product Demo'}"


class ProductReview(models.Model):
    STATUS_APPROVED = "approved"
    STATUS_PENDING = "pending"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = (
        (STATUS_APPROVED, "Approved"),
        (STATUS_PENDING, "Pending Moderation"),
        (STATUS_REJECTED, "Rejected"),
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="store_reviews",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating between 1 and 5 stars",
    )
    title = models.CharField(max_length=150)
    content = models.TextField()
    is_verified_purchase = models.BooleanField(
        default=False,
        help_text="True if reviewer completed a verified purchase of this product",
    )
    order = models.ForeignKey(
        "orders.Order",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="product_reviews",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_APPROVED,
        db_index=True,
    )
    helpful_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Product Review"
        verbose_name_plural = "Product Reviews"
        constraints = [
            models.UniqueConstraint(
                fields=["product", "user"],
                name="unique_user_product_review",
            )
        ]

    def __str__(self):
        return f"{self.rating}* by {self.user.username} on {self.product.title}"


class ProductReviewImage(models.Model):
    review = models.ForeignKey(
        ProductReview,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to="store/reviews/")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Review Image"
        verbose_name_plural = "Review Images"

    def __str__(self):
        return f"Image for Review #{self.review_id}"


class ProductReviewHelpfulVote(models.Model):
    review = models.ForeignKey(
        ProductReview,
        on_delete=models.CASCADE,
        related_name="helpful_votes",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="review_helpful_votes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Review Helpful Vote"
        verbose_name_plural = "Review Helpful Votes"
        constraints = [
            models.UniqueConstraint(
                fields=["review", "user"],
                name="unique_user_review_helpful_vote",
            )
        ]

    def __str__(self):
        return f"Helpful vote by {self.user.username} on Review #{self.review_id}"


class ProductReviewReport(models.Model):
    review = models.ForeignKey(
        ProductReview,
        on_delete=models.CASCADE,
        related_name="reports",
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="review_reports",
    )
    reason = models.CharField(max_length=255)
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Review Report"
        verbose_name_plural = "Review Reports"

    def __str__(self):
        return f"Report on Review #{self.review_id} by {self.reporter.username}"


class Wishlist(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="store_wishlist_items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="wishlisted_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Wishlist Item"
        verbose_name_plural = "Wishlist Items"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "product"],
                name="unique_user_wishlist_product",
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.product.title}"
