from django.core.management.base import BaseCommand
from store.models import Category, Product, ProductImage


class Command(BaseCommand):
    help = "Safely removes demonstration catalog products without affecting genuine products or orders."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all-samples",
            action="store_true",
            help="Also remove earlier [Demo Sample] initial prototype products.",
        )

    def handle(self, *args, **options):
        include_samples = options.get("all_samples", False)

        qs = Product.objects.filter(slug__startswith="demo-")
        if include_samples:
            qs = qs | Product.objects.filter(slug__startswith="sample-")

        count = qs.count()
        if count == 0:
            self.stdout.write(self.style.WARNING("No demonstration products found to clear."))
            return

        self.stdout.write(f"Found {count} demonstration products to remove...")

        # Remove image files from disk
        for prod in qs:
            for img in prod.images.all():
                if img.image:
                    try:
                        img.image.delete(save=False)
                    except Exception as exc:
                        self.stderr.write(f"Could not delete image file for {prod.slug}: {exc}")

        deleted_count, _ = qs.delete()
        self.stdout.write(self.style.SUCCESS(f"Successfully deleted {deleted_count} demonstration records."))

        # Clean up empty demo categories if no products remain
        demo_cat_slugs = [
            "running-shoes", "casual-sneakers", "formal-shoes", "sports-shoes", "sandals-slides", "shoes",
            "mens-tshirts-shirts", "womens-tops-dresses", "jeans-trousers", "hoodies-jackets", "activewear", "clothing",
            "headphones-earbuds", "keyboards-mice", "speakers-audio", "smartwatches-wearables", "chargers-cables",
            "monitors-accessories", "electronics",
        ]
        for c_slug in demo_cat_slugs:
            cat = Category.objects.filter(slug=c_slug).first()
            if cat and cat.products.count() == 0 and cat.children.count() == 0:
                cat.delete()
                self.stdout.write(f"Removed unused category '{c_slug}'.")

        self.stdout.write(self.style.SUCCESS("Demo catalog cleanup completed safely."))
