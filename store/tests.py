from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from store.models import (
    Category,
    Product,
    ProductDigitalAsset,
    ProductInventory,
    ProductVariant,
)
from vendors.models import VendorProfile

User = get_user_model()


class StoreModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="seller_store", email="store@example.com", password="pass")
        self.vendor = VendorProfile.objects.create(
            user=self.user,
            store_name="Himalayan Electronics",
            slug="himalayan-electronics",
            business_email="sales@himalayan.com",
            business_phone="+977-9822222222",
        )
        self.category = Category.objects.create(name="Hardware Kits", slug="hardware-kits")

    def test_category_hierarchy(self):
        sub_cat = Category.objects.create(name="Robotics Kits", slug="robotics-kits", parent=self.category)
        self.assertEqual(sub_cat.parent, self.category)
        self.assertIn(sub_cat, self.category.children.all())

    def test_nptor_owned_and_vendor_owned_products(self):
        # NPTOR owned
        nptor_prod = Product.objects.create(
            title="NPTOR Official Study Guide",
            slug="nptor-official-study-guide",
            category=self.category,
            product_type=Product.TYPE_PHYSICAL,
        )
        self.assertTrue(nptor_prod.is_nptor_owned)
        self.assertIsNone(nptor_prod.vendor)

        # Vendor owned
        vendor_prod = Product.objects.create(
            vendor=self.vendor,
            title="Arduino Starter Kit",
            slug="arduino-starter-kit",
            category=self.category,
            product_type=Product.TYPE_PHYSICAL,
        )
        self.assertFalse(vendor_prod.is_nptor_owned)
        self.assertEqual(vendor_prod.vendor, self.vendor)

    def test_product_variant_pricing_and_inventory(self):
        prod = Product.objects.create(
            title="Digital Microcontroller Handbook",
            slug="digital-microcontroller-handbook",
            category=self.category,
            product_type=Product.TYPE_DIGITAL,
            is_internationally_available=True,
        )
        variant = ProductVariant.objects.create(
            product=prod,
            sku="DMH-PDF-001",
            variant_name="PDF Edition",
            price=Decimal("499.00"),
            currency="NPR",
        )
        inventory = ProductInventory.objects.create(
            variant=variant,
            quantity=100,
            reserved_quantity=5,
        )
        self.assertEqual(inventory.available_quantity, 95)

    def test_inventory_check_constraint_rejects_negative_stock(self):
        prod = Product.objects.create(
            title="Test Sensor",
            slug="test-sensor",
            category=self.category,
            product_type=Product.TYPE_PHYSICAL,
        )
        variant = ProductVariant.objects.create(
            product=prod,
            sku="TEST-SENSOR-001",
            price=Decimal("150.00"),
        )
        # Check constraint on quantity >= 0
        with self.assertRaises(IntegrityError):
            ProductInventory.objects.create(
                variant=variant,
                quantity=-5,
                reserved_quantity=0,
            )

    def test_digital_asset_attributes(self):
        prod = Product.objects.create(
            title="Python Cheat Sheet",
            slug="python-cheat-sheet",
            category=self.category,
            product_type=Product.TYPE_DIGITAL,
            is_internationally_available=True,
        )
        asset = ProductDigitalAsset.objects.create(
            product=prod,
            file_name="python_cheat_sheet.pdf",
            file_size_bytes=1048576,
            checksum_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            max_downloads_per_purchase=5,
            download_validity_days=365,
        )
        self.assertEqual(prod.digital_asset, asset)
        self.assertEqual(asset.max_downloads_per_purchase, 5)
        # Verify protected storage raises ValueError when attempting to generate a public URL
        with self.assertRaises(ValueError):
            _ = asset.file.url



