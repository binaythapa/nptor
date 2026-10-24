from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from cart.models import Cart, CartItem
from cart.services.cart_service import CartService
from store.models import Category, Product, ProductInventory, ProductVariant
from vendors.models import VendorProfile

User = get_user_model()


class CartViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="cart_shopper", email="shopper@test.com", password="pass")
        self.vendor_user = User.objects.create_user(username="cart_seller", email="seller@test.com", password="pass")
        self.vendor = VendorProfile.objects.create(
            user=self.vendor_user,
            store_name="Book Haven",
            slug="book-haven",
            status=VendorProfile.STATUS_ACTIVE,
        )
        self.category = Category.objects.create(name="Study Notes", slug="study-notes")
        self.product = Product.objects.create(
            vendor=self.vendor,
            category=self.category,
            title="Loksewa General Knowledge 2026",
            slug="loksewa-gk-2026",
            product_type=Product.TYPE_PHYSICAL,
            approval_status=Product.STATUS_APPROVED,
            is_active=True,
            is_cod_eligible=True,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku="LS-GK-01",
            price=Decimal("750.00"),
            currency="NPR",
        )
        self.inventory = ProductInventory.objects.create(
            variant=self.variant,
            quantity=10,
            reserved_quantity=0,
            low_stock_threshold=2,
        )

    def test_anonymous_visitor_can_add_to_cart_and_view(self):
        # 1. Anonymous visitor adds product to cart
        add_url = reverse("cart:add", kwargs={"variant_id": self.variant.id})
        resp = self.client.post(add_url, {"quantity": 2})
        self.assertEqual(resp.status_code, 302)

        # 2. View cart
        cart_url = reverse("cart:detail")
        resp_view = self.client.get(cart_url)
        self.assertEqual(resp_view.status_code, 200)
        self.assertContains(resp_view, "Loksewa General Knowledge 2026")
        self.assertContains(resp_view, "NPR 1500.00")

    def test_anonymous_cart_merges_upon_login(self):
        # Anonymous adds item
        self.client.post(reverse("cart:add", kwargs={"variant_id": self.variant.id}), {"quantity": 1})
        session_key = self.client.session.session_key
        guest_cart = Cart.objects.get(session_key=session_key)
        self.assertEqual(guest_cart.items.count(), 1)

        # User logs in
        self.client.force_login(self.user)
        # Hitting cart view merges guest cart into user cart
        resp = self.client.get(reverse("cart:detail"))
        self.assertEqual(resp.status_code, 200)

        user_cart = Cart.objects.get(user=self.user)
        self.assertEqual(user_cart.items.count(), 1)
        self.assertEqual(user_cart.items.first().quantity, 1)
        self.assertFalse(Cart.objects.filter(session_key=session_key, user__isnull=True).exists())

    def test_cart_update_quantity(self):
        self.client.force_login(self.user)
        self.client.post(reverse("cart:add", kwargs={"variant_id": self.variant.id}), {"quantity": 1})
        cart = Cart.objects.get(user=self.user)
        item = cart.items.first()

        # Update quantity to 4
        resp = self.client.post(reverse("cart:update", kwargs={"item_id": item.id}), {"quantity": 4})
        self.assertEqual(resp.status_code, 302)

        item.refresh_from_db()
        self.assertEqual(item.quantity, 4)
        self.assertEqual(item.total_price, Decimal("3000.00"))

    def test_cart_update_to_zero_removes_item(self):
        self.client.force_login(self.user)
        self.client.post(reverse("cart:add", kwargs={"variant_id": self.variant.id}), {"quantity": 2})
        cart = Cart.objects.get(user=self.user)
        item = cart.items.first()

        resp = self.client.post(reverse("cart:update", kwargs={"item_id": item.id}), {"quantity": 0})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(cart.items.count(), 0)

    def test_cart_remove_item(self):
        self.client.force_login(self.user)
        self.client.post(reverse("cart:add", kwargs={"variant_id": self.variant.id}), {"quantity": 1})
        cart = Cart.objects.get(user=self.user)
        item = cart.items.first()

        resp = self.client.post(reverse("cart:remove", kwargs={"item_id": item.id}))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(cart.items.count(), 0)

    def test_cart_clear(self):
        self.client.force_login(self.user)
        self.client.post(reverse("cart:add", kwargs={"variant_id": self.variant.id}), {"quantity": 2})
        resp = self.client.post(reverse("cart:clear"))
        self.assertEqual(resp.status_code, 302)
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.items.count(), 0)

    def test_adding_more_than_available_stock_is_rejected(self):
        self.client.force_login(self.user)
        # Attempt to add 15 when only 10 available
        resp = self.client.post(reverse("cart:add", kwargs={"variant_id": self.variant.id}), {"quantity": 15})
        self.assertEqual(resp.status_code, 302)
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.items.count(), 0)

    def test_cart_detail_warns_on_price_change(self):
        self.client.force_login(self.user)
        self.client.post(reverse("cart:add", kwargs={"variant_id": self.variant.id}), {"quantity": 1})

        # Seller changes variant price in database
        self.variant.price = Decimal("899.00")
        self.variant.save()

        resp = self.client.get(reverse("cart:detail"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "changed from NPR 750.00 to NPR 899.00")
