"""
Management command to seed genuine, non-demo purchasable physical products
in the NPTOR Store catalog for live customer orders and testing.
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from store.models import Category, Product, ProductImage, ProductInventory, ProductVariant


class Command(BaseCommand):
    help = "Seeds genuine, purchasable physical products in NPTOR Store with live stock."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding genuine purchasable products..."))

        # 1. Ensure Categories exist
        cat_books, _ = Category.objects.get_or_create(
            slug="study-guides-books",
            defaults={
                "name": "Study Guides & Books",
                "is_active": True,
            },
        )
        cat_acc, _ = Category.objects.get_or_create(
            slug="monitors-accessories",
            defaults={
                "name": "Monitors & Accessories",
                "is_active": True,
            },
        )

        products_data = [
            {
                "title": "NPTOR Academic Entrance Examination Guide 2026 (Physical Edition)",
                "slug": "nptor-academic-entrance-examination-guide-2026",
                "category": cat_books,
                "price": Decimal("1250.00"),
                "sku": "NPTOR-BOOK-ENT-2026",
                "stock": 50,
                "description": (
                    "Complete 2026 physical examination guidebook containing past model questions, "
                    "in-depth solutions, chapter summaries, and timed mock tests for national academic entrance "
                    "examinations across Nepal. Published by NPTOR Academic Press."
                ),
                "specifications": {
                    "is_demo": False,
                    "publisher": "NPTOR Academic Press",
                    "edition": "2026 Edition",
                    "pages": "480 pages",
                    "binding": "Paperback",
                    "language": "English & Nepali",
                },
            },
            {
                "title": "NPTOR Loksewa Aayog Preparation Master Handbook 2026",
                "slug": "nptor-loksewa-master-handbook-2026",
                "category": cat_books,
                "price": Decimal("1450.00"),
                "sku": "NPTOR-BOOK-LOK-2026",
                "stock": 40,
                "description": (
                    "Authoritative physical preparation handbook for Loksewa Aayog (Public Service Commission) "
                    "examinations. Includes administrative procedures, constitution, general knowledge, "
                    "and IQ reasoning questions with step-by-step explanations."
                ),
                "specifications": {
                    "is_demo": False,
                    "publisher": "NPTOR Academic Press",
                    "edition": "2026 Edition",
                    "pages": "520 pages",
                    "binding": "Paperback",
                },
            },
            {
                "title": "NPTOR Official Ergonomic Study & Laptop Riser Stand",
                "slug": "nptor-official-ergonomic-study-laptop-stand",
                "category": cat_acc,
                "price": Decimal("2100.00"),
                "sku": "NPTOR-HW-STAND-01",
                "stock": 35,
                "description": (
                    "High-grade sandblasted aluminum ergonomic riser stand suitable for laptops, tablets, and study books. "
                    "Offers 6 adjustable viewing angles to improve posture during long study and exam preparation sessions."
                ),
                "specifications": {
                    "is_demo": False,
                    "material": "Anodized Aluminum Alloy",
                    "adjustability": "6 Angles (15 to 45 degrees)",
                    "weight_capacity": "Up to 15 kg",
                    "compatibility": "Laptops & Tablets 10 to 17 inches",
                    "warranty": "1 Year NPTOR Warranty",
                },
            },
        ]

        created_count = 0
        updated_count = 0

        for item in products_data:
            product, created = Product.objects.get_or_create(
                slug=item["slug"],
                defaults={
                    "title": item["title"],
                    "category": item["category"],
                    "description": item["description"],
                    "product_type": "physical",
                    "approval_status": "approved",
                    "is_active": True,
                    "is_cod_eligible": True,
                    "is_internationally_available": False,
                    "specifications": item["specifications"],
                },
            )

            if not created:
                product.title = item["title"]
                product.category = item["category"]
                product.description = item["description"]
                product.product_type = "physical"
                product.approval_status = "approved"
                product.is_active = True
                product.is_cod_eligible = True
                product.specifications = item["specifications"]
                product.save()
                updated_count += 1
            else:
                created_count += 1

            # Ensure default variant exists
            variant, v_created = ProductVariant.objects.get_or_create(
                product=product,
                sku=item["sku"],
                defaults={
                    "variant_name": "Standard Edition",
                    "price": item["price"],
                    "is_active": True,
                },
            )
            if not v_created:
                variant.price = item["price"]
                variant.is_active = True
                variant.save()

            # Ensure inventory exists
            inventory, inv_created = ProductInventory.objects.get_or_create(
                variant=variant,
                defaults={"quantity": item["stock"], "low_stock_threshold": 5},
            )
            if not inv_created:
                if inventory.quantity < 10:
                    inventory.quantity = item["stock"]
                    inventory.save()

            self.stdout.write(
                f" - {'Created' if created else 'Updated'} purchasable product: '{product.title}' (SKU: {variant.sku}, Stock: {inventory.quantity}, is_demo: {product.is_demo})"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded purchasable products! Created: {created_count}, Updated: {updated_count}"
            )
        )
