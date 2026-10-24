from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Cart(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="store_carts",
    )
    session_key = models.CharField(max_length=40, db_index=True, blank=True, default="")
    currency = models.CharField(
        max_length=10,
        default="NPR",
        help_text="Store cart currency; independent of educational currency",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cart"
        verbose_name_plural = "Carts"
        indexes = [
            models.Index(fields=["session_key", "updated_at"]),
            models.Index(fields=["user", "updated_at"]),
        ]

    def __str__(self):
        owner = self.user.username if self.user else f"Guest ({self.session_key[:8]})"
        return f"Cart #{self.id} for {owner}"

    @property
    def total_quantity(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        return sum(item.total_price for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
    )
    variant = models.ForeignKey(
        "store.ProductVariant",
        on_delete=models.CASCADE,
        related_name="cart_items",
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )
    unit_price_snapshot = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("cart", "variant")
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"

    def __str__(self):
        return f"{self.quantity}x {self.variant.sku} in Cart #{self.cart_id}"

    @property
    def total_price(self):
        return self.unit_price_snapshot * self.quantity


class StockReservation(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="stock_reservations",
    )
    variant = models.ForeignKey(
        "store.ProductVariant",
        on_delete=models.CASCADE,
        related_name="stock_reservations",
    )
    reserved_units = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )
    expires_at = models.DateTimeField(db_index=True)
    is_released = models.BooleanField(default=False, db_index=True)
    idempotency_key = models.CharField(
        max_length=120,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("cart", "variant")
        verbose_name = "Stock Reservation"
        verbose_name_plural = "Stock Reservations"
        indexes = [
            models.Index(fields=["expires_at", "is_released"]),
        ]

    def __str__(self):
        status = "Released" if self.is_released else ("Expired" if self.is_expired else "Active")
        return f"Hold {self.reserved_units} of {self.variant.sku} ({status})"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