class StoreCatalogUITests(TestCase):
    def setUp(self):
        self.cat1 = Category.objects.create(name="Study Materials", slug="study-materials", is_active=True)
        self.subcat = Category.objects.create(name="Notes", slug="notes", parent=self.cat1, is_active=True)
        self.cat2 = Category.objects.create(name="Desk Supplies", slug="desk-supplies", is_active=True)

        self.prod1 = Product.objects.create(
            title="Comprehensive Study Guide",
            slug="comprehensive-study-guide",
            category=self.cat1,
            product_type=Product.TYPE_PHYSICAL,
            approval_status=Product.STATUS_APPROVED,
            is_active=True,
            is_cod_eligible=True,
        )
        self.var1 = ProductVariant.objects.create(
            product=self.prod1,
            sku="SG-001",
            price=Decimal("750.00"),
            currency="NPR",
        )

        self.prod2 = Product.objects.create(
            title="Desk Organizer Tray",
            slug="desk-organizer-tray",
            category=self.cat2,
            product_type=Product.TYPE_PHYSICAL,
            approval_status=Product.STATUS_APPROVED,
            is_active=True,
        )
        self.var2 = ProductVariant.objects.create(
            product=self.prod2,
            sku="DOT-001",
            price=Decimal("450.00"),
            currency="NPR",
        )

    def test_catalog_renders_simplified_top_bar_and_wider_grid(self):
        url = reverse("store:product_list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)

        # Old inner sidebar category panel and is-3 column are removed
        self.assertNotContains(res, '<h2 class="title is-5 mb-3">Categories</h2>')
        self.assertNotContains(res, '<div class="column is-3">')

        # New compact category controls and horizontal pills are rendered
        self.assertContains(res, 'store-catalog-header')
        self.assertContains(res, 'store-cat-select')
        self.assertContains(res, 'store-filter-pills')
        self.assertContains(res, 'All Categories')
        self.assertContains(res, 'Study Materials')
        self.assertContains(res, 'Desk Supplies')

        # Wider product grid classes are present
        self.assertContains(res, 'store-product-grid')
        self.assertContains(res, 'is-3-widescreen')

        # Product cards and titles are rendered
        self.assertContains(res, "Comprehensive Study Guide")
        self.assertContains(res, "Desk Organizer Tray")
        self.assertContains(res, "COD Eligible")

    def test_catalog_category_filtering(self):
        url = reverse("store:product_list")
        res = self.client.get(url, {"category": "study-materials"})
        self.assertEqual(res.status_code, 200)

        # Should include prod1 and exclude prod2
        self.assertContains(res, "Comprehensive Study Guide")
        self.assertNotContains(res, "Desk Organizer Tray")

        # Category pill is active
        self.assertContains(res, 'Category: <strong>Study Materials</strong>')

    def test_catalog_search_filtering(self):
        url = reverse("store:product_list")
        res = self.client.get(url, {"q": "Organizer"})
        self.assertEqual(res.status_code, 200)

        self.assertContains(res, "Desk Organizer Tray")
        self.assertNotContains(res, "Comprehensive Study Guide")
        self.assertContains(res, 'matching "<em>Organizer</em>"')

    def test_catalog_combined_category_and_search(self):
        url = reverse("store:product_list")
        res = self.client.get(url, {"category": "study-materials", "q": "Guide"})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Comprehensive Study Guide")

        # Searching for something not in study materials
        res2 = self.client.get(url, {"category": "study-materials", "q": "Organizer"})
        self.assertEqual(res2.status_code, 200)
        self.assertContains(res2, "No products found")
        self.assertNotContains(res2, "Desk Organizer Tray")

    def test_dedicated_store_header_and_full_width_layout(self):
        url = reverse("store:product_list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)

        # Dedicated store header is rendered
        self.assertContains(res, "store-dedicated-header")
        self.assertContains(res, "store-brand")
        self.assertContains(res, "Learning")
        self.assertContains(res, "store-cart-btn")
        self.assertContains(res, "Shop by Category")
        self.assertContains(res, "store-hero-banner")

        # Global education sidebar is hidden on store catalog
        self.assertNotContains(res, 'id="site-sidebar"')

    def test_global_sidebar_preserved_on_quiz_practice_page(self):
        url = reverse("quiz:practice")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)

        # Global education sidebar MUST be present on non-store pages
        self.assertContains(res, 'id="site-sidebar"')
        # Dedicated store header MUST NOT be present on non-store pages
        self.assertNotContains(res, "store-dedicated-header")

    def test_marketplace_category_icon_filter(self):
        from store.templatetags.store_tags import category_icon
        self.assertEqual(category_icon('Consumer Electronics'), 'fa-laptop')
        self.assertEqual(category_icon('Men Fashion & Apparel'), 'fa-shirt')
        self.assertEqual(category_icon('Home & Kitchen Appliances'), 'fa-couch')
        self.assertEqual(category_icon('Beauty & Personal Care'), 'fa-spa')
        self.assertEqual(category_icon('Exam Study Guides'), 'fa-book-bookmark')
        self.assertEqual(category_icon('Daily Groceries & Food'), 'fa-basket-shopping')
        self.assertEqual(category_icon('Sports & Fitness'), 'fa-dumbbell')
        self.assertEqual(category_icon('Desk Organization'), 'fa-boxes-stacked')

    def test_general_marketplace_hero_and_navigation(self):
        url = reverse('store:product_list')
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)

        # General marketplace hero elements
        self.assertContains(res, 'Nepal Online Marketplace')
        self.assertContains(res, 'Shop Everything You Need')
        self.assertContains(res, 'Nepal Delivery')
        self.assertContains(res, 'Cash on Delivery')
        self.assertContains(res, 'Verified Sellers')
        self.assertContains(res, 'Secure Checkout')
        self.assertContains(res, 'Shop by Category')
