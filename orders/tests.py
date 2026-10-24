from decimal import Decimal
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from orders.models import (
    DigitalDelivery,
    Order,
    OrderItem,
    OrderPayment,
    OrderReturnRequest,
    ShippingAddress,
    SubOrder,
)
from store.models import Category, Product, ProductDigitalAsset, ProductVariant
from vendors.models import VendorProfile

User = get_user_model()


class OrderModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="buyer", email="buyer@example.com", password="pass")
        self.seller = User.objects.create_user(username="vendor_orders", email="vo@example.com", password="pass")
        self.vendor = VendorProfile.objects.create(
            user=self.seller,
            store_name="Pokhara Stationery",
            slug="pokhara-stationery",
            business_email="sales@pokharastationery.com",
            business_phone="+977-9833333333",
        )
        self.category = Category.objects.create(name="Stationery", slug="stationery")
        self.product = Product.objects.create(
            vendor=self.vendor,
            title="Scientific Calculator",
            slug="scientific-calculator",
            category=self.category,
            product_type=Product.TYPE_PHYSICAL,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku="CALC-FX991",
            price=Decimal("2500.00"),
            currency="NPR",
        )
        self.shipping_address = ShippingAddress.objects.create(
            user=self.user,
            full_name="Aayush Sharma",
            phone="+977-9841234567",
            street_address_1="New Road Gate",
            city="Kathmandu",
            district="Kathmandu",
            province="Bagmati",
            country="NP",
        )

    def test_order_and_suborder_creation_with_multidimensional_states(self):
        order = Order.objects.create(
            order_number="NPTOR-ORD-2026-0001",
            user=self.user,
            payment_method=Order.PAYMENT_METHOD_COD,
            total_items_amount=Decimal("2500.00"),
            shipping_amount=Decimal("100.00"),
            grand_total=Decimal("2600.00"),
            currency="NPR",
            shipping_address=self.shipping_address,
            order_status=Order.ORDER_STATUS_PENDING,
            cod_collection_status=Order.COD_STATUS_PENDING_DELIVERY,
        )
        self.assertEqual(order.currency, "NPR")
        self.assertEqual(order.payment_method, "cod")

        suborder = SubOrder.objects.create(
            master_order=order,
            suborder_number="NPTOR-SUB-2026-0001-01",
            vendor=self.vendor,
            items_subtotal=Decimal("2500.00"),
            customer_shipping_charge=Decimal("100.00"),
            platform_commission=Decimal("250.00"),
            vendor_payout_amount=Decimal("2250.00"),
            fulfillment_status=SubOrder.FULFILLMENT_PENDING,
            seller_payable_status=SubOrder.PAYABLE_HOLDING,
        )
        self.assertEqual(suborder.master_order, order)
        self.assertEqual(suborder.vendor, self.vendor)

        item = OrderItem.objects.create(
            suborder=suborder,
            variant=self.variant,
            product_title_snapshot="Scientific Calculator",
            sku_snapshot="CALC-FX991",
            unit_price=Decimal("2500.00"),
            quantity=1,
            total_price=Decimal("2500.00"),
            commission_rate_snapshot=Decimal("10.00"),
        )
        self.assertEqual(suborder.items.count(), 1)
        self.assertEqual(item.total_price, Decimal("2500.00"))

    def test_order_idempotency_key_uniqueness(self):
        order1 = Order.objects.create(
            order_number="NPTOR-ORD-001",
            user=self.user,
            total_items_amount=Decimal("1000.00"),
            grand_total=Decimal("1000.00"),
            idempotency_key="IDEM-ORD-001",
        )
        self.assertIsNotNone(order1.pk)

        with self.assertRaises(IntegrityError):
            Order.objects.create(
                order_number="NPTOR-ORD-002",
                user=self.user,
                total_items_amount=Decimal("1000.00"),
                grand_total=Decimal("1000.00"),
                idempotency_key="IDEM-ORD-001",
            )

    def test_order_payment_and_digital_delivery(self):
        order = Order.objects.create(
            order_number="NPTOR-ORD-003",
            user=self.user,
            total_items_amount=Decimal("500.00"),
            grand_total=Decimal("500.00"),
        )
        payment = OrderPayment.objects.create(
            order=order,
            amount=Decimal("500.00"),
            currency="NPR",
            status=OrderPayment.STATUS_SUCCESSFUL,
            gateway_name="dummy",
            gateway_payment_id="DUMMY-PAY-001",
            idempotency_key="IDEM-PAY-001",
        )
        self.assertEqual(payment.status, OrderPayment.STATUS_SUCCESSFUL)

        # Digital delivery
        digital_prod = Product.objects.create(
            title="E-Book",
            slug="e-book",
            category=self.category,
            product_type=Product.TYPE_DIGITAL,
        )
        digital_var = ProductVariant.objects.create(
            product=digital_prod,
            sku="EBK-001",
            price=Decimal("500.00"),
        )
        asset = ProductDigitalAsset.objects.create(
            product=digital_prod,
            file_name="ebook.pdf",
            file_size_bytes=2048,
        )
        suborder = SubOrder.objects.create(
            master_order=order,
            suborder_number="NPTOR-SUB-003-01",
            items_subtotal=Decimal("500.00"),
        )
        order_item = OrderItem.objects.create(
            suborder=suborder,
            variant=digital_var,
            product_title_snapshot="E-Book",
            sku_snapshot="EBK-001",
            unit_price=Decimal("500.00"),
            quantity=1,
            total_price=Decimal("500.00"),
        )
        delivery = DigitalDelivery.objects.create(
            order_item=order_item,
            user=self.user,
            digital_asset=asset,
            download_token="tok_1234567890abcdef",
            max_downloads=5,
            expires_at=timezone.now() + timedelta(days=365),
        )
        self.assertEqual(delivery.order_item, order_item)
        self.assertEqual(delivery.download_count, 0)
        self.assertFalse(delivery.is_revoked)
