from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from cart.models import Cart
from cart.services.cart_service import CartService
from orders.models import (
    Order,
    OrderItem,
    OrderPayment,
    ShippingAddress,
    SubOrder,
)
from orders.services.checkout_service import CheckoutService
from store.models import Category, Product, ProductInventory, ProductVariant
from vendors.models import VendorProfile

User = get_user_model()


class CheckoutServiceTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(username="checkout_buyer", email="cbuyer@example.com", password="pass")
        self.seller_1 = User.objects.create_user(username="seller_one", email="s1@example.com", password="pass")
        self.seller_2 = User.objects.create_user(username="seller_two", email="s2@example.com", password="pass")

        self.vendor_1 = VendorProfile.objects.create(
            user=self.seller_1,
            store_name="Kathmandu Science Store",
            slug="ktm-science-store",
            commission_rate=Decimal("10.00"),
            is_cod_enabled=True,
            status=VendorProfile.STATUS_ACTIVE,
        )
        self.vendor_2 = VendorProfile.objects.create(
            user=self.seller_2,
            store_name="Himalayan Robotics",
            slug="himalayan-robotics",
            commission_rate=Decimal("15.00"),
            is_cod_enabled=False,  # COD disabled for this seller
            status=VendorProfile.STATUS_ACTIVE,
        )

        self.category = Category.objects.create(name="Education", slug="education")

        # Physical Product (Vendor 1, COD eligible)
        self.physical_prod = Product.objects.create(
            vendor=self.vendor_1,
            title="Physics Experiment Kit",
            slug="physics-experiment-kit",
            category=self.category,
            product_type=Product.TYPE_PHYSICAL,
            is_cod_eligible=True,
            is_internationally_available=False,
            approval_status=Product.STATUS_APPROVED,
            is_active=True,
        )
        self.physical_var = ProductVariant.objects.create(
            product=self.physical_prod,
            sku="PHYS-KIT-01",
            price=Decimal("2000.00"),
        )
        ProductInventory.objects.create(variant=self.physical_var, quantity=20, reserved_quantity=0)

        # Physical Product (Vendor 2, COD not eligible due to vendor setting)
        self.vendor2_prod = Product.objects.create(
            vendor=self.vendor_2,
            title="Robotics Motor Pack",
            slug="robotics-motor-pack",
            category=self.category,
            product_type=Product.TYPE_PHYSICAL,
            is_cod_eligible=True,
            approval_status=Product.STATUS_APPROVED,
            is_active=True,
        )
        self.vendor2_var = ProductVariant.objects.create(
            product=self.vendor2_prod,
            sku="ROBOT-MTR-01",
            price=Decimal("1500.00"),
        )
        ProductInventory.objects.create(variant=self.vendor2_var, quantity=10, reserved_quantity=0)

        # Digital Product (International eligible)
        self.digital_prod = Product.objects.create(
            title="NPTOR Python Handbook",
            slug="nptor-python-handbook",
            category=self.category,
            product_type=Product.TYPE_DIGITAL,
            is_cod_eligible=False,
            is_internationally_available=True,
            approval_status=Product.STATUS_APPROVED,
            is_active=True,
        )
        self.digital_var = ProductVariant.objects.create(
            product=self.digital_prod,
            sku="PY-BOOK-PDF",
            price=Decimal("500.00"),
        )

        # Shipping Addresses
        self.nepal_address = ShippingAddress.objects.create(
            user=self.buyer,
            full_name="Ram Thapa",
            phone="+977-9851000000",
            street_address_1="Thamel Marg",
            city="Kathmandu",
            district="Kathmandu",
            province="Bagmati",
            country="NP",
        )
        self.intl_address = ShippingAddress.objects.create(
            user=self.buyer,
            full_name="John Doe",
            phone="+1-555-0199",
            street_address_1="123 Market St",
            city="San Francisco",
            country="US",
        )

    def test_nepal_physical_delivery_restriction(self):
        """Physical products must reject non-Nepal destination countries."""
        cart = Cart.objects.create(user=self.buyer, currency="NPR")
        CartService.add_to_cart(cart, self.physical_var.id, quantity=1)

        with self.assertRaises(ValidationError) as ctx:
            CheckoutService.prepare_checkout(
                cart=cart,
                user=self.buyer,
                shipping_address=self.intl_address,
                payment_method=Order.PAYMENT_METHOD_ONLINE,
            )
        self.assertIn("only within Nepal", str(ctx.exception))

    def test_international_digital_order_without_shipping_address(self):
        """Digital download checkout does not require a physical shipping address and is available internationally."""
        cart = Cart.objects.create(user=self.buyer, currency="NPR")
        CartService.add_to_cart(cart, self.digital_var.id, quantity=1)

        order = CheckoutService.prepare_checkout(
            cart=cart,
            user=self.buyer,
            shipping_address=None,
            payment_method=Order.PAYMENT_METHOD_ONLINE,
        )
        self.assertEqual(order.user, self.buyer)
        self.assertEqual(order.grand_total, Decimal("500.00"))
        self.assertEqual(order.suborders.count(), 1)
        self.assertIsNone(order.shipping_address)

    def test_cod_rejected_for_digital_only_cart(self):
        """Cash on Delivery must be rejected for purely digital products."""
        cart = Cart.objects.create(user=self.buyer, currency="NPR")
        CartService.add_to_cart(cart, self.digital_var.id, quantity=1)

        with self.assertRaises(ValidationError) as ctx:
            CheckoutService.prepare_checkout(
                cart=cart,
                user=self.buyer,
                shipping_address=self.nepal_address,
                payment_method=Order.PAYMENT_METHOD_COD,
            )
        self.assertIn("digital downloads", str(ctx.exception).lower())

    def test_cod_rejected_for_mixed_cart(self):
        """Cash on Delivery must be rejected for mixed physical + digital carts."""
        cart = Cart.objects.create(user=self.buyer, currency="NPR")
        CartService.add_to_cart(cart, self.physical_var.id, quantity=1)
        CartService.add_to_cart(cart, self.digital_var.id, quantity=1)

        with self.assertRaises(ValidationError) as ctx:
            CheckoutService.prepare_checkout(
                cart=cart,
                user=self.buyer,
                shipping_address=self.nepal_address,
                payment_method=Order.PAYMENT_METHOD_COD,
            )
        self.assertIn("mixed carts", str(ctx.exception).lower())

    def test_cod_rejected_when_vendor_has_cod_disabled(self):
        """Cash on Delivery must be rejected if any physical product's seller has COD disabled."""
        cart = Cart.objects.create(user=self.buyer, currency="NPR")
        CartService.add_to_cart(cart, self.vendor2_var.id, quantity=1)

        with self.assertRaises(ValidationError) as ctx:
            CheckoutService.prepare_checkout(
                cart=cart,
                user=self.buyer,
                shipping_address=self.nepal_address,
                payment_method=Order.PAYMENT_METHOD_COD,
            )
        self.assertIn("not eligible for cash on delivery", str(ctx.exception).lower())

    def test_multi_vendor_cart_splitting_and_accounting(self):
        """Multi-vendor order creates separate SubOrders with independent commission deductions."""
        cart = Cart.objects.create(user=self.buyer, currency="NPR")
        CartService.add_to_cart(cart, self.physical_var.id, quantity=2)  # Vendor 1: 2 * 2000 = 4000
        CartService.add_to_cart(cart, self.vendor2_var.id, quantity=1)   # Vendor 2: 1 * 1500 = 1500

        order = CheckoutService.prepare_checkout(
            cart=cart,
            user=self.buyer,
            shipping_address=self.nepal_address,
            payment_method=Order.PAYMENT_METHOD_ONLINE,
        )

        self.assertEqual(order.grand_total, Decimal("5500.00"))
        self.assertEqual(order.suborders.count(), 2)

        # SubOrder for Vendor 1 (10% commission on 4000 = 400 comm, 3600 payout)
        sub1 = order.suborders.get(vendor=self.vendor_1)
        self.assertEqual(sub1.items_subtotal, Decimal("4000.00"))
        self.assertEqual(sub1.platform_commission, Decimal("400.00"))
        self.assertEqual(sub1.vendor_payout_amount, Decimal("3600.00"))

        # SubOrder for Vendor 2 (15% commission on 1500 = 225 comm, 1275 payout)
        sub2 = order.suborders.get(vendor=self.vendor_2)
        self.assertEqual(sub2.items_subtotal, Decimal("1500.00"))
        self.assertEqual(sub2.platform_commission, Decimal("225.00"))
        self.assertEqual(sub2.vendor_payout_amount, Decimal("1275.00"))

        # Inventory reserved
        self.physical_var.inventory.refresh_from_db()
        self.assertEqual(self.physical_var.inventory.reserved_quantity, 2)
        self.vendor2_var.inventory.refresh_from_db()
        self.assertEqual(self.vendor2_var.inventory.reserved_quantity, 1)

    def test_idempotent_duplicate_checkout_submission(self):
        """Submitting checkout twice with the same idempotency key returns the existing order."""
        cart = Cart.objects.create(user=self.buyer, currency="NPR")
        CartService.add_to_cart(cart, self.physical_var.id, quantity=1)

        key = "IDEM-TEST-KEY-7777"
        order1 = CheckoutService.prepare_checkout(
            cart=cart,
            user=self.buyer,
            shipping_address=self.nepal_address,
            payment_method=Order.PAYMENT_METHOD_ONLINE,
            idempotency_key=key,
        )

        # Attempt second checkout with identical key
        order2 = CheckoutService.prepare_checkout(
            cart=cart,
            user=self.buyer,
            shipping_address=self.nepal_address,
            payment_method=Order.PAYMENT_METHOD_ONLINE,
            idempotency_key=key,
        )

        self.assertEqual(order1.pk, order2.pk)
        self.assertEqual(Order.objects.filter(idempotency_key=key).count(), 1)
