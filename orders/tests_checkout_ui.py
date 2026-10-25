import concurrent.futures
from decimal import Decimal
import uuid
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from cart.models import Cart, CartItem, StockReservation
from orders.models import Order, OrderItem, ShippingAddress, SubOrder
from store.models import Category, Product, ProductDigitalAsset, ProductInventory, ProductVariant
from vendors.models import VendorProfile

User = get_user_model()


class CheckoutUITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.customer = User.objects.create_user(username="checkout_buyer", email="buyer@test.com", password="pass")
        self.staff_user = User.objects.create_user(username="checkout_staff", email="staff@test.com", password="pass", is_staff=True)
        self.vendor_user = User.objects.create_user(username="checkout_seller", email="seller@test.com", password="pass")
        self.vendor = VendorProfile.objects.create(
            user=self.vendor_user,
            store_name="Himalaya Publishers",
            slug="himalaya-publishers",
            commission_rate=Decimal("12.00"),
            status=VendorProfile.STATUS_ACTIVE,
            is_cod_enabled=True,
        )
        self.category = Category.objects.create(name="Textbooks", slug="textbooks")

        # Physical product
        self.phys_product = Product.objects.create(
            vendor=self.vendor,
            category=self.category,
            title="Loksewa Officer Preparation Manual",
            slug="loksewa-manual",
            product_type=Product.TYPE_PHYSICAL,
            approval_status=Product.STATUS_APPROVED,
            is_active=True,
            is_cod_eligible=True,
        )
        self.phys_variant = ProductVariant.objects.create(
            product=self.phys_product,
            sku="LOK-OFF-01",
            price=Decimal("1200.00"),
            currency="NPR",
        )
        self.inventory = ProductInventory.objects.create(
            variant=self.phys_variant,
            quantity=5,
            reserved_quantity=0,
            low_stock_threshold=1,
        )

        # Digital product
        self.dig_product = Product.objects.create(
            vendor=self.vendor,
            category=self.category,
            title="Officer Exam PDF Mock Questions",
            slug="officer-mock-pdf",
            product_type=Product.TYPE_DIGITAL,
            approval_status=Product.STATUS_APPROVED,
            is_active=True,
            is_cod_eligible=False,
        )
        uploaded = SimpleUploadedFile("mock.pdf", b"%PDF-1.4 Mock", content_type="application/pdf")
        self.dig_asset = ProductDigitalAsset.objects.create(
            product=self.dig_product,
            file=uploaded,
            file_name="mock.pdf",
            file_size_bytes=100,
            checksum_sha256="mockpdfsha256",
        )
        self.dig_variant = ProductVariant.objects.create(
            product=self.dig_product,
            sku="DIG-MOCK-01",
            price=Decimal("450.00"),
            currency="NPR",
        )

    def test_unauthenticated_checkout_redirects_to_login(self):
        resp = self.client.get(reverse("orders:checkout"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp.url)

    def test_empty_cart_checkout_redirects_to_cart_detail(self):
        self.client.force_login(self.customer)
        resp = self.client.get(reverse("orders:checkout"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("cart:detail"), resp.url)

    def test_successful_physical_checkout_flow_cod(self):
        """Authorized launch flow: customer orders physical items via Cash on Delivery."""
        self.client.force_login(self.customer)
        cart = Cart.objects.create(user=self.customer, currency="NPR")
        CartItem.objects.create(cart=cart, variant=self.phys_variant, quantity=2, unit_price_snapshot=Decimal("1200.00"))

        checkout_url = reverse("orders:checkout")
        resp_get = self.client.get(checkout_url)
        self.assertEqual(resp_get.status_code, 200)
        self.assertContains(resp_get, "Delivery Address (Nepal Only)")

        idem_key = uuid.uuid4().hex
        payload = {
            "full_name": "Ram Bahadur",
            "phone": "9841234567",
            "street_address_1": "Putalisadak Ward 28",
            "city": "Kathmandu",
            "district": "Kathmandu",
            "province": "Bagmati",
            "postal_code": "44600",
            "country": "NP",
            "payment_method": "cod",
            "idempotency_key": idem_key,
        }

        resp_post = self.client.post(checkout_url, payload)
        self.assertEqual(resp_post.status_code, 302)

        # Order created
        order = Order.objects.filter(user=self.customer, idempotency_key=idem_key).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.grand_total, Decimal("2400.00"))
        self.assertEqual(order.payment_method, Order.PAYMENT_METHOD_COD)
        self.assertEqual(order.online_payment_status, Order.ONLINE_STATUS_NOT_APPLICABLE)
        self.assertEqual(order.suborders.count(), 1)

        suborder = order.suborders.first()
        self.assertEqual(suborder.items.count(), 1)
        self.assertEqual(suborder.platform_commission, Decimal("288.00"))  # 12% of 2400

        # Stock deducted upon COD confirmation
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.reserved_quantity, 0)
        self.assertEqual(self.inventory.quantity, 3)
        self.assertEqual(self.inventory.available_quantity, 3)

        # Cart items cleared
        cart.refresh_from_db()
        self.assertEqual(cart.items.count(), 0)

        # Redirects to order detail
        self.assertIn(order.order_number, resp_post.url)

    def test_public_checkout_rejects_online_payment_method(self):
        """Public checkout form must reject attempts to submit payment_method='online'."""
        self.client.force_login(self.customer)
        cart = Cart.objects.create(user=self.customer, currency="NPR")
        CartItem.objects.create(cart=cart, variant=self.phys_variant, quantity=1, unit_price_snapshot=Decimal("1200.00"))

        checkout_url = reverse("orders:checkout")
        payload = {
            "full_name": "Ram Bahadur",
            "phone": "9841234567",
            "street_address_1": "Putalisadak Ward 28",
            "city": "Kathmandu",
            "district": "Kathmandu",
            "province": "Bagmati",
            "country": "NP",
            "payment_method": "online",
            "idempotency_key": uuid.uuid4().hex,
        }

        resp = self.client.post(checkout_url, payload)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Online payments are currently disabled for public orders.")
        self.assertEqual(Order.objects.count(), 0)

    def test_public_checkout_rejects_digital_products(self):
        """Public checkout view must reject carts containing digital items and redirect to cart."""
        self.client.force_login(self.customer)
        cart = Cart.objects.create(user=self.customer, currency="NPR")
        CartItem.objects.create(cart=cart, variant=self.dig_variant, quantity=1, unit_price_snapshot=Decimal("450.00"))

        checkout_url = reverse("orders:checkout")
        payload = {
            "payment_method": "cod",
            "idempotency_key": uuid.uuid4().hex,
        }

        resp = self.client.post(checkout_url, payload)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("cart:detail"), resp.url)
        self.assertEqual(Order.objects.count(), 0)

    def test_staff_successful_digital_checkout(self):
        """Staff users can test digital checkout in staging/internal mode."""
        self.client.force_login(self.staff_user)
        cart = Cart.objects.create(user=self.staff_user, currency="NPR")
        CartItem.objects.create(cart=cart, variant=self.dig_variant, quantity=1, unit_price_snapshot=Decimal("450.00"))

        checkout_url = reverse("orders:checkout")
        resp_get = self.client.get(checkout_url)
        self.assertEqual(resp_get.status_code, 200)
        self.assertContains(resp_get, "Digital Purchase")

        idem_key = uuid.uuid4().hex
        payload = {
            "payment_method": "online",
            "idempotency_key": idem_key,
        }

        resp_post = self.client.post(checkout_url, payload)
        self.assertEqual(resp_post.status_code, 302)

        order = Order.objects.filter(user=self.staff_user, idempotency_key=idem_key).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.grand_total, Decimal("450.00"))
        self.assertIsNone(order.shipping_address)

    def test_duplicate_submission_idempotency_prevents_duplicate_orders(self):
        self.client.force_login(self.customer)
        cart = Cart.objects.create(user=self.customer, currency="NPR")
        CartItem.objects.create(cart=cart, variant=self.phys_variant, quantity=1, unit_price_snapshot=Decimal("1200.00"))

        idem_key = "IDEM-TEST-DUPLICATE-999"
        payload = {
            "full_name": "Sita Sharma",
            "phone": "9812345678",
            "street_address_1": "Lakeside Ward 6",
            "city": "Pokhara",
            "district": "Kaski",
            "province": "Gandaki",
            "country": "NP",
            "payment_method": "cod",
            "idempotency_key": idem_key,
        }

        # First submission
        resp1 = self.client.post(reverse("orders:checkout"), payload)
        self.assertEqual(resp1.status_code, 302)
        self.assertEqual(Order.objects.filter(idempotency_key=idem_key).count(), 1)

        # Second repeated submission with same key
        resp2 = self.client.post(reverse("orders:checkout"), payload)
        self.assertEqual(resp2.status_code, 302)
        # Still exactly 1 order
        self.assertEqual(Order.objects.filter(idempotency_key=idem_key).count(), 1)

    def test_checkout_rejects_insufficient_stock_and_preserves_cart(self):
        self.client.force_login(self.customer)
        cart = Cart.objects.create(user=self.customer, currency="NPR")
        CartItem.objects.create(cart=cart, variant=self.phys_variant, quantity=3, unit_price_snapshot=Decimal("1200.00"))

        # Inventory is exhausted right before checkout submit
        self.inventory.quantity = 1
        self.inventory.save()

        payload = {
            "full_name": "Hari Prasad",
            "phone": "9800000000",
            "street_address_1": "Traffic Chowk",
            "city": "Biratnagar",
            "country": "NP",
            "payment_method": "cod",
            "idempotency_key": uuid.uuid4().hex,
        }

        resp = self.client.post(reverse("orders:checkout"), payload)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("cart:detail"), resp.url)

        # No order created; cart items preserved
        self.assertEqual(Order.objects.count(), 0)
        cart.refresh_from_db()
        self.assertEqual(cart.items.count(), 1)

    def test_checkout_handles_price_change_gracefully(self):
        self.client.force_login(self.customer)
        cart = Cart.objects.create(user=self.customer, currency="NPR")
        item = CartItem.objects.create(cart=cart, variant=self.phys_variant, quantity=1, unit_price_snapshot=Decimal("1200.00"))

        # Price changes in catalog
        self.phys_variant.price = Decimal("1350.00")
        self.phys_variant.save()

        # Checkout view detects price change and renders updated grand total
        resp = self.client.get(reverse("orders:checkout"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "NPR 1350.00")

        item.refresh_from_db()
        self.assertEqual(item.unit_price_snapshot, Decimal("1350.00"))


    def test_public_checkout_rejects_demonstration_products(self):
        """Public checkout view must reject carts containing demonstration items and redirect to cart."""
        demo_prod = Product.objects.create(
            title="Demo Running Shoes",
            slug="demo-running-shoes-test",
            category=self.category,
            product_type=Product.TYPE_PHYSICAL,
            approval_status=Product.STATUS_APPROVED,
            is_active=True,
            specifications={"is_demo": True},
        )
        demo_var = ProductVariant.objects.create(
            product=demo_prod,
            sku="DEMO-SHOE-01",
            price=Decimal("3500.00"),
            currency="NPR",
        )
        ProductInventory.objects.create(variant=demo_var, quantity=20, reserved_quantity=0)

        self.client.force_login(self.customer)
        # Add to cart
        cart = Cart.objects.create(user=self.customer, currency="NPR")
        CartItem.objects.create(cart=cart, variant=demo_var, quantity=1, unit_price_snapshot=Decimal("3500.00"))

        checkout_url = reverse("orders:checkout")
        resp = self.client.get(checkout_url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("cart:detail"), resp.url)


class ConcurrentCheckoutUITests(TransactionTestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username="concur_u1", email="u1@test.com", password="pass")
        self.user2 = User.objects.create_user(username="concur_u2", email="u2@test.com", password="pass")
        self.vendor_user = User.objects.create_user(username="concur_v1", email="v1@test.com", password="pass")
        self.vendor = VendorProfile.objects.create(
            user=self.vendor_user,
            store_name="Rare Books",
            slug="rare-books",
            status=VendorProfile.STATUS_ACTIVE,
            is_cod_enabled=True,
        )
        self.category = Category.objects.create(name="Rare", slug="rare")
        self.product = Product.objects.create(
            vendor=self.vendor,
            category=self.category,
            title="Last Available Rare Manuscript",
            slug="rare-manuscript",
            product_type=Product.TYPE_PHYSICAL,
            approval_status=Product.STATUS_APPROVED,
            is_active=True,
            is_cod_eligible=True,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku="RARE-001",
            price=Decimal("9999.00"),
            currency="NPR",
        )
        # Exactly 1 unit available in stock
        self.inventory = ProductInventory.objects.create(
            variant=self.variant,
            quantity=1,
            reserved_quantity=0,
        )

    def test_concurrent_checkout_competing_for_single_unit_prevents_oversell(self):
        # User 1 cart has 1 unit
        cart1 = Cart.objects.create(user=self.user1, currency="NPR")
        CartItem.objects.create(cart=cart1, variant=self.variant, quantity=1, unit_price_snapshot=Decimal("9999.00"))

        # User 2 cart has 1 unit
        cart2 = Cart.objects.create(user=self.user2, currency="NPR")
        CartItem.objects.create(cart=cart2, variant=self.variant, quantity=1, unit_price_snapshot=Decimal("9999.00"))

        def do_checkout(user):
            connection.close()
            client = Client()
            client.force_login(user)
            payload = {
                "full_name": f"{user.username} Buyer",
                "phone": "9841000000",
                "street_address_1": "Main St",
                "city": "Kathmandu",
                "district": "Kathmandu",
                "province": "Bagmati",
                "country": "NP",
                "payment_method": "cod",
                "idempotency_key": uuid.uuid4().hex,
            }
            resp = client.post(reverse("orders:checkout"), payload)
            return resp.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(do_checkout, u) for u in [self.user1, self.user2]]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        connection.close()

        # Both requests finish safely
        self.assertEqual(len(results), 2)
        # Exactly 1 order is created (no overselling)
        self.assertEqual(Order.objects.count(), 1)
        self.inventory.refresh_from_db()
        # Stock reservation was converted to deduction for COD order
        self.assertEqual(self.inventory.reserved_quantity, 0)
        self.assertEqual(self.inventory.quantity, 0)
        self.assertEqual(self.inventory.available_quantity, 0)



class GeolocationAndCartDemoTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.customer = User.objects.create_user(username="geo_buyer", email="geobuyer@test.com", password="pass")
        self.category = Category.objects.create(name="Stationery", slug="stationery")
        
        # Genuine product
        self.real_product = Product.objects.create(
            title="NPTOR Academic Workbook",
            slug="nptor-academic-workbook",
            category=self.category,
            product_type="physical",
            approval_status="approved",
            is_active=True,
            is_cod_eligible=True,
            specifications={"is_demo": False},
        )
        self.real_variant = ProductVariant.objects.create(
            product=self.real_product,
            sku="NPTOR-WB-01",
            price=Decimal("850.00"),
            currency="NPR",
        )
        self.real_inv = ProductInventory.objects.create(variant=self.real_variant, quantity=10, reserved_quantity=0)

        # Demo product
        self.demo_product = Product.objects.create(
            title="Demo Universal Fast Cable",
            slug="demo-universal-fast-cable",
            category=self.category,
            product_type="physical",
            approval_status="approved",
            is_active=True,
            is_cod_eligible=True,
            specifications={"is_demo": True},
        )
        self.demo_variant = ProductVariant.objects.create(
            product=self.demo_product,
            sku="DEMO-CBL-01",
            price=Decimal("650.00"),
            currency="NPR",
        )
        self.demo_inv = ProductInventory.objects.create(variant=self.demo_variant, quantity=25, reserved_quantity=0)

    def test_gps_reverse_geocode_api_nepal_success(self):
        """API successfully reverse-geocodes Nepal coordinates to structured address."""
        from unittest.mock import patch, MagicMock

        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "display_name": "Putalisadak, Kathmandu, Bagmati Province, 44600, Nepal",
            "address": {
                "road": "Putalisadak",
                "neighbourhood": "Ward 28",
                "city": "Kathmandu Metropolitan City",
                "county": "Kathmandu District",
                "state": "Bagmati Province",
                "postcode": "44600",
                "country": "Nepal",
                "country_code": "np",
            },
        }

        with patch("requests.get", return_value=mock_resp):
            payload = {"latitude": 27.700769, "longitude": 85.300140}
            # Test POST
            resp = self.client.post(
                reverse("orders:api_reverse_geocode"),
                data=payload,
                content_type="application/json",
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertTrue(data["success"])
            self.assertTrue(data["is_serviceable"])
            addr = data["address"]
            self.assertEqual(addr["city"], "Kathmandu")
            self.assertEqual(addr["district"], "Kathmandu")
            self.assertEqual(addr["province"], "Bagmati")
            self.assertEqual(addr["country"], "NP")
            self.assertIn("Putalisadak", addr["street_address_1"])

            # Test GET
            resp_get = self.client.get(reverse("orders:api_reverse_geocode"), {"lat": 27.700769, "lon": 85.300140})
            self.assertEqual(resp_get.status_code, 200)
            self.assertTrue(resp_get.json()["success"])

    def test_gps_reverse_geocode_api_outside_nepal_rejected(self):
        """API rejects coordinates outside Nepal with clear serviceability guidance."""
        from unittest.mock import patch, MagicMock

        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "display_name": "Trafalgar Square, London, England, United Kingdom",
            "address": {
                "road": "Trafalgar Square",
                "city": "London",
                "country": "United Kingdom",
                "country_code": "gb",
            },
        }

        with patch("requests.get", return_value=mock_resp):
            payload = {"latitude": 51.5080, "longitude": -0.1281}
            resp = self.client.post(
                reverse("orders:api_reverse_geocode"),
                data=payload,
                content_type="application/json",
            )
            self.assertEqual(resp.status_code, 422)
            data = resp.json()
            self.assertFalse(data["success"])
            self.assertFalse(data["is_serviceable"])
            self.assertIn("United Kingdom", data["error"])
            self.assertIn("Nepal", data["error"])

    def test_gps_reverse_geocode_api_invalid_coordinates(self):
        """API validates missing or out-of-range coordinates."""
        # Missing coordinates
        resp1 = self.client.post(
            reverse("orders:api_reverse_geocode"),
            data={},
            content_type="application/json",
        )
        self.assertEqual(resp1.status_code, 400)

        # Out-of-range coordinates
        resp2 = self.client.post(
            reverse("orders:api_reverse_geocode"),
            data={"latitude": 120.0, "longitude": 200.0},
            content_type="application/json",
        )
        self.assertEqual(resp2.status_code, 422)
        self.assertIn("outside valid geographical range", resp2.json()["error"])

    def test_gps_reverse_geocode_api_network_failure_handled(self):
        """API handles reverse-geocoding network timeout gracefully."""
        import requests
        from unittest.mock import patch

        with patch("requests.get", side_effect=requests.Timeout("Connection timed out")):
            payload = {"latitude": 27.7172, "longitude": 85.3240}
            resp = self.client.post(
                reverse("orders:api_reverse_geocode"),
                data=payload,
                content_type="application/json",
            )
            self.assertEqual(resp.status_code, 422)
            data = resp.json()
            self.assertFalse(data["success"])
            self.assertIn("manually", data["error"].lower())

    def test_cart_remove_demo_action(self):
        """Action cart:remove_demo removes only demonstration items from the cart."""
        cart = Cart.objects.create(user=self.customer, currency="NPR")
        CartItem.objects.create(cart=cart, variant=self.real_variant, quantity=1, unit_price_snapshot=Decimal("850.00"))
        CartItem.objects.create(cart=cart, variant=self.demo_variant, quantity=2, unit_price_snapshot=Decimal("650.00"))

        self.assertEqual(cart.items.count(), 2)

        self.client.force_login(self.customer)
        resp = self.client.post(reverse("cart:remove_demo"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("cart:detail"), resp.url)

        cart.refresh_from_db()
        self.assertEqual(cart.items.count(), 1)
        remaining = cart.items.first()
        self.assertEqual(remaining.variant, self.real_variant)

    def test_cart_detail_renders_demo_badges_and_notice(self):
        """Cart page displays demonstration badge and notice when demo items are present."""
        cart = Cart.objects.create(user=self.customer, currency="NPR")
        CartItem.objects.create(cart=cart, variant=self.demo_variant, quantity=1, unit_price_snapshot=Decimal("650.00"))

        self.client.force_login(self.customer)
        resp = self.client.get(reverse("cart:detail"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Demonstration Showcase")
        self.assertContains(resp, "Remove Demonstration Item")
        # Proceed to Checkout is disabled for non-staff with only demo items
        self.assertContains(resp, "disabled")

    def test_genuine_purchasable_product_completes_checkout(self):
        """Customer with genuine, non-demo physical product can complete live checkout via COD."""
        self.client.force_login(self.customer)
        cart = Cart.objects.create(user=self.customer, currency="NPR")
        CartItem.objects.create(cart=cart, variant=self.real_variant, quantity=1, unit_price_snapshot=Decimal("850.00"))

        payload = {
            "full_name": "Sita Sharma",
            "phone": "9841234567",
            "street_address_1": "Baluwatar, Ward 4",
            "street_address_2": "Near Italian Embassy",
            "city": "Kathmandu",
            "district": "Kathmandu",
            "province": "Bagmati",
            "postal_code": "44600",
            "country": "NP",
            "payment_method": "cod",
            "idempotency_key": uuid.uuid4().hex,
        }

        resp = self.client.post(reverse("orders:checkout"), payload)
        self.assertEqual(resp.status_code, 302)

        # Order created successfully
        order = Order.objects.filter(user=self.customer).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.shipping_address.full_name, "Sita Sharma")
        self.assertEqual(order.shipping_address.city, "Kathmandu")
        self.assertEqual(order.payment_method, "cod")
        self.assertEqual(order.grand_total, Decimal("850.00"))

        # Inventory reserved / deducted
        self.real_inv.refresh_from_db()
        self.assertEqual(self.real_inv.quantity, 9)

    def test_customer_order_list_heading_structure(self):
        """Customer order list renders proper heading row, icon alignment, and non-overlapping subtitle."""
        self.client.force_login(self.customer)
        resp = self.client.get(reverse("orders:customer_order_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "store-page-header")
        self.assertContains(resp, "store-page-heading-row")
        self.assertContains(resp, "store-page-heading-icon")
        self.assertContains(resp, "store-page-title")
        self.assertContains(resp, "store-page-subtitle")
        self.assertContains(resp, "My Orders")
        self.assertContains(resp, "View order status, shipment tracking, and return options")

    def test_customer_order_detail_heading_structure(self):
        """Customer order detail renders proper heading row and structured header."""
        self.client.force_login(self.customer)
        addr = ShippingAddress.objects.create(
            user=self.customer,
            full_name="Binay Test",
            phone="9800000000",
            street_address_1="Kholagaal Marg",
            city="Kathmandu",
            district="Kathmandu",
            province="Bagmati",
            country="NP",
        )
        order = Order.objects.create(
            user=self.customer,
            order_number="NPTOR-ORD-TEST-HEAD",
            payment_method="cod",
            total_items_amount=Decimal("1200.00"),
            grand_total=Decimal("1200.00"),
            currency="NPR",
            shipping_address=addr,
            order_status="pending",
        )
        resp = self.client.get(reverse("orders:customer_order_detail", kwargs={"order_number": order.order_number}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "store-page-header")
        self.assertContains(resp, "store-page-heading-row")
        self.assertContains(resp, "store-page-heading-icon")
        self.assertContains(resp, "store-page-title")
        self.assertContains(resp, "store-page-subtitle")
        self.assertContains(resp, "Order #NPTOR-ORD-TEST-HEAD")
