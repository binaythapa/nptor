from decimal import Decimal
import uuid
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from cart.models import Cart, CartItem
from cart.services.cart_service import CartService
from orders.forms import CheckoutForm
from orders.models import DigitalDelivery, Order, OrderItem, OrderPayment, ShippingAddress, SubOrder
from orders.services.checkout_service import CheckoutService
from orders.services.order_workflow_service import OrderWorkflowService
from store.models import Category, Product, ProductDigitalAsset, ProductInventory, ProductVariant
from vendors.models import VendorProfile

User = get_user_model()


class PaymentAndFulfillmentFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.customer = User.objects.create_user(username="flow_buyer", email="buyer@flow.com", password="pass")
        self.vendor_user = User.objects.create_user(username="flow_seller", email="seller@flow.com", password="pass")
        self.staff_user = User.objects.create_user(username="flow_staff", email="staff@flow.com", password="pass", is_staff=True)

        self.vendor = VendorProfile.objects.create(
            user=self.vendor_user,
            store_name="Flow Store",
            slug="flow-store",
            commission_rate=Decimal("10.00"),
            status=VendorProfile.STATUS_ACTIVE,
            is_cod_enabled=True,
        )
        self.category = Category.objects.create(name="Books", slug="books")

        # Physical product
        self.phys_product = Product.objects.create(
            vendor=self.vendor,
            category=self.category,
            title="Physical Book",
            slug="phys-book",
            product_type=Product.TYPE_PHYSICAL,
            approval_status=Product.STATUS_APPROVED,
            is_active=True,
            is_cod_eligible=True,
        )
        self.phys_variant = ProductVariant.objects.create(
            product=self.phys_product,
            sku="PHYS-01",
            price=Decimal("1000.00"),
            currency="NPR",
        )
        self.phys_inventory = ProductInventory.objects.create(
            variant=self.phys_variant,
            quantity=10,
            reserved_quantity=0,
            low_stock_threshold=1,
        )

        # Digital product
        self.dig_product = Product.objects.create(
            vendor=self.vendor,
            category=self.category,
            title="E-Book Guide",
            slug="ebook-guide",
            product_type=Product.TYPE_DIGITAL,
            approval_status=Product.STATUS_APPROVED,
            is_active=True,
            is_cod_eligible=False,
        )
        uploaded = SimpleUploadedFile("guide.pdf", b"%PDF-1.4 Guide content", content_type="application/pdf")
        self.dig_asset = ProductDigitalAsset.objects.create(
            product=self.dig_product,
            file=uploaded,
            file_name="guide.pdf",
            max_downloads_per_purchase=3,
            download_validity_days=7,
        )
        self.dig_variant = ProductVariant.objects.create(
            product=self.dig_product,
            sku="DIG-01",
            price=Decimal("500.00"),
            currency="NPR",
        )

    def _create_online_order(self, with_digital=True, user=None):
        """Helper to create an order awaiting online payment with stock reserved (created by staff or testing)."""
        target_user = user or self.staff_user
        cart = Cart.objects.create(user=target_user)
        CartItem.objects.create(cart=cart, variant=self.phys_variant, quantity=1, unit_price_snapshot=self.phys_variant.price)
        if with_digital:
            CartItem.objects.create(cart=cart, variant=self.dig_variant, quantity=1, unit_price_snapshot=self.dig_variant.price)

        address = ShippingAddress.objects.create(
            user=target_user,
            full_name="Flow Staff Buyer",
            street_address_1="New Baneshwor, Ward 10",
            city="Kathmandu",
            district="Kathmandu",
            province="Bagmati",
            country="NP",
        )

        order = CheckoutService.prepare_checkout(
            cart=cart,
            shipping_address=address,
            payment_method=Order.PAYMENT_METHOD_ONLINE,
            user=target_user,
            idempotency_key=f"flow-{uuid.uuid4().hex[:8]}",
        )
        return order

    def test_public_user_cannot_initiate_online_payment(self):
        """Mandatory launch security blocker: non-staff public users receive HTTP 403."""
        order = self._create_online_order(user=self.staff_user)
        # Public customer attempts to access dummy initiate route
        self.client.force_login(self.customer)
        url = reverse("orders:initiate_online_payment", kwargs={"order_number": order.order_number})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_public_user_cannot_tamper_payment_callback_with_client_flags(self):
        """Mandatory launch security blocker: mock_status=success query param gives HTTP 403 and never marks order paid."""
        order = self._create_online_order(user=self.staff_user)
        self.client.force_login(self.customer)
        callback_url = reverse("orders:payment_callback", kwargs={"order_number": order.order_number})
        response = self.client.get(f"{callback_url}?mock_status=success&gateway_payment_id=HACK-123")
        self.assertEqual(response.status_code, 403)

        # Order remains strictly unpaid
        order.refresh_from_db()
        self.assertEqual(order.online_payment_status, Order.ONLINE_STATUS_UNPAID)
        self.assertEqual(order.order_status, Order.ORDER_STATUS_PENDING)

    def test_public_user_cannot_add_digital_product_to_cart(self):
        """Digital products are preview-only for public launch; add-to-cart redirects with warning."""
        self.client.force_login(self.customer)
        add_url = reverse("cart:add", kwargs={"variant_id": self.dig_variant.id})
        detail_url = reverse("store:product_detail", kwargs={"slug": self.dig_product.slug})
        response = self.client.post(add_url, {"quantity": 1, "next": detail_url}, follow=True)
        self.assertRedirects(response, detail_url)
        self.assertContains(response, "preview mode")
        # Ensure cart is empty
        cart = Cart.objects.filter(user=self.customer).first()
        if cart:
            self.assertEqual(cart.items.count(), 0)

    def test_public_user_checkout_rejects_digital_product_and_online_payment(self):
        """CheckoutForm enforces validation against dummy online payment for public non-staff users."""
        form = CheckoutForm(
            data={
                "full_name": "Flow Buyer",
                "phone": "9841234567",
                "street_address_1": "New Baneshwor, Ward 10",
                "city": "Kathmandu",
                "district": "Kathmandu",
                "province": "Bagmati",
                "country": "NP",
                "payment_method": "online",
            },
            user=self.customer,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("payment_method", form.errors)
        self.assertIn("Online payments are currently disabled", form.errors["payment_method"][0])

    def test_staff_initiate_online_payment_redirects_to_callback(self):
        self.client.force_login(self.staff_user)
        order = self._create_online_order(user=self.staff_user)

        url = reverse("orders:initiate_online_payment", kwargs={"order_number": order.order_number})
        response = self.client.get(url)

        # Dummy adapter immediately redirects to callback url with simulated success payload
        self.assertEqual(response.status_code, 302)
        self.assertIn("callback", response.url)
        self.assertIn("mock_status=success", response.url)

    def test_staff_payment_callback_success_confirms_order_and_creates_digital_delivery(self):
        self.client.force_login(self.staff_user)
        order = self._create_online_order(with_digital=True, user=self.staff_user)

        callback_url = reverse("orders:payment_callback", kwargs={"order_number": order.order_number})
        response = self.client.get(f"{callback_url}?mock_status=success&gateway_payment_id=DUMMY-TX-123")

        self.assertRedirects(response, reverse("orders:customer_order_detail", kwargs={"order_number": order.order_number}))

        order.refresh_from_db()
        self.assertEqual(order.online_payment_status, Order.ONLINE_STATUS_PAID)
        self.assertEqual(order.order_status, Order.ORDER_STATUS_PROCESSING)

        # Verify inventory reservation was converted to deduction
        self.phys_inventory.refresh_from_db()
        self.assertEqual(self.phys_inventory.quantity, 9)
        self.assertEqual(self.phys_inventory.reserved_quantity, 0)

        # Verify digital delivery was generated
        digital_delivs = DigitalDelivery.objects.filter(order_item__suborder__master_order=order)
        self.assertEqual(digital_delivs.count(), 1)
        delivery = digital_delivs.first()
        self.assertEqual(delivery.max_downloads, 5)
        self.assertFalse(delivery.is_revoked)

    def test_staff_payment_callback_failure_marks_payment_failed_and_preserves_retry(self):
        self.client.force_login(self.staff_user)
        order = self._create_online_order(user=self.staff_user)

        callback_url = reverse("orders:payment_callback", kwargs={"order_number": order.order_number})
        response = self.client.get(f"{callback_url}?mock_status=failure")

        self.assertRedirects(response, reverse("orders:customer_order_detail", kwargs={"order_number": order.order_number}))

        order.refresh_from_db()
        self.assertEqual(order.online_payment_status, Order.ONLINE_STATUS_UNPAID)
        payment = order.payments.first()
        self.assertEqual(payment.status, OrderPayment.STATUS_FAILED)

        # Order detail allows retry for staff
        detail_res = self.client.get(reverse("orders:customer_order_detail", kwargs={"order_number": order.order_number}))
        self.assertContains(detail_res, "Simulate Payment (Staff Only)")

    def test_vendor_suborder_shipping_and_delivery_lifecycle(self):
        # Public customer creates a physical COD order
        cart = Cart.objects.create(user=self.customer)
        CartItem.objects.create(cart=cart, variant=self.phys_variant, quantity=1, unit_price_snapshot=self.phys_variant.price)
        address = ShippingAddress.objects.create(
            user=self.customer,
            full_name="Flow Buyer",
            street_address_1="New Baneshwor, Ward 10",
            city="Kathmandu",
            district="Kathmandu",
            province="Bagmati",
            country="NP",
        )
        order = CheckoutService.prepare_checkout(
            cart=cart,
            shipping_address=address,
            payment_method=Order.PAYMENT_METHOD_COD,
            user=self.customer,
        )
        OrderWorkflowService.confirm_cod_order(order)

        suborder = order.suborders.first()
        self.assertEqual(suborder.fulfillment_status, SubOrder.FULFILLMENT_PROCESSING)

        # Vendor logs in and ships suborder
        self.client.force_login(self.vendor_user)
        suborder_url = reverse("orders:vendor_suborder_detail", kwargs={"suborder_number": suborder.suborder_number})

        # POST action='ship' with carrier & tracking
        ship_res = self.client.post(
            suborder_url,
            {"action": "ship", "carrier": "Nepal Post Express", "tracking_number": "NP-789012"},
        )
        self.assertRedirects(ship_res, suborder_url)

        suborder.refresh_from_db()
        self.assertEqual(suborder.fulfillment_status, SubOrder.FULFILLMENT_SHIPPED)
        self.assertEqual(suborder.shipping_carrier, "Nepal Post Express")
        self.assertEqual(suborder.tracking_number, "NP-789012")

        # POST action='deliver'
        deliver_res = self.client.post(suborder_url, {"action": "deliver"})
        self.assertRedirects(deliver_res, suborder_url)

        suborder.refresh_from_db()
        self.assertEqual(suborder.fulfillment_status, SubOrder.FULFILLMENT_DELIVERED)

        # Verify COD collection status
        order.refresh_from_db()
        self.assertEqual(order.cod_collection_status, Order.COD_STATUS_COLLECTED_BY_COURIER)

        # Reconcile courier remittance
        OrderWorkflowService.reconcile_cod_remittance(suborder, courier_remittance_ref="REMIT-NP-999")
        order.refresh_from_db()
        self.assertEqual(order.cod_collection_status, Order.COD_STATUS_RECONCILED)
        payment = order.payments.first()
        self.assertEqual(payment.status, OrderPayment.STATUS_SUCCESSFUL)

    def test_admin_order_list_access_control(self):
        # Anonymous user gets redirected to admin login
        anon_res = self.client.get(reverse("orders:admin_order_list"))
        self.assertEqual(anon_res.status_code, 302)
        self.assertIn("login", anon_res.url)

        # Regular customer gets redirected (not staff)
        self.client.force_login(self.customer)
        cust_res = self.client.get(reverse("orders:admin_order_list"))
        self.assertEqual(cust_res.status_code, 302)

        # Staff user gets 200 OK and sees orders
        self.client.force_login(self.staff_user)
        staff_res = self.client.get(reverse("orders:admin_order_list"))
        self.assertEqual(staff_res.status_code, 200)
        self.assertTemplateUsed(staff_res, "orders/admin_order_list.html")
