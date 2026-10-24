from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from store.models import (
    Category,
    Product,
    ProductInventory,
    ProductReview,
    ProductReviewHelpfulVote,
    ProductReviewReport,
    ProductVariant,
    ProductVideo,
    Wishlist,
)
from orders.models import Order, SubOrder, OrderItem, OrderReturnRequest
from vendors.models import VendorProfile

User = get_user_model()


class StoreMarketplaceFeaturesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="shopper1", email="shopper1@example.com", password="password123")
        self.vendor_user = User.objects.create_user(username="seller1", email="seller1@example.com", password="password123")
        self.vendor = VendorProfile.objects.create(
            user=self.vendor_user,
            store_name="Kathmandu Apparel & Gear",
            slug="ktm-apparel-gear",
            business_email="ktm@example.com",
            business_phone="+977-9800000001",
        )

        self.cat_shoes = Category.objects.create(name="Shoes & Footwear", slug="shoes")
        self.subcat_running = Category.objects.create(name="Running Shoes", slug="running-shoes", parent=self.cat_shoes)
        self.cat_clothing = Category.objects.create(name="Clothing & Apparel", slug="clothing")

        # Create Product 1: Running Shoes with Variants
        self.prod_shoes = Product.objects.create(
            title="Pro Stride Road Running Shoes",
            slug="demo-pro-stride-running-shoes",
            category=self.subcat_running,
            product_type=Product.TYPE_PHYSICAL,
            approval_status=Product.STATUS_APPROVED,
            is_active=True,
            vendor=self.vendor,
            specifications={"is_demo": True, "brand": "ProStride", "material": "Breathable Mesh"},
            description="### Road Running Performance\n- Cushioning sole\n- High durability",
        )
        self.var_sz40 = ProductVariant.objects.create(
            product=self.prod_shoes,
            sku="PRO-STRIDE-40",
            variant_name="Size 40",
            price=Decimal("3500.00"),
            compare_at_price=Decimal("4200.00"),
            currency="NPR",
            attributes={"size": "40"},
        )
        ProductInventory.objects.create(variant=self.var_sz40, quantity=5, reserved_quantity=0)

        self.var_sz41 = ProductVariant.objects.create(
            product=self.prod_shoes,
            sku="PRO-STRIDE-41",
            variant_name="Size 41",
            price=Decimal("3600.00"),
            currency="NPR",
            attributes={"size": "41"},
        )
        ProductInventory.objects.create(variant=self.var_sz41, quantity=0, reserved_quantity=0)  # Out of stock

        # Product 2: Clothing item
        self.prod_shirt = Product.objects.create(
            title="Organic Cotton Athletic T-Shirt",
            slug="demo-organic-cotton-tshirt",
            category=self.cat_clothing,
            product_type=Product.TYPE_PHYSICAL,
            approval_status=Product.STATUS_APPROVED,
            is_active=True,
            vendor=self.vendor,
            specifications={"is_demo": True, "brand": "EverestWear", "fabric": "100% Organic Cotton"},
            description="Premium everyday t-shirt.",
        )
        self.var_shirt_m = ProductVariant.objects.create(
            product=self.prod_shirt,
            sku="TSHIRT-M",
            variant_name="Size M",
            price=Decimal("1200.00"),
            currency="NPR",
            attributes={"size": "M"},
        )
        ProductInventory.objects.create(variant=self.var_shirt_m, quantity=15, reserved_quantity=0)

        # Video
        self.video = ProductVideo.objects.create(
            product=self.prod_shoes,
            title="Pro Stride Unboxing and Flexibility Test",
            video_url="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
            display_order=0,
        )

    # 1. CATALOG DISCOVERY & FILTERING
    def test_catalog_category_filtering(self):
        url = reverse("store:product_list")
        res = self.client.get(url, {"category": "shoes"})
        self.assertEqual(res.status_code, 200)
        # Shoes parent category includes child subcat_running
        self.assertContains(res, "Pro Stride Road Running Shoes")
        self.assertNotContains(res, "Organic Cotton Athletic T-Shirt")

    def test_catalog_search_filtering(self):
        url = reverse("store:product_list")
        res = self.client.get(url, {"q": "Cotton"})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Organic Cotton Athletic T-Shirt")
        self.assertNotContains(res, "Pro Stride Road Running Shoes")

    def test_catalog_price_range_filtering(self):
        url = reverse("store:product_list")
        # Price <= 2000 should only return T-Shirt (1200)
        res = self.client.get(url, {"max_price": "2000"})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Organic Cotton Athletic T-Shirt")
        self.assertNotContains(res, "Pro Stride Road Running Shoes")

        # Price >= 3000 should only return Shoes (3500)
        res2 = self.client.get(url, {"min_price": "3000"})
        self.assertEqual(res2.status_code, 200)
        self.assertContains(res2, "Pro Stride Road Running Shoes")
        self.assertNotContains(res2, "Organic Cotton Athletic T-Shirt")

    def test_catalog_in_stock_filtering(self):
        # Create an out-of-stock product
        prod_oos = Product.objects.create(
            title="Out Of Stock Demo Item",
            slug="demo-out-of-stock-item",
            category=self.cat_clothing,
            approval_status=Product.STATUS_APPROVED,
            is_active=True,
        )
        var_oos = ProductVariant.objects.create(product=prod_oos, sku="OOS-01", price=Decimal("500.00"))
        ProductInventory.objects.create(variant=var_oos, quantity=0)

        url = reverse("store:product_list")
        res = self.client.get(url, {"in_stock": "1"})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Pro Stride Road Running Shoes")
        self.assertContains(res, "Organic Cotton Athletic T-Shirt")
        self.assertNotContains(res, "Out Of Stock Demo Item")

    def test_catalog_sorting_options(self):
        url = reverse("store:product_list")
        # Sort price low to high: T-shirt (1200) before Shoes (3500)
        res_low = self.client.get(url, {"sort": "price_low"})
        self.assertEqual(res_low.status_code, 200)
        content = res_low.content.decode()
        self.assertTrue(content.find("Organic Cotton Athletic T-Shirt") < content.find("Pro Stride Road Running Shoes"))

        # Sort price high to low: Shoes (3500) before T-shirt (1200)
        res_high = self.client.get(url, {"sort": "price_high"})
        self.assertEqual(res_high.status_code, 200)
        content_high = res_high.content.decode()
        self.assertTrue(content_high.find("Pro Stride Road Running Shoes") < content_high.find("Organic Cotton Athletic T-Shirt"))

    # 2. PRODUCT DETAIL & ATTRIBUTES
    def test_product_detail_page_renders_variants_and_video(self):
        url = reverse("store:product_detail", kwargs={"slug": self.prod_shoes.slug})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)

        # Context contains variants_json and attributes_map
        self.assertIn("variants_json", res.context)
        self.assertIn("Size", res.context["attributes_map"])
        self.assertIn("40", res.context["attributes_map"]["Size"])
        self.assertIn("41", res.context["attributes_map"]["Size"])

        # Page contains video container and video thumbnail button
        self.assertContains(res, "store-video-player")
        self.assertContains(res, "store-video-thumb-btn")
        self.assertContains(res, "ForBiggerBlazes.mp4")

        # Specifications table
        self.assertContains(res, "store-spec-table")
        self.assertContains(res, "ProStride")

    # 3. REVIEWS & RATINGS
    def test_review_submission_unverified_and_verified(self):
        self.client.login(username="shopper1", password="password123")
        review_url = reverse("store:submit_product_review", kwargs={"slug": self.prod_shoes.slug})

        # Submit first review without a completed order
        res = self.client.post(review_url, {
            "rating": 5,
            "title": "Outstanding Road Running Feel",
            "content": "These shoes have great arch support and lightweight cushioning.",
        })
        self.assertEqual(res.status_code, 302)

        review = ProductReview.objects.get(product=self.prod_shoes, user=self.user)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.title, "Outstanding Road Running Feel")
        self.assertFalse(review.is_verified_purchase)
        self.assertEqual(self.prod_shoes.average_rating, 5.0)
        self.assertEqual(self.prod_shoes.review_count, 1)

    def test_duplicate_review_prevention(self):
        self.client.login(username="shopper1", password="password123")
        review_url = reverse("store:submit_product_review", kwargs={"slug": self.prod_shoes.slug})

        # Create existing review
        ProductReview.objects.create(
            product=self.prod_shoes,
            user=self.user,
            rating=4,
            title="Initial review",
            content="Solid shoes.",
            status=ProductReview.STATUS_APPROVED,
        )

        # Try submitting another review
        res = self.client.post(review_url, {
            "rating": 2,
            "title": "Changed my mind",
            "content": "Actually not good.",
        })
        self.assertEqual(res.status_code, 302)

        # Confirm count remains 1 and original review unmodified
        self.assertEqual(ProductReview.objects.filter(product=self.prod_shoes, user=self.user).count(), 1)
        r = ProductReview.objects.get(product=self.prod_shoes, user=self.user)
        self.assertEqual(r.rating, 4)

    def test_helpful_review_voting_and_duplicate_vote_protection(self):
        self.client.login(username="shopper1", password="password123")
        review = ProductReview.objects.create(
            product=self.prod_shoes,
            user=self.vendor_user,
            rating=5,
            title="Great fit",
            content="Fits true to size.",
            status=ProductReview.STATUS_APPROVED,
        )

        vote_url = reverse("store:vote_review_helpful", kwargs={"review_id": review.id})

        # First vote
        res = self.client.post(vote_url)
        self.assertEqual(res.status_code, 302)
        review.refresh_from_db()
        self.assertEqual(review.helpful_count, 1)
        self.assertTrue(ProductReviewHelpfulVote.objects.filter(review=review, user=self.user).exists())

        # Duplicate vote attempt
        res2 = self.client.post(vote_url)
        self.assertEqual(res2.status_code, 302)
        review.refresh_from_db()
        self.assertEqual(review.helpful_count, 1)  # Did not increment again

    def test_report_review_moderation(self):
        self.client.login(username="shopper1", password="password123")
        review = ProductReview.objects.create(
            product=self.prod_shoes,
            user=self.vendor_user,
            rating=1,
            title="Spam Title",
            content="Check my external scam website.",
            status=ProductReview.STATUS_APPROVED,
        )

        report_url = reverse("store:report_product_review", kwargs={"review_id": review.id})
        res = self.client.post(report_url, {"reason": "External link and spam promotional text"})
        self.assertEqual(res.status_code, 302)

        self.assertTrue(
            ProductReviewReport.objects.filter(review=review, reporter=self.user, reason="External link and spam promotional text").exists()
        )

    # 4. WISHLIST
    def test_wishlist_toggle_and_list_view(self):
        self.client.login(username="shopper1", password="password123")
        toggle_url = reverse("store:wishlist_toggle", kwargs={"product_id": self.prod_shoes.id})

        # Add to wishlist
        res_add = self.client.get(toggle_url)
        self.assertEqual(res_add.status_code, 302)
        self.assertTrue(Wishlist.objects.filter(user=self.user, product=self.prod_shoes).exists())

        # Check wishlist page
        wishlist_page_url = reverse("store:wishlist_view")
        res_page = self.client.get(wishlist_page_url)
        self.assertEqual(res_page.status_code, 200)
        self.assertContains(res_page, "Pro Stride Road Running Shoes")

        # Remove from wishlist
        res_remove = self.client.get(toggle_url)
        self.assertEqual(res_remove.status_code, 302)
        self.assertFalse(Wishlist.objects.filter(user=self.user, product=self.prod_shoes).exists())

    # 5. ORDER TRACKING & RETURN REQUEST
    def test_customer_order_list_and_return_request_lifecycle(self):
        self.client.login(username="shopper1", password="password123")

        # Create completed delivered order for customer
        order = Order.objects.create(
            user=self.user,
            order_number="ORD-TEST-9999",
            order_status=Order.ORDER_STATUS_COMPLETED,
            payment_method=Order.PAYMENT_METHOD_COD,
            total_items_amount=Decimal("3500.00"),
            shipping_amount=Decimal("0.00"),
            grand_total=Decimal("3500.00"),
        )
        suborder = SubOrder.objects.create(
            master_order=order,
            suborder_number="SUB-TEST-9999-1",
            vendor=self.vendor,
            fulfillment_status=SubOrder.FULFILLMENT_DELIVERED,
            items_subtotal=Decimal("3500.00"),
            shipping_carrier="Nepal Express Courier",
            tracking_number="NEX-778899",
        )
        OrderItem.objects.create(
            suborder=suborder,
            variant=self.var_sz40,
            product_title_snapshot=self.prod_shoes.title,
            sku_snapshot=self.var_sz40.sku,
            unit_price=self.var_sz40.price,
            quantity=1,
            total_price=self.var_sz40.price,
        )

        # Check customer order history page
        history_url = reverse("orders:customer_order_list")
        res_hist = self.client.get(history_url)
        self.assertEqual(res_hist.status_code, 200)
        self.assertContains(res_hist, "ORD-TEST-9999")
        self.assertContains(res_hist, "Package: Delivered")

        # Check customer order detail with tracking timeline and return action
        detail_url = reverse("orders:customer_order_detail", kwargs={"order_number": order.order_number})
        res_det = self.client.get(detail_url)
        self.assertEqual(res_det.status_code, 200)
        self.assertContains(res_det, "store-order-timeline")
        self.assertContains(res_det, "Request Return / Replacement")

        # Submit return request
        return_url = reverse("orders:customer_return_request", kwargs={"suborder_number": suborder.suborder_number})
        res_ret = self.client.post(return_url, {
            "reason": OrderReturnRequest.REASON_DEFECTIVE,
            "explanation": "Sole stitching arrived loose on the right shoe.",
        })
        self.assertEqual(res_ret.status_code, 302)

        self.assertTrue(
            OrderReturnRequest.objects.filter(
                suborder=suborder,
                user=self.user,
                reason=OrderReturnRequest.REASON_DEFECTIVE,
            ).exists()
        )
