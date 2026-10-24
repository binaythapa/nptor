from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from store.models import Category, Product, ProductVariant
from vendors.models import VendorProfile

User = get_user_model()


class StoreModerationAndIsolationTests(TestCase):
    def setUp(self):
        self.seller_a_user = User.objects.create_user(username="seller_a", email="sa@example.com", password="pass")
        self.seller_b_user = User.objects.create_user(username="seller_b", email="sb@example.com", password="pass")
        self.staff_user = User.objects.create_user(username="moderator", email="mod@example.com", password="pass", is_staff=True)
        self.buyer_user = User.objects.create_user(username="buyer_test", email="buyer@example.com", password="pass")

        self.vendor_a = VendorProfile.objects.create(
            user=self.seller_a_user,
            store_name="Vendor A Store",
            slug="vendor-a-store",
            status=VendorProfile.STATUS_ACTIVE,
        )
        self.vendor_b = VendorProfile.objects.create(
            user=self.seller_b_user,
            store_name="Vendor B Store",
            slug="vendor-b-store",
            status=VendorProfile.STATUS_ACTIVE,
        )
        self.category = Category.objects.create(name="Lab Equipment", slug="lab-equipment")

    def test_vendor_can_create_draft_product(self):
        self.client.force_login(self.seller_a_user)
        response = self.client.post(
            reverse("store:vendor_product_create"),
            data={
                "title": "Digital Multimeter Pro",
                "category": self.category.id,
                "product_type": Product.TYPE_PHYSICAL,
                "description": "High precision multimeter.",
                "is_cod_eligible": True,
                "sku": "DMM-PRO-01",
                "variant_name": "Standard",
                "price": "1850.00",
                "quantity": "25",
                "low_stock_threshold": "3",
            },
        )
        self.assertRedirects(response, reverse("store:vendor_product_list"))

        product = Product.objects.get(title="Digital Multimeter Pro")
        self.assertEqual(product.vendor, self.vendor_a)
        self.assertEqual(product.approval_status, Product.STATUS_DRAFT)
        self.assertFalse(product.is_active)
        self.assertEqual(product.variants.count(), 1)
        self.assertEqual(product.variants.first().inventory.quantity, 25)

    def test_vendor_can_submit_product_for_moderation(self):
        product = Product.objects.create(
            vendor=self.vendor_a,
            title="Oscilloscope Cable",
            slug="oscilloscope-cable",
            category=self.category,
            product_type=Product.TYPE_PHYSICAL,
            approval_status=Product.STATUS_DRAFT,
        )

        self.client.force_login(self.seller_a_user)
        res_submit = self.client.post(reverse("store:vendor_product_submit", args=[product.pk]))
        self.assertRedirects(res_submit, reverse("store:vendor_product_list"))

        product.refresh_from_db()
        self.assertEqual(product.approval_status, Product.STATUS_PENDING)
        self.assertIsNotNone(product.submitted_at)

    def test_staff_moderation_approval_workflow(self):
        product = Product.objects.create(
            vendor=self.vendor_a,
            title="Lab Power Supply 30V",
            slug="lab-power-supply-30v",
            category=self.category,
            product_type=Product.TYPE_PHYSICAL,
            approval_status=Product.STATUS_PENDING,
        )

        self.client.force_login(self.staff_user)
        res_mod = self.client.post(
            reverse("store:admin_moderate_product", args=[product.pk]),
            data={
                "action": "approve",
                "review_notes": "Meets quality standards.",
            },
        )
        self.assertRedirects(res_mod, reverse("store:admin_moderation_queue"))

        product.refresh_from_db()
        self.assertEqual(product.approval_status, Product.STATUS_APPROVED)
        self.assertTrue(product.is_active)
        self.assertEqual(product.reviewed_by, self.staff_user)
        self.assertIsNotNone(product.reviewed_at)
        self.assertEqual(product.review_notes, "Meets quality standards.")

    def test_staff_moderation_request_changes(self):
        product = Product.objects.create(
            vendor=self.vendor_a,
            title="Incomplete Kit",
            slug="incomplete-kit",
            category=self.category,
            approval_status=Product.STATUS_PENDING,
        )

        self.client.force_login(self.staff_user)
        res_mod = self.client.post(
            reverse("store:admin_moderate_product", args=[product.pk]),
            data={
                "action": "changes_required",
                "review_notes": "Please specify component quantities in description.",
            },
        )
        self.assertRedirects(res_mod, reverse("store:admin_moderation_queue"))

        product.refresh_from_db()
        self.assertEqual(product.approval_status, Product.STATUS_CHANGES_REQUIRED)
        self.assertFalse(product.is_active)

    def test_storefront_catalog_hides_unapproved_products(self):
        # 1 Approved product
        approved = Product.objects.create(
            vendor=self.vendor_a,
            title="Approved Sensor",
            slug="approved-sensor",
            category=self.category,
            approval_status=Product.STATUS_APPROVED,
            is_active=True,
        )
        # 1 Draft product
        Product.objects.create(
            vendor=self.vendor_a,
            title="Draft Sensor",
            slug="draft-sensor",
            category=self.category,
            approval_status=Product.STATUS_DRAFT,
            is_active=False,
        )
        # 1 Pending product
        Product.objects.create(
            vendor=self.vendor_a,
            title="Pending Sensor",
            slug="pending-sensor",
            category=self.category,
            approval_status=Product.STATUS_PENDING,
            is_active=False,
        )

        response = self.client.get(reverse("store:product_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Approved Sensor")
        self.assertNotContains(response, "Draft Sensor")
        self.assertNotContains(response, "Pending Sensor")

    def test_strict_multi_tenant_seller_isolation(self):
        """Seller B cannot edit or submit Seller A's product."""
        product_a = Product.objects.create(
            vendor=self.vendor_a,
            title="Seller A Exclusive Product",
            slug="seller-a-exclusive-product",
            category=self.category,
            approval_status=Product.STATUS_DRAFT,
        )

        # Login as Seller B and attempt to edit Seller A's product
        self.client.force_login(self.seller_b_user)
        res_edit = self.client.get(reverse("store:vendor_product_edit", args=[product_a.pk]))
        self.assertEqual(res_edit.status_code, 404)

        # Login as Seller B and attempt to submit Seller A's product
        res_submit = self.client.post(reverse("store:vendor_product_submit", args=[product_a.pk]))
        self.assertEqual(res_submit.status_code, 404)
