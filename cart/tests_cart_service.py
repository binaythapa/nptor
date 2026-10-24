from datetime import timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase
from django.utils import timezone

from cart.models import Cart, CartItem, StockReservation
from cart.services.cart_service import (
    CartService,
    InactiveProductError,
    InsufficientStockError,
)
from cart.services.reservation_service import ReservationService
from store.models import Category, Product, ProductInventory, ProductVariant
from vendors.models import VendorProfile

User = get_user_model()


class CartServiceTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="cart_shopper", email="shopper@example.com", password="pass")
        self.category = Category.objects.create(name="Tech", slug="tech")
        self.product = Product.objects.create(
            title="Python Robotics Board",
            slug="python-robotics-board",
            category=self.category,
            product_type=Product.TYPE_PHYSICAL,
            approval_status=Product.STATUS_APPROVED,
            is_active=True,
            is_cod_eligible=True,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku="ROBOT-BRD-01",
            price=Decimal("3500.00"),
            currency="NPR",
        )
        self.inventory = ProductInventory.objects.create(
            variant=self.variant,
            quantity=10,
            reserved_quantity=0,
        )

    def test_anonymous_and_authenticated_cart_creation(self):
        # Anonymous request
        anon_request = self.factory.get("/")
        anon_request.user = AnonymousUser()
        anon_request.session = self.client.session
        anon_cart = CartService.get_or_create_cart(anon_request)
        self.assertIsNotNone(anon_cart.session_key)
        self.assertIsNone(anon_cart.user)

        # Authenticated request
        auth_request = self.factory.get("/")
        auth_request.user = self.user
        auth_request.session = self.client.session
        auth_cart = CartService.get_or_create_cart(auth_request)
        self.assertEqual(auth_cart.user, self.user)

    def test_merge_anonymous_cart_into_user_cart(self):
        guest_cart = Cart.objects.create(session_key="sess_guest_merge", currency="NPR")
        CartItem.objects.create(
            cart=guest_cart,
            variant=self.variant,
            quantity=2,
            unit_price_snapshot=Decimal("3500.00"),
        )
        user_cart = Cart.objects.create(user=self.user, currency="NPR")

        CartService.merge_carts(guest_cart, user_cart)
        self.assertEqual(user_cart.items.count(), 1)
        self.assertEqual(user_cart.items.first().quantity, 2)
        self.assertFalse(Cart.objects.filter(pk=guest_cart.pk).exists())

    def test_add_to_cart_rejects_unapproved_or_inactive_products(self):
        cart = Cart.objects.create(user=self.user, currency="NPR")

        # Draft product
        draft_prod = Product.objects.create(
            title="Draft Kit",
            slug="draft-kit",
            category=self.category,
            approval_status=Product.STATUS_DRAFT,
            is_active=False,
        )
        draft_var = ProductVariant.objects.create(product=draft_prod, sku="DRAFT-01", price=Decimal("100.00"))
        with self.assertRaises(InactiveProductError):
            CartService.add_to_cart(cart, draft_var.id, quantity=1)

    def test_add_to_cart_enforces_available_inventory(self):
        cart = Cart.objects.create(user=self.user, currency="NPR")
        # Requesting 15 when only 10 available
        with self.assertRaises(InsufficientStockError):
            CartService.add_to_cart(cart, self.variant.id, quantity=15)

        # Requesting 5 succeeds
        item = CartService.add_to_cart(cart, self.variant.id, quantity=5)
        self.assertEqual(item.quantity, 5)

    def test_price_change_detection_and_validation(self):
        cart = Cart.objects.create(user=self.user, currency="NPR")
        item = CartService.add_to_cart(cart, self.variant.id, quantity=2)
        self.assertEqual(item.unit_price_snapshot, Decimal("3500.00"))

        # Vendor changes price to 3800.00
        self.variant.price = Decimal("3800.00")
        self.variant.save()

        analysis = CartService.validate_cart(cart)
        self.assertTrue(analysis["valid"])
        self.assertEqual(len(analysis["price_changes"]), 1)
        self.assertEqual(analysis["price_changes"][0]["old_price"], Decimal("3500.00"))
        self.assertEqual(analysis["price_changes"][0]["new_price"], Decimal("3800.00"))

        item.refresh_from_db()
        self.assertEqual(item.unit_price_snapshot, Decimal("3800.00"))
        self.assertEqual(item.total_price, Decimal("7600.00"))

    def test_purging_unapproved_items_on_cart_validation(self):
        cart = Cart.objects.create(user=self.user, currency="NPR")
        CartService.add_to_cart(cart, self.variant.id, quantity=1)

        # Admin rejects product after it was placed in cart
        self.product.approval_status = Product.STATUS_REJECTED
        self.product.is_active = False
        self.product.save()

        with self.assertRaises(InactiveProductError):
            CartService.validate_cart(cart)

        # Item must be purged
        self.assertEqual(cart.items.count(), 0)

    def test_reservation_and_expiry_release(self):
        cart = Cart.objects.create(user=self.user, currency="NPR")
        CartService.add_to_cart(cart, self.variant.id, quantity=3)

        # Reserve stock
        reservations = ReservationService.reserve_cart_stock(cart, ttl_minutes=15)
        self.assertEqual(len(reservations), 1)

        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.reserved_quantity, 3)
        self.assertEqual(self.inventory.available_quantity, 7)

        # Fast forward time to expire reservation
        res = reservations[0]
        res.expires_at = timezone.now() - timedelta(minutes=1)
        res.save()

        # Run expiry cleanup
        released = ReservationService.release_expired_reservations()
        self.assertEqual(released, 1)

        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.reserved_quantity, 0)
        self.assertEqual(self.inventory.available_quantity, 10)
