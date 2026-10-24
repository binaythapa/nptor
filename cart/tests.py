from decimal import Decimal
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from cart.models import Cart, CartItem, StockReservation
from store.models import Category, Product, ProductVariant

User = get_user_model()


class CartModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cart_user", email="cart@example.com", password="pass")
        self.category = Category.objects.create(name="Books", slug="books")
        self.product = Product.objects.create(
            title="Django 6 Mastery",
            slug="django-6-mastery",
            category=self.category,
            product_type=Product.TYPE_PHYSICAL,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku="DJ6-BOOK-001",
            price=Decimal("1200.00"),
            currency="NPR",
        )

    def test_cart_item_calculation_and_uniqueness(self):
        cart = Cart.objects.create(user=self.user, currency="NPR")
        item = CartItem.objects.create(
            cart=cart,
            variant=self.variant,
            quantity=2,
            unit_price_snapshot=Decimal("1200.00"),
        )
        self.assertEqual(item.total_price, Decimal("2400.00"))
        self.assertEqual(cart.subtotal, Decimal("2400.00"))
        self.assertEqual(cart.total_quantity, 2)

        # Unique together constraint on cart + variant
        with self.assertRaises(IntegrityError):
            CartItem.objects.create(
                cart=cart,
                variant=self.variant,
                quantity=1,
                unit_price_snapshot=Decimal("1200.00"),
            )

    def test_stock_reservation_lifecycle(self):
        cart = Cart.objects.create(session_key="guest_sess_12345", currency="NPR")
        now = timezone.now()
        reservation = StockReservation.objects.create(
            cart=cart,
            variant=self.variant,
            reserved_units=2,
            expires_at=now + timedelta(minutes=15),
            idempotency_key="RES-001",
        )
        self.assertFalse(reservation.is_expired)
        self.assertFalse(reservation.is_released)

        # Expired check
        reservation.expires_at = now - timedelta(seconds=1)
        reservation.save()
        self.assertTrue(reservation.is_expired)
