import concurrent.futures
from datetime import timedelta
from decimal import Decimal
import os
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from cart.models import Cart, CartItem
from orders.models import DigitalDelivery, Order, OrderPayment, SubOrder
from orders.services.checkout_service import CheckoutService
from orders.services.digital_delivery_service import DigitalDeliveryService
from orders.services.order_workflow_service import OrderWorkflowService
from store.models import Category, Product, ProductDigitalAsset, ProductVariant
from store.storage import protected_storage
from vendors.models import VendorProfile

User = get_user_model()


class DigitalDeliveryTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.customer = User.objects.create_user(username="digital_buyer", email="buyer@test.com", password="pass")
        self.unauth_user = User.objects.create_user(username="stranger", email="stranger@test.com", password="pass")

        self.vendor_user = User.objects.create_user(username="digital_seller", email="seller@test.com", password="pass")
        self.vendor = VendorProfile.objects.create(
            user=self.vendor_user,
            store_name="Digital Academy",
            slug="digital-academy",
            commission_rate=Decimal("10.00"),
            status=VendorProfile.STATUS_ACTIVE,
        )

        self.category = Category.objects.create(name="Digital", slug="digital")

        # Create digital product with real protected file
        self.product = Product.objects.create(
            vendor=self.vendor,
            category=self.category,
            title="Advanced Python PDF Guide",
            slug="python-pdf-guide",
            product_type=Product.TYPE_DIGITAL,
            approval_status=Product.STATUS_APPROVED,
            is_active=True,
            is_cod_eligible=False,
        )

        # Upload dummy file into protected storage
        file_content = b"%PDF-1.4 Fake PDF Content for Automated Testing"
        uploaded = SimpleUploadedFile("python_guide.pdf", file_content, content_type="application/pdf")
        self.asset = ProductDigitalAsset.objects.create(
            product=self.product,
            file=uploaded,
            file_name="python_guide.pdf",
            file_size_bytes=len(file_content),
            checksum_sha256="abc123sha256",
            max_downloads_per_purchase=3,
            download_validity_days=30,
        )

        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku="DIG-PY-01",
            price=Decimal("1200.00"),
            currency="NPR",
        )

    def _create_paid_digital_order(self):
        cart = Cart.objects.create(user=self.customer, currency="NPR")
        CartItem.objects.create(cart=cart, variant=self.variant, quantity=1, unit_price_snapshot=Decimal("1200.00"))

        order = CheckoutService.prepare_checkout(
            cart=cart,
            user=self.customer,
            payment_method=Order.PAYMENT_METHOD_ONLINE,
        )
        payment = order.payments.first()
        OrderWorkflowService.confirm_online_payment(payment, gateway_payment_id="TXN-DIG-PAID")
        order.refresh_from_db()
        return order

    def test_successful_digital_download_streaming(self):
        order = self._create_paid_digital_order()
        suborder = order.suborders.first()
        item = suborder.items.first()

        delivery = DigitalDelivery.objects.filter(order_item=item).first()
        self.assertIsNotNone(delivery)
        self.assertEqual(delivery.download_count, 0)
        self.assertEqual(delivery.max_downloads, 5)

        # Customer downloads file
        self.client.force_login(self.customer)
        url = reverse("orders:download_digital_asset", kwargs={"download_token": delivery.download_token})
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Disposition"], 'attachment; filename="python_guide.pdf"')
        self.assertEqual(b"".join(resp.streaming_content), b"%PDF-1.4 Fake PDF Content for Automated Testing")

        delivery.refresh_from_db()
        self.assertEqual(delivery.download_count, 1)

    def test_download_limit_enforcement(self):
        order = self._create_paid_digital_order()
        item = order.suborders.first().items.first()
        delivery = DigitalDelivery.objects.get(order_item=item)

        # Set count to max
        delivery.download_count = delivery.max_downloads
        delivery.save()

        self.client.force_login(self.customer)
        url = reverse("orders:download_digital_asset", kwargs={"download_token": delivery.download_token})
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 403)
        self.assertIn("Maximum download limit", resp.content.decode())

    def test_expired_token_rejected(self):
        order = self._create_paid_digital_order()
        item = order.suborders.first().items.first()
        delivery = DigitalDelivery.objects.get(order_item=item)

        # Expire token
        delivery.expires_at = timezone.now() - timedelta(days=1)
        delivery.save()

        self.client.force_login(self.customer)
        url = reverse("orders:download_digital_asset", kwargs={"download_token": delivery.download_token})
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 410)
        self.assertIn("expired", resp.content.decode().lower())

    def test_revoked_token_rejected_after_cancellation(self):
        order = self._create_paid_digital_order()
        suborder = order.suborders.first()
        delivery = DigitalDelivery.objects.get(order_item=suborder.items.first())

        # Cancel suborder
        OrderWorkflowService.cancel_suborder(suborder, reason="Refunded")
        delivery.refresh_from_db()
        self.assertTrue(delivery.is_revoked)

        self.client.force_login(self.customer)
        url = reverse("orders:download_digital_asset", kwargs={"download_token": delivery.download_token})
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 410)
        self.assertIn("revoked", resp.content.decode().lower())

    def test_unauthorized_customer_cannot_download(self):
        order = self._create_paid_digital_order()
        delivery = DigitalDelivery.objects.get(order_item=order.suborders.first().items.first())

        # Different user tries to use token
        self.client.force_login(self.unauth_user)
        url = reverse("orders:download_digital_asset", kwargs={"download_token": delivery.download_token})
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 403)
        self.assertIn("not authorized", resp.content.decode().lower())

    def test_tampered_or_invalid_token_returns_404(self):
        self.client.force_login(self.customer)
        # Random non-existent 64-char token
        fake_token = "f" * 64
        url = reverse("orders:download_digital_asset", kwargs={"download_token": fake_token})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)

        # Invalid length
        url_short = reverse("orders:download_digital_asset", kwargs={"download_token": "abc123short"})
        resp_short = self.client.get(url_short)
        self.assertEqual(resp_short.status_code, 404)

    def test_protected_storage_cannot_leak_public_url(self):
        # Protected storage base_url is None; asset.file.url must raise ValueError
        with self.assertRaises(ValueError):
            _ = self.asset.file.url


class DigitalDeliveryConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.customer = User.objects.create_user(username="concur_buyer", email="concur_buyer@test.com", password="pass")
        self.vendor_user = User.objects.create_user(username="concur_seller", email="concur_seller@test.com", password="pass")
        self.vendor = VendorProfile.objects.create(
            user=self.vendor_user,
            store_name="Concurrency Books",
            slug="concurrency-books",
            status=VendorProfile.STATUS_ACTIVE,
        )
        self.category = Category.objects.create(name="Digital Concurrency", slug="digital-concur")
        self.product = Product.objects.create(
            vendor=self.vendor,
            category=self.category,
            title="Concurrency Guide",
            slug="concurrency-guide",
            product_type=Product.TYPE_DIGITAL,
            approval_status=Product.STATUS_APPROVED,
            is_active=True,
        )
        file_content = b"%PDF-1.4 Concurrency PDF Test Data"
        uploaded = SimpleUploadedFile("concurrency.pdf", file_content, content_type="application/pdf")
        self.asset = ProductDigitalAsset.objects.create(
            product=self.product,
            file=uploaded,
            file_name="concurrency.pdf",
            file_size_bytes=len(file_content),
            checksum_sha256="testsha256concur",
            max_downloads_per_purchase=3,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku="CONC-01",
            price=Decimal("500.00"),
            currency="NPR",
        )

    def test_concurrent_downloads_cannot_exceed_max_limit(self):
        """
        Concurrency regression test:
        Fires 8 simultaneous download requests against a delivery token with max_downloads=3.
        Proves that select_for_update row locking ensures:
        - Exactly 3 requests succeed (HTTP 200).
        - Exactly 5 requests are rejected with HTTP 403 (download limit reached).
        - Final download_count is strictly 3.
        """
        cart = Cart.objects.create(user=self.customer, currency="NPR")
        CartItem.objects.create(cart=cart, variant=self.variant, quantity=1, unit_price_snapshot=Decimal("500.00"))
        order = CheckoutService.prepare_checkout(cart=cart, user=self.customer, payment_method=Order.PAYMENT_METHOD_ONLINE)
        payment = order.payments.first()
        OrderWorkflowService.confirm_online_payment(payment, gateway_payment_id="TXN-CONCUR-PAID")
        order.refresh_from_db()

        delivery = DigitalDelivery.objects.get(order_item=order.suborders.first().items.first())
        delivery.max_downloads = 3
        delivery.save()

        token = delivery.download_token
        user_id = self.customer.id

        def worker_request():
            connection.close()
            user = User.objects.get(id=user_id)
            is_valid, reason, status, deliv = DigitalDeliveryService.claim_and_reserve_download(
                download_token=token,
                user=user,
            )
            return status

        # Run 8 concurrent worker requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(worker_request) for _ in range(8)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        connection.close()
        delivery.refresh_from_db()

        success_count = results.count(200)
        limit_rejected_count = results.count(403)

        self.assertEqual(success_count, 3)
        self.assertEqual(limit_rejected_count, 5)
        self.assertEqual(delivery.download_count, 3)
        self.assertLessEqual(delivery.download_count, delivery.max_downloads)

