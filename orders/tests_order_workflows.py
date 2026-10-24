from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from cart.models import Cart, CartItem, StockReservation
from cart.services.cart_service import CartService
from cart.services.reservation_service import ReservationService
from orders.adapters.dummy import DummyPaymentAdapter
from orders.models import (
    DigitalDelivery,
    Order,
    OrderItem,
    OrderPayment,
    ShippingAddress,
    SubOrder,
)
from orders.services.checkout_service import CheckoutService
from orders.services.order_workflow_service import OrderWorkflowService
from store.models import Category, Product, ProductDigitalAsset, ProductInventory, ProductVariant
from vendors.models import VendorLedger, VendorProfile

User = get_user_model()


class OrderWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.customer = User.objects.create_user(username="customer1", email="cust1@example.com", password="pass")
        self.other_customer = User.objects.create_user(username="customer2", email="cust2@example.com", password="pass")

        self.vendor_user_a = User.objects.create_user(username="vendor_a", email="va@example.com", password="pass")
        self.vendor_a = VendorProfile.objects.create(
            user=self.vendor_user_a,
            store_name="Alpha Electronics",
            slug="alpha-electronics",
            commission_rate=Decimal("10.00"),
            is_cod_enabled=True,
            status=VendorProfile.STATUS_ACTIVE,
        )

        self.vendor_user_b = User.objects.create_user(username="vendor_b", email="vb@example.com", password="pass")
        self.vendor_b = VendorProfile.objects.create(
            user=self.vendor_user_b,
            store_name="Beta Books",
            slug="beta-books",
            commission_rate=Decimal("15.00"),
            is_cod_enabled=True,
            status=VendorProfile.STATUS_ACTIVE,
        )

        self.category = Category.objects.create(name="Tech", slug="tech")

        # Physical product for Vendor A
        self.product_phys = Product.objects.create(
            vendor=self.vendor_a,
            category=self.category,
            title="Arduino Board",
            slug="arduino-board",
            product_type=Product.TYPE_PHYSICAL,
            approval_status=Product.STATUS_APPROVED,
            is_active=True,
            is_cod_eligible=True,
        )
        self.variant_phys = ProductVariant.objects.create(
            product=self.product_phys,
            sku="ARDUINO-01",
            price=Decimal("1000.00"),
            currency="NPR",
        )
        self.inv_phys = ProductInventory.objects.create(
            variant=self.variant_phys,
            quantity=20,
            reserved_quantity=0,
        )

        # Digital product for Vendor B
        self.product_dig = Product.objects.create(
            vendor=self.vendor_b,
            category=self.category,
            title="Robotics E-Book",
            slug="robotics-ebook",
            product_type=Product.TYPE_DIGITAL,
            approval_status=Product.STATUS_APPROVED,
            is_active=True,
            is_cod_eligible=False,
        )
        self.asset_dig = ProductDigitalAsset.objects.create(
            product=self.product_dig,
            file="protected_storage/ebook.pdf",
            checksum_sha256="fakechecksum",
            file_size_bytes=1024,
        )
        self.variant_dig = ProductVariant.objects.create(
            product=self.product_dig,
            sku="DIG-EBOOK-01",
            price=Decimal("500.00"),
            currency="NPR",
        )

        self.shipping_addr = ShippingAddress.objects.create(
            user=self.customer,
            full_name="Ram Sharma",
            phone="9841000000",
            street_address_1="New Road",
            city="Kathmandu",
            district="Kathmandu",
            country="NP",
        )

    def test_online_payment_workflow_and_inventory_consumption(self):
        # 1. Add physical item to cart & prepare checkout
        cart = Cart.objects.create(user=self.customer, currency="NPR")
        CartItem.objects.create(cart=cart, variant=self.variant_phys, quantity=2, unit_price_snapshot=Decimal("1000.00"))

        order = CheckoutService.prepare_checkout(
            cart=cart,
            user=self.customer,
            shipping_address=self.shipping_addr,
            payment_method=Order.PAYMENT_METHOD_ONLINE,
        )

        # Inventory is currently reserved (not yet permanently consumed)
        self.inv_phys.refresh_from_db()
        self.assertEqual(self.inv_phys.quantity, 20)
        self.assertEqual(self.inv_phys.reserved_quantity, 2)
        self.assertEqual(order.order_status, Order.ORDER_STATUS_PENDING)

        payment = order.payments.first()
        self.assertEqual(payment.status, OrderPayment.STATUS_PENDING)

        # 2. Simulate Payment Adapter verification
        adapter = DummyPaymentAdapter()
        init_res = adapter.initiate_payment(payment, return_url="/store/orders/callback/")
        verify_res = adapter.verify_payment({
            "mock_status": "success",
            "gateway_order_id": init_res["gateway_order_id"],
        })
        self.assertTrue(verify_res["is_successful"])

        # 3. Confirm payment in workflow service
        confirmed_order = OrderWorkflowService.confirm_online_payment(
            payment,
            gateway_payment_id=verify_res["gateway_payment_id"],
            raw_response=verify_res["raw_response"],
        )

        # Status transitions
        self.assertEqual(confirmed_order.order_status, Order.ORDER_STATUS_PROCESSING)
        self.assertEqual(confirmed_order.online_payment_status, Order.ONLINE_STATUS_PAID)

        # Inventory permanently consumed: quantity 20 -> 18, reserved 2 -> 0
        self.inv_phys.refresh_from_db()
        self.assertEqual(self.inv_phys.quantity, 18)
        self.assertEqual(self.inv_phys.reserved_quantity, 0)

        # Vendor ledger postings: gross sale (2000.00) and commission (200.00 at 10%)
        suborder = confirmed_order.suborders.first()
        self.assertEqual(suborder.fulfillment_status, SubOrder.FULFILLMENT_PROCESSING)
        self.assertEqual(suborder.seller_payable_status, SubOrder.PAYABLE_HOLDING)

        ledger_entries = list(VendorLedger.objects.filter(suborder=suborder).order_by("entry_type"))
        self.assertEqual(len(ledger_entries), 2)
        sale_entry = next(e for e in ledger_entries if e.entry_type == VendorLedger.ENTRY_CREDIT_ORDER_SALE)
        comm_entry = next(e for e in ledger_entries if e.entry_type == VendorLedger.ENTRY_DEBIT_COMMISSION)

        self.assertEqual(sale_entry.amount, Decimal("2000.00"))
        self.assertEqual(comm_entry.amount, Decimal("-200.00"))
        self.assertFalse(sale_entry.is_settled)

        # 4. Idempotency test: repeating confirm_online_payment causes NO double-consumption or duplicate ledger entries
        OrderWorkflowService.confirm_online_payment(payment, gateway_payment_id="TXN-DUP-TEST")
        self.inv_phys.refresh_from_db()
        self.assertEqual(self.inv_phys.quantity, 18)
        self.assertEqual(len(VendorLedger.objects.filter(suborder=suborder)), 2)

    def test_cod_order_workflow_and_remittance_reconciliation(self):
        # 1. Prepare COD order
        cart = Cart.objects.create(user=self.customer, currency="NPR")
        CartItem.objects.create(cart=cart, variant=self.variant_phys, quantity=3, unit_price_snapshot=Decimal("1000.00"))

        order = CheckoutService.prepare_checkout(
            cart=cart,
            user=self.customer,
            shipping_address=self.shipping_addr,
            payment_method=Order.PAYMENT_METHOD_COD,
        )

        # Confirm COD placement
        confirmed_order = OrderWorkflowService.confirm_cod_order(order)
        self.assertEqual(confirmed_order.order_status, Order.ORDER_STATUS_PROCESSING)
        self.assertEqual(confirmed_order.cod_collection_status, Order.COD_STATUS_PENDING_DELIVERY)

        # Inventory consumed immediately upon packing confirmation
        self.inv_phys.refresh_from_db()
        self.assertEqual(self.inv_phys.quantity, 17)
        self.assertEqual(self.inv_phys.reserved_quantity, 0)

        # CRITICAL SAFEGUARD: Zero seller ledger entries created at this point!
        suborder = confirmed_order.suborders.first()
        self.assertEqual(VendorLedger.objects.filter(suborder=suborder).count(), 0)

        # 2. Fulfillment updates: Shipped -> Delivered
        OrderWorkflowService.update_suborder_fulfillment(
            suborder,
            SubOrder.FULFILLMENT_SHIPPED,
            carrier="Nepal Post",
            tracking_number="NP-12345",
        )
        suborder.refresh_from_db()
        self.assertEqual(suborder.shipping_carrier, "Nepal Post")
        self.assertEqual(suborder.fulfillment_status, SubOrder.FULFILLMENT_SHIPPED)

        OrderWorkflowService.update_suborder_fulfillment(suborder, SubOrder.FULFILLMENT_DELIVERED)
        confirmed_order.refresh_from_db()
        self.assertEqual(confirmed_order.cod_collection_status, Order.COD_STATUS_COLLECTED_BY_COURIER)
        self.assertEqual(confirmed_order.order_status, Order.ORDER_STATUS_COMPLETED)

        # 3. Courier Remittance Reconciliation
        OrderWorkflowService.reconcile_cod_remittance(
            suborder,
            courier_remittance_ref="REMIT-NPPOST-999",
            courier_fee=Decimal("100.00"),
        )
        confirmed_order.refresh_from_db()
        self.assertEqual(confirmed_order.cod_collection_status, Order.COD_STATUS_RECONCILED)

        # Ledger entries now posted: remitted cash (3000), commission (-300), courier fee (-100)
        entries = list(VendorLedger.objects.filter(suborder=suborder).order_by("entry_type"))
        self.assertEqual(len(entries), 3)

        remit_entry = next(e for e in entries if e.entry_type == VendorLedger.ENTRY_CREDIT_COD_REMITTED)
        comm_entry = next(e for e in entries if e.entry_type == VendorLedger.ENTRY_DEBIT_COMMISSION)
        fee_entry = next(e for e in entries if e.entry_type == VendorLedger.ENTRY_DEBIT_COURIER_SHIPPING)

        self.assertEqual(remit_entry.amount, Decimal("3000.00"))
        self.assertEqual(comm_entry.amount, Decimal("-300.00"))
        self.assertEqual(fee_entry.amount, Decimal("-100.00"))

    def test_suborder_cancellation_restores_inventory_and_posts_ledger_reversals(self):
        # 1. Setup online paid order
        cart = Cart.objects.create(user=self.customer, currency="NPR")
        CartItem.objects.create(cart=cart, variant=self.variant_phys, quantity=2, unit_price_snapshot=Decimal("1000.00"))

        order = CheckoutService.prepare_checkout(
            cart=cart,
            user=self.customer,
            shipping_address=self.shipping_addr,
            payment_method=Order.PAYMENT_METHOD_ONLINE,
        )
        payment = order.payments.first()
        OrderWorkflowService.confirm_online_payment(payment, gateway_payment_id="TXN-CANCEL-TEST")

        self.inv_phys.refresh_from_db()
        self.assertEqual(self.inv_phys.quantity, 18)

        suborder = order.suborders.first()

        # 2. Cancel suborder prior to dispatch
        OrderWorkflowService.cancel_suborder(suborder, reason="Customer requested cancellation", cancelled_by=self.customer)

        suborder.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(suborder.fulfillment_status, SubOrder.FULFILLMENT_CANCELLED)
        self.assertEqual(order.order_status, Order.ORDER_STATUS_CANCELLED)

        # Inventory is restored: 18 -> 20
        self.inv_phys.refresh_from_db()
        self.assertEqual(self.inv_phys.quantity, 20)

        # Balanced ledger reversal entries: refund debit (-2000.00) & commission credit (+200.00)
        reversals = list(VendorLedger.objects.filter(
            suborder=suborder,
            entry_type__in=[VendorLedger.ENTRY_DEBIT_REFUND, VendorLedger.ENTRY_CREDIT_COMMISSION_REVERSAL],
        ))
        self.assertEqual(len(reversals), 2)

    def test_failed_delivery_rto_workflow(self):
        cart = Cart.objects.create(user=self.customer, currency="NPR")
        CartItem.objects.create(cart=cart, variant=self.variant_phys, quantity=1, unit_price_snapshot=Decimal("1000.00"))

        order = CheckoutService.prepare_checkout(
            cart=cart,
            user=self.customer,
            shipping_address=self.shipping_addr,
            payment_method=Order.PAYMENT_METHOD_COD,
        )
        OrderWorkflowService.confirm_cod_order(order)
        self.inv_phys.refresh_from_db()
        self.assertEqual(self.inv_phys.quantity, 19)

        suborder = order.suborders.first()
        OrderWorkflowService.handle_failed_delivery_rto(
            suborder,
            rto_penalty=Decimal("80.00"),
            reason="Customer phone unreachable",
        )

        suborder.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(suborder.fulfillment_status, SubOrder.FULFILLMENT_FAILED_RTO)
        self.assertEqual(order.cod_collection_status, Order.COD_STATUS_DELIVERY_REFUSED)

        # Inventory restored
        self.inv_phys.refresh_from_db()
        self.assertEqual(self.inv_phys.quantity, 20)

        # RTO penalty debited to vendor ledger
        rto_entry = VendorLedger.objects.filter(suborder=suborder, entry_type=VendorLedger.ENTRY_DEBIT_RTO_SHIPPING).first()
        self.assertIsNotNone(rto_entry)
        self.assertEqual(rto_entry.amount, Decimal("-80.00"))

    def test_customer_and_vendor_tenant_access_controls(self):
        cart = Cart.objects.create(user=self.customer, currency="NPR")
        CartItem.objects.create(cart=cart, variant=self.variant_phys, quantity=1, unit_price_snapshot=Decimal("1000.00"))

        order = CheckoutService.prepare_checkout(
            cart=cart,
            user=self.customer,
            shipping_address=self.shipping_addr,
            payment_method=Order.PAYMENT_METHOD_ONLINE,
        )
        suborder = order.suborders.first()

        # 1. Customer order detail view
        self.client.force_login(self.customer)
        url_cust = reverse("orders:customer_order_detail", kwargs={"order_number": order.order_number})
        resp = self.client.get(url_cust)
        self.assertEqual(resp.status_code, 200)

        # Customer 2 attempting to view Customer 1's order -> 404 Not Found
        self.client.force_login(self.other_customer)
        resp_unauth = self.client.get(url_cust)
        self.assertEqual(resp_unauth.status_code, 404)

        # 2. Vendor suborder detail view
        url_vendor_sub = reverse("orders:vendor_suborder_detail", kwargs={"suborder_number": suborder.suborder_number})

        # Vendor A (owner) can view -> 200 OK
        self.client.force_login(self.vendor_user_a)
        resp_va = self.client.get(url_vendor_sub)
        self.assertEqual(resp_va.status_code, 200)

        # Vendor B (different seller) cannot view Vendor A's suborder -> 404 Not Found
        self.client.force_login(self.vendor_user_b)
        resp_vb = self.client.get(url_vendor_sub)
        self.assertEqual(resp_vb.status_code, 404)

        # Regular non-vendor user receives 403 Forbidden
        self.client.force_login(self.other_customer)
        resp_cust = self.client.get(url_vendor_sub)
        self.assertEqual(resp_cust.status_code, 403)
