import os
import ssl
import urllib.request
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from store.models import Category, Product, ProductImage, ProductInventory, ProductVariant


class Command(BaseCommand):
    help = "Seeds NPTOR Store with realistic demonstration products across Shoes, Clothing, and Electronics."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-images",
            action="store_true",
            help="Create products and inventory without downloading remote photographs.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing demonstration products if they already exist.",
        )

    def handle(self, *args, **options):
        skip_images = options.get("skip_images", False)
        force = options.get("force", False)

        self.stdout.write(self.style.NOTICE("Initializing NPTOR Store Marketplace Demonstration Catalog..."))

        # 1. CATEGORIES DEFINITION
        categories_structure = [
            # Top-level: Shoes
            {
                "name": "Shoes & Footwear",
                "slug": "shoes",
                "children": [
                    {"name": "Running Shoes", "slug": "running-shoes"},
                    {"name": "Casual Sneakers", "slug": "casual-sneakers"},
                    {"name": "Formal Shoes", "slug": "formal-shoes"},
                    {"name": "Sports Shoes", "slug": "sports-shoes"},
                    {"name": "Sandals & Slides", "slug": "sandals-slides"},
                ],
            },
            # Top-level: Clothing
            {
                "name": "Clothing & Apparel",
                "slug": "clothing",
                "children": [
                    {"name": "Men's T-Shirts & Shirts", "slug": "mens-tshirts-shirts"},
                    {"name": "Women's Tops & Dresses", "slug": "womens-tops-dresses"},
                    {"name": "Jeans & Trousers", "slug": "jeans-trousers"},
                    {"name": "Hoodies & Jackets", "slug": "hoodies-jackets"},
                    {"name": "Activewear & Sportswear", "slug": "activewear"},
                ],
            },
            # Top-level: Electronics
            {
                "name": "Consumer Electronics",
                "slug": "electronics",
                "children": [
                    {"name": "Headphones & Earbuds", "slug": "headphones-earbuds"},
                    {"name": "Keyboards & Mice", "slug": "keyboards-mice"},
                    {"name": "Speakers & Audio", "slug": "speakers-audio"},
                    {"name": "Smartwatches & Wearables", "slug": "smartwatches-wearables"},
                    {"name": "Chargers & Cables", "slug": "chargers-cables"},
                    {"name": "Monitors & Accessories", "slug": "monitors-accessories"},
                ],
            },
        ]

        cat_map = {}
        for parent_data in categories_structure:
            parent_cat, _ = Category.objects.get_or_create(
                slug=parent_data["slug"],
                defaults={"name": parent_data["name"], "is_active": True},
            )
            cat_map[parent_data["slug"]] = parent_cat
            for child_data in parent_data.get("children", []):
                child_cat, _ = Category.objects.get_or_create(
                    slug=child_data["slug"],
                    defaults={
                        "name": child_data["name"],
                        "parent": parent_cat,
                        "is_active": True,
                    },
                )
                cat_map[child_data["slug"]] = child_cat

        self.stdout.write(self.style.SUCCESS(f"Categories verified: {len(cat_map)} categories available."))

        # 2. PRODUCT CATALOG DATA (30 Realistic Products)
        products_data = [
            # ------------------------------------------------------------------
            # SHOES (5 Products)
            # ------------------------------------------------------------------
            {
                "title": "Aeroflex Road Running Shoes",
                "slug": "demo-aeroflex-road-running-shoes",
                "category_slug": "running-shoes",
                "price": Decimal("3850.00"),
                "compare_at_price": Decimal("4500.00"),
                "stock": 24,
                "weight_grams": 650,
                "image_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=600&h=600&q=80",
                "image_filename": "demo_aeroflex_running_shoes.jpg",
                "specifications": {"is_demo": True, "material": "Engineered Mesh", "midsole": "EVA Foam", "sole": "Carbon Rubber", "closure": "Lace-up"},
                "description": (
                    "### High-Performance Road Running Comfort\n"
                    "The Aeroflex Road Runner delivers lightweight cushioning and breathable upper mesh engineered for daily jogging and long-distance road training.\n\n"
                    "### Key Highlights\n"
                    "- Multi-density EVA foam midsole absorbs footstrike impact\n"
                    "- Breathable engineered mesh upper keeps feet dry and cool\n"
                    "- High-traction carbon rubber outsole for wet and dry roads\n"
                    "- Padded heel collar and tongue for blister-free ankle support"
                ),
            },
            {
                "title": "Urban Canvas Low-Top Casual Sneakers",
                "slug": "demo-urban-canvas-low-top-sneakers",
                "category_slug": "casual-sneakers",
                "price": Decimal("2450.00"),
                "compare_at_price": Decimal("2950.00"),
                "stock": 35,
                "weight_grams": 720,
                "image_url": "https://images.unsplash.com/photo-1560769629-975ec94e6a86?auto=format&fit=crop&w=600&h=600&q=80",
                "image_filename": "demo_urban_canvas_sneakers.jpg",
                "specifications": {"is_demo": True, "material": "100% Cotton Canvas", "sole": "Vulcanized Rubber", "style": "Low-Top Casual"},
                "description": (
                    "### Everyday Street & Campus Style\n"
                    "Classic low-top silhouette crafted with durable cotton canvas and a flexible vulcanized rubber sole.\n\n"
                    "### Key Highlights\n"
                    "- Heavyweight 12oz cotton canvas upper with contrast stitching\n"
                    "- Cushioned memory-foam insole for all-day comfort\n"
                    "- Non-slip waffle tread rubber outsole\n"
                    "- Reinforced metal eyelets with tonal woven laces"
                ),
            },
            {
                "title": "Oxford Derby Leather Formal Dress Shoes",
                "slug": "demo-oxford-derby-leather-formal-shoes",
                "category_slug": "formal-shoes",
                "price": Decimal("5200.00"),
                "compare_at_price": Decimal("6200.00"),
                "stock": 18,
                "weight_grams": 850,
                "image_url": "https://images.unsplash.com/photo-1614252235316-8c857d38b5f4?auto=format&fit=crop&w=600&h=600&q=80",
                "image_filename": "demo_oxford_formal_shoes.jpg",
                "specifications": {"is_demo": True, "material": "Synthetic Full-Grain Leather", "sole": "TPR Formal Dress Sole", "toe": "Classic Cap-Toe"},
                "description": (
                    "### Handcrafted Formal Polish\n"
                    "Refined Oxford Derby dress shoes designed for office wear, corporate presentations, and celebratory occasions.\n\n"
                    "### Key Highlights\n"
                    "- Premium synthetic full-grain leather with hand-burnished gloss finish\n"
                    "- Ergonomic arch-support footbed reduces fatigue during long workdays\n"
                    "- Stitched welt detailing for reinforced longevity\n"
                    "- Low block heel with anti-slip rubber traction pad"
                ),
            },
            {
                "title": "All-Terrain Multi-Sport Training Shoes",
                "slug": "demo-all-terrain-multi-sport-training-shoes",
                "category_slug": "sports-shoes",
                "price": Decimal("4100.00"),
                "compare_at_price": Decimal("4800.00"),
                "stock": 20,
                "weight_grams": 690,
                "image_url": "https://images.unsplash.com/photo-1608231387042-66d1773070a5?auto=format&fit=crop&w=600&h=600&q=80",
                "image_filename": "demo_multisport_training_shoes.jpg",
                "specifications": {"is_demo": True, "material": "Synthetic Mesh & TPU Overlays", "sole": "Deep Lug Rubber", "activity": "Cross-Training & Turf"},
                "description": (
                    "### Rugged Athletic Performance\n"
                    "Built for cross-training, turf sports, and gym agility workouts with reinforced lateral stability.\n\n"
                    "### Key Highlights\n"
                    "- TPU heel clip locks your foot securely during lateral cuts and sprints\n"
                    "- Shock-absorbing dual-density midsole protects joints\n"
                    "- Protective rubberized toe bumper prevents scuffs\n"
                    "- Breathable mesh lining with moisture-wicking properties"
                ),
            },
            {
                "title": "Comfort-Strap Trail Outdoor Sandals",
                "slug": "demo-comfort-strap-trail-outdoor-sandals",
                "category_slug": "sandals-slides",
                "price": Decimal("1750.00"),
                "compare_at_price": Decimal("2100.00"),
                "stock": 40,
                "weight_grams": 450,
                "image_url": "https://images.unsplash.com/photo-1603808033192-082d6919d3e1?auto=format&fit=crop&w=600&h=600&q=80",
                "image_filename": "demo_outdoor_trail_sandals.jpg",
                "specifications": {"is_demo": True, "straps": "Quick-Dry Webbing", "footbed": "Textured Water-Resistant EVA", "closure": "Triple Hook & Loop"},
                "description": (
                    "### Outdoor Summer & Monsoon Comfort\n"
                    "Triple-strap adjustable sandals featuring quick-drying webbing and textured arch support for light trails and daily walks.\n\n"
                    "### Key Highlights\n"
                    "- 3 adjustable hook-and-loop points for a customized snug fit\n"
                    "- Hydrophobic textured footbed drains water rapidly\n"
                    "- Deep-tread rubber outsole ensures grip across wet pavement and rocky paths\n"
                    "- Lightweight buoyant EVA construction"
                ),
            },

            # ------------------------------------------------------------------
            # CLOTHING (10 Products)
            # ------------------------------------------------------------------
            {
                "title": "Men's Organic Combed Cotton Crewneck T-Shirt",
                "slug": "demo-mens-organic-cotton-crewneck-tshirt",
                "category_slug": "mens-tshirts-shirts",
                "price": Decimal("950.00"),
                "compare_at_price": Decimal("1200.00"),
                "stock": 45,
                "weight_grams": 210,
                "image_url": "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&w=600&h=600&q=80",
                "image_filename": "demo_mens_crewneck_tshirt.jpg",
                "specifications": {"is_demo": True, "fabric": "100% Combed Organic Cotton", "gsm": "180 GSM", "fit": "Regular Fit", "neck": "Crewneck"},
                "description": (
                    "### Ultra-Soft Everyday Essential\n"
                    "Crafted from 180 GSM bio-washed combed organic cotton for supreme softness, breathability, and all-day ease.\n\n"
                    "### Key Highlights\n"
                    "- 100% combed cotton with anti-pilling enzymatic treatment\n"
                    "- Ribbed elastane collar maintains shape wash after wash\n"
                    "- Tailored regular fit with clean shoulder taping\n"
                    "- Pre-shrunk fabric to prevent post-wash shrinkage"
                ),
            },
            {
                "title": "Men's Classic Slim-Fit Oxford Button-Down Shirt",
                "slug": "demo-mens-classic-slim-fit-oxford-shirt",
                "category_slug": "mens-tshirts-shirts",
                "price": Decimal("2250.00"),
                "compare_at_price": Decimal("2750.00"),
                "stock": 28,
                "weight_grams": 310,
                "image_url": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?auto=format&fit=crop&w=600&h=600&q=80",
                "image_filename": "demo_mens_oxford_shirt.jpg",
                "specifications": {"is_demo": True, "fabric": "100% Woven Oxford Cotton", "collar": "Button-Down", "cuff": "Adjustable Double-Button"},
                "description": (
                    "### Versatile Smart-Casual Oxford\n"
                    "Timeless button-down Oxford cloth shirt suitable for office wear, university, and evening gatherings.\n\n"
                    "### Key Highlights\n"
                    "- Heavyweight breathable Oxford basket-weave cotton\n"
                    "- Crisp button-down collar and single front patch pocket\n"
                    "- Tailored slim fit with curved hemline suitable tucked or untucked\n"
                    "- Cross-stitched pearlized buttons for durability"
                ),
            },
            {
                "title": "Women's Floral Summer A-Line Midi Dress",
                "slug": "demo-womens-floral-summer-midi-dress",
                "category_slug": "womens-tops-dresses",
                "price": Decimal("2900.00"),
                "compare_at_price": Decimal("3500.00"),
                "stock": 22,
                "weight_grams": 280,
                "image_url": "https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?auto=format&fit=crop&w=600&h=600&q=80",
                "image_filename": "demo_womens_floral_midi_dress.jpg",
                "specifications": {"is_demo": True, "fabric": "Chiffon with Cotton-Poly Lining", "length": "Midi", "pattern": "Botanical Floral"},
                "description": (
                    "### Lightweight Graceful Silhouette\n"
                    "Flattering A-line midi dress featuring a subtle floral print, flutter sleeves, and an elasticated waist with sash belt.\n\n"
                    "### Key Highlights\n"
                    "- Breathable, wrinkle-resistant chiffon outer with soft inner lining\n"
                    "- Feminine V-neckline with delicate short flutter sleeves\n"
                    "- Elasticated waist effortlessly accommodates varied body shapes\n"
                    "- Flowy tiered hemline for elegant movement"
                ),
            },
            {
                "title": "Women's Ribbed Knit Long-Sleeve Casual Top",
                "slug": "demo-womens-ribbed-knit-long-sleeve-top",
                "category_slug": "womens-tops-dresses",
                "price": Decimal("1450.00"),
                "compare_at_price": Decimal("1800.00"),
                "stock": 30,
                "weight_grams": 240,
                "image_url": "https://images.unsplash.com/photo-1434389677669-e08b4cac3105?auto=format&fit=crop&w=600&h=600&q=80",
                "image_filename": "demo_womens_ribbed_knit_top.jpg",
                "specifications": {"is_demo": True, "fabric": "95% Cotton, 5% Spandex", "knit": "Vertical Rib Knit", "sleeve": "Full Length"},
                "description": (
                    "### Cozy Everyday Layering\n"
                    "Chic ribbed knit stretch top with a flattering scoop neck, ideal for pairing with tailored trousers or denim.\n\n"
                    "### Key Highlights\n"
                    "- Premium cotton-spandex ribbed fabric blend with 4-way stretch\n"
                    "- Body-contouring yet breathable comfortable fit\n"
                    "- Double-stitched flat cuffs and hem\n"
                    "- Thermal-regulating knit suited for autumn and winter layering"
                ),
            },
            {
                "title": "Classic Straight-Fit Stretch Denim Jeans",
                "slug": "demo-classic-straight-fit-stretch-denim-jeans",
                "category_slug": "jeans-trousers",
                "price": Decimal("2800.00"),
                "compare_at_price": Decimal("3400.00"),
                "stock": 26,
                "weight_grams": 680,
                "image_url": "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?auto=format&fit=crop&w=600&h=600&q=80",
                "image_filename": "demo_straight_fit_denim_jeans.jpg",
                "specifications": {"is_demo": True, "fabric": "98% Cotton, 2% Elastane", "weight": "12.5 oz Denim", "fit": "Straight Fit"},
                "description": (
                    "### Timeless 5-Pocket Indigo Denim\n"
                    "Durable 12.5 oz stretch denim designed to move with you throughout the day without bagging at the knees.\n\n"
                    "### Key Highlights\n"
                    "- 98% ringspun cotton with 2% elastane for flexible comfort\n"
                    "- Classic 5-pocket architecture with reinforced copper rivets\n"
                    "- Heavy-duty brass zip fly with durable cast shank button\n"
                    "- Eco-friendly enzyme stone wash for authentic subtle fade"
                ),
            },
            {
                "title": "Slim-Tapered Stretch Chino Trousers",
                "slug": "demo-slim-tapered-stretch-chino-trousers",
                "category_slug": "jeans-trousers",
                "price": Decimal("2350.00"),
                "compare_at_price": Decimal("2850.00"),
                "stock": 32,
                "weight_grams": 460,
                "image_url": "https://images.unsplash.com/photo-1473966968600-fa801b869a1a?auto=format&fit=crop&w=600&h=600&q=80",
                "image_filename": "demo_slim_tapered_chino_trousers.jpg",
                "specifications": {"is_demo": True, "fabric": "97% Cotton Twill, 3% Spandex", "cut": "Slim Tapered", "pockets": "4-Pocket Styling"},
                "description": (
                    "### Modern Smart Casual Trouser\n"
                    "Clean-cut chino trousers combining dress-pant sophistication with cotton stretch comfort.\n\n"
                    "### Key Highlights\n"
                    "- High-density compact cotton twill with mechanical stretch\n"
                    "- Slanted front pockets and button-through rear welt pockets\n"
                    "- Flat front styling with cleanly tapered leg opening\n"
                    "- Wrinkle-resistant finish for easy wash-and-wear care"
                ),
            },
            {
                "title": "Heavyweight Fleece Full-Zip Casual Hoodie",
                "slug": "demo-heavyweight-fleece-full-zip-hoodie",
                "category_slug": "hoodies-jackets",
                "price": Decimal("3200.00"),
                "compare_at_price": Decimal("3900.00"),
                "stock": 25,
                "weight_grams": 740,
                "image_url": "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?auto=format&fit=crop&w=600&h=600&q=80",
                "image_filename": "demo_heavyweight_fleece_hoodie.jpg",
                "specifications": {"is_demo": True, "fabric": "80% Cotton, 20% Polyester", "fleece": "320 GSM Brushed Fleece", "zipper": "Full-Length YKK"},
                "description": (
                    "### Deep Warmth and Daily Comfort\n"
                    "320 GSM brushed-back fleece hoodie with spacious split kangaroo pockets and an adjustable double-layered hood.\n\n"
                    "### Key Highlights\n"
                    "- Thick thermal brushed fleece interior locks in body heat\n"
                    "- Premium metallic YKK front zipper glide\n"
                    "- Double-layered fabric hood with tipped round drawstrings\n"
                    "- 2x2 rib knit elastane cuffs and waistband resist stretching out"
                ),
            },
            {
                "title": "All-Weather Windbreaker Outdoor Jacket",
                "slug": "demo-all-weather-windbreaker-outdoor-jacket",
                "category_slug": "hoodies-jackets",
                "price": Decimal("4600.00"),
                "compare_at_price": Decimal("5400.00"),
                "stock": 15,
                "weight_grams": 420,
                "image_url": "https://images.unsplash.com/photo-1548883354-7622d03aca27?auto=format&fit=crop&w=600&h=600&q=80",
                "image_filename": "demo_all_weather_windbreaker.jpg",
                "specifications": {"is_demo": True, "shell": "Water-Repellent DWR Ripstop", "lining": "Breathable Poly Mesh", "packable": "Yes"},
                "description": (
                    "### Water-Repellent Weather Barrier\n"
                    "Technical windbreaker jacket built for morning commutes, hill treks, and sudden monsoon showers.\n\n"
                    "### Key Highlights\n"
                    "- DWR (Durable Water Repellent) treated nylon ripstop shell\n"
                    "- Breathable interior mesh lining prevents clammy moisture buildup\n"
                    "- Zippered storm pockets with water-resistant seam tape\n"
                    "- Packs compactly into its own internal zip chest pouch"
                ),
            },
            {
                "title": "Moisture-Wicking Athletic Training Shirt",
                "slug": "demo-moisture-wicking-athletic-training-shirt",
                "category_slug": "activewear",
                "price": Decimal("1200.00"),
                "compare_at_price": Decimal("1500.00"),
                "stock": 38,
                "weight_grams": 160,
                "image_url": "https://images.unsplash.com/photo-1618354691373-d851c5c3a990?auto=format&fit=crop&w=600&h=600&q=80",
                "image_filename": "demo_athletic_training_shirt.jpg",
                "specifications": {"is_demo": True, "fabric": "100% Quick-Dry Poly Microfiber", "stretch": "4-Way Mechanical Stretch", "weight": "135 GSM"},
                "description": (
                    "### Cool Dry Workout Performance\n"
                    "Engineered for high-intensity gym training, morning jogging, and sports.\n\n"
                    "### Key Highlights\n"
                    "- 4-way stretch micro-vented fabric accelerates sweat evaporation\n"
                    "- Anti-microbial yarn helps prevent odor accumulation\n"
                    "- Flatlock anti-friction stitching prevents skin chafing\n"
                    "- Reflective safety accents for dawn and evening visibility"
                ),
            },
            {
                "title": "Pro Compression Active Running Shorts",
                "slug": "demo-pro-compression-active-running-shorts",
                "category_slug": "activewear",
                "price": Decimal("1650.00"),
                "compare_at_price": Decimal("2000.00"),
                "stock": 30,
                "weight_grams": 220,
                "image_url": "https://images.unsplash.com/photo-1591195853828-11db59a44f6b?auto=format&fit=crop&w=600&h=600&q=80",
                "image_filename": "demo_compression_running_shorts.jpg",
                "specifications": {"is_demo": True, "design": "2-in-1 Dual Layer", "liner": "Spandex Compression Liner", "phone_pocket": "Integrated Liner Pocket"},
                "description": (
                    "### 2-in-1 Dual Layer Motion Shorts\n"
                    "Combines a featherlight outer shell with a supportive compression inner liner equipped with a bounce-free phone pocket.\n\n"
                    "### Key Highlights\n"
                    "- Built-in compression liner prevents thigh friction and supports quad muscles\n"
                    "- Dedicated bounce-free liner pocket fits smartphones up to 6.7 inches\n"
                    "- Wide elastic waistband with internal adjustable drawstring\n"
                    "- Rear zippered key/card pocket with reflective zipper track"
                ),
            },

            # ------------------------------------------------------------------
            # ELECTRONICS (15 Products)
            # ------------------------------------------------------------------
            {
                "title": "Pro Active Noise-Cancelling Wireless Earbuds",
                "slug": "demo-pro-anc-wireless-earbuds",
                "category_slug": "headphones-earbuds",
                "price": Decimal("4999.00"),
                "compare_at_price": Decimal("6499.00"),
                "stock": 25,
                "weight_grams": 120,
                "image_url": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?auto=format&fit=crop&w=600&h=600&q=80",
                "image_filename": "demo_pro_anc_wireless_earbuds.jpg",
                "specifications": {"is_demo": True, "anc": "Up to 35dB Hybrid ANC", "battery": "32 Hours Total Playtime", "bluetooth": "v5.3", "waterproof": "IPX5"},
                "description": (
                    "### Immersive Sound with Hybrid Active Noise Cancellation\n"
                    "Experience crystal clear audio and up to 35dB of ambient noise cancellation with 32 hours of total charging-case battery life.\n\n"
                    "### Key Highlights\n"
                    "- Hybrid Active Noise Cancellation with one-touch Transparency mode\n"
                    "- 10mm dynamic titanium composite drivers delivering deep resonant bass\n"
                    "- Quad-microphone ENC system filters ambient wind during calls\n"
                    "- IPX5 sweat and splash resistance for workout confidence\n"
                    "- Fast USB-C charging: 10 minutes provides 2 full hours of playback"
                ),
            },
            {
                "title": "Wireless Over-Ear Hi-Fi Studio Headphones",
                "slug": "demo-wireless-over-ear-hifi-headphones",
                "category_slug": "headphones-earbuds",
                "price": Decimal("6800.00"),
                "compare_at_price": Decimal("8500.00"),
                "stock": 16,
                "weight_grams": 380,
                "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=600&h=600&q=80",
                "image_filename": "demo_hifi_over_ear_headphones.jpg",
                "specifications": {"is_demo": True, "drivers": "40mm Neodymium Acoustic", "battery": "50 Hours Playtime", "latency": "45ms Low Latency Mode"},
                "description": (
                    "### Deep Bass & 50-Hour Extended Playtime\n"
                    "Plush memory-foam ear cushions and custom 40mm neodymium drivers engineered for all-day focus, music, and online lectures.\n\n"
                    "### Key Highlights\n"
                    "- 40mm high-resolution stereo acoustic drivers with balanced tuning\n"
                    "- Up to 50 hours uninterrupted battery life on a single charge\n"
                    "- Low-latency gaming and streaming audio profile (45ms)\n"
                    "- Detachable 3.5mm braided audio cable included for wired backup\n"
                    "- Foldable multi-axis swivel earcups for easy commuting"
                ),
            },
            {
                "title": "Mechanical Gaming Keyboard RGB Backlit",
                "slug": "demo-mechanical-gaming-keyboard-rgb",
                "category_slug": "keyboards-mice",
                "price": Decimal("5450.00"),
                "compare_at_price": Decimal("6800.00"),
                "stock": 20,
                "weight_grams": 980,
                "image_url": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=600&h=600&q=80",
                "image_filename": "demo_mechanical_gaming_keyboard.jpg",
                "specifications": {"is_demo": True, "switches": "Tactile Blue Switches", "keys": "104 Full Size", "lighting": "18 RGB Presets", "rollover": "N-Key Anti-Ghosting"},
                "description": (
                    "### Tactile Precision for Typing & Gaming\n"
                    "Full-size 104-key mechanical keyboard featuring crisp blue tactile switches, brushed aluminum top plate, and dynamic per-key RGB.\n\n"
                    "### Key Highlights\n"
                    "- 50-million keystroke rated mechanical blue switches with satisfying tactile click\n"
                    "- 18 customizable RGB backlighting presets with speed and brightness tuning\n"
                    "- Full N-Key Rollover anti-ghosting across all 104 keys\n"
                    "- Anodized aircraft-grade aluminum top plate resists flex and wear\n"
                    "- Detachable ergonomic wrist rest included"
                ),
            },
            {
                "title": "Ergonomic Wireless Silent Optical Mouse",
                "slug": "demo-ergonomic-wireless-silent-mouse",
                "category_slug": "keyboards-mice",
                "price": Decimal("1850.00"),
                "compare_at_price": Decimal("2300.00"),
                "stock": 42,
                "weight_grams": 140,
                "image_url": "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?auto=format&fit=crop&w=600&h=600&q=80",
                "image_filename": "demo_wireless_silent_mouse.jpg",
                "specifications": {"is_demo": True, "connection": "Bluetooth 5.1 & 2.4GHz USB", "dpi": "800-1200-1600-2400 DPI", "clicks": "90% Silent Switch"},
                "description": (
                    "### Whisper-Quiet Productive Tracking\n"
                    "90% noise-reduced click switches and a sculpted thumb rest engineered for comfortable home and office desktop work.\n\n"
                    "### Key Highlights\n"
                    "- Dual wireless connectivity: Bluetooth 5.1 and 2.4GHz USB nano receiver\n"
                    "- 90% silent micro-switches eliminate distracting clicking sounds\n"
                    "- 4-level on-the-fly DPI adjustment button (800 / 1200 / 1600 / 2400 DPI)\n"
                    "- Contoured ergonomic grip with textured rubber thumb support\n"
                    "- Up to 18-month battery life with smart automatic sleep"
                ),
            },
            {
                "title": "Portable Waterproof Bluetooth Speaker 20W",
                "slug": "demo-portable-waterproof-bluetooth-speaker-20w",
                "category_slug": "speakers-audio",
                "price": Decimal("3950.00"),
                "compare_at_price": Decimal("4900.00"),
                "stock": 28,
                "weight_grams": 540,
                "image_url": "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?auto=format&fit=crop&w=600&h=600&q=80",
                "image_filename": "demo_portable_waterproof_speaker.jpg",
                "specifications": {"is_demo": True, "power": "20W RMS Output", "waterproof": "IPX7 Submersible", "battery": "15 Hours Playtime", "tws": "Supported"},
                "description": (
                    "### 360-Degree Stereo Sound Anywhere\n"
                    "Compact 20W dual-driver speaker featuring dual bass passive radiators and IPX7 complete waterproof protection.\n\n"
                    "### Key Highlights\n"
                    "- Dual 10W precision acoustic drivers with dual bass passive radiators\n"
                    "- IPX7 waterproof rating: safe for pool parties, rain, and riverbanks\n"
                    "- Up to 15 hours continuous playtime on a single charge\n"
                    "- True Wireless Stereo (TWS) pairing to link two speakers wirelessly\n"
                    "- Built-in microphone for speakerphone hands-free calls"
                ),
            },
            {
                "title": "Desktop Stereo Soundbar with Deep Bass Sub",
                "slug": "demo-desktop-stereo-soundbar",
                "category_slug": "speakers-audio",
                "price": Decimal("4600.00"),
                "compare_at_price": Decimal("5500.00"),
                "stock": 19,
                "weight_grams": 1100,
                "image_url": "https://images.unsplash.com/photo-1545454675-3531b543be5d?auto=format&fit=crop&w=600&h=600&q=80",
                "image_filename": "demo_desktop_stereo_soundbar.jpg",
                "specifications": {"is_demo": True, "channels": "2.0 Stereo with Bass Port", "connectivity": "Bluetooth 5.0, AUX 3.5mm, USB", "power": "USB 5V Powered"},
                "description": (
                    "### Cinematic Desktop Audio Upgrade\n"
                    "Low-profile stereo soundbar designed to sit neatly under your computer monitor or small TV for punchy, clear audio.\n\n"
                    "### Key Highlights\n"
                    "- Dual full-range drivers with side bass reflex tubes for rich resonance\n"
                    "- Triple input versatility: Bluetooth 5.0, AUX 3.5mm line-in, and USB audio\n"
                    "- Smooth rotary volume control dial with ambient soft LED backlight\n"
                    "- USB-powered design eliminates messy wall adapters"
                ),
            },
            {
                "title": "Smart Fitness Watch with 1.43\" AMOLED Display",
                "slug": "demo-smart-fitness-watch-amoled",
                "category_slug": "smartwatches-wearables",
                "price": Decimal("6250.00"),
                "compare_at_price": Decimal("7800.00"),
                "stock": 22,
                "weight_grams": 95,
                "image_url": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=600&h=600&q=80",
                "image_filename": "demo_smart_fitness_watch_amoled.jpg",
                "specifications": {"is_demo": True, "display": "1.43\" AMOLED 466x466", "battery": "Up to 10 Days", "sensors": "Heart Rate, SpO2, Sleep", "calling": "Bluetooth Phone Calls"},
                "description": (
                    "### Crisp AMOLED & Comprehensive Health Tracking\n"
                    "Always-On 466x466 AMOLED display with 24/7 heart rate monitoring, SpO2 blood oxygen, and Bluetooth phone calling.\n\n"
                    "### Key Highlights\n"
                    "- 1.43-inch HD AMOLED touchscreen with vibrant Always-On Display\n"
                    "- Continuous 24/7 heart rate, SpO2 blood oxygen, and sleep stage tracking\n"
                    "- 100+ dedicated athletic sports tracking modes\n"
                    "- High-clarity Bluetooth calling with onboard speaker and mic\n"
                    "- Up to 10 days standard battery life on a single magnetic charge"
                ),
            },
            {
                "title": "Rugged Outdoor GPS Multisport Smartwatch",
                "slug": "demo-rugged-outdoor-gps-smartwatch",
                "category_slug": "smartwatches-wearables",
                "price": Decimal("9800.00"),
                "compare_at_price": Decimal("12500.00"),
                "stock": 14,
                "weight_grams": 130,
                "image_url": "https://images.unsplash.com/photo-1508685096489-7aacd43bd3b1?auto=format&fit=crop&w=600&h=600&q=80",
                "image_filename": "demo_rugged_outdoor_gps_watch.jpg",
                "specifications": {"is_demo": True, "durability": "MIL-STD-810G Shockproof", "waterproof": "5 ATM (50m)", "gnss": "Dual-Band GPS/GLONASS", "battery": "14 Days Trek Mode"},
                "description": (
                    "### Military-Grade Toughness for Treks & Trails\n"
                    "Tough reinforced casing, built-in compass, barometer, altimeter, and multi-GNSS satellite tracking for Himalayan trekking.\n\n"
                    "### Key Highlights\n"
                    "- MIL-STD-810G military-grade shock, freeze, and heat resistance\n"
                    "- Integrated dual-frequency GPS tracking for trail navigation\n"
                    "- Built-in barometric altimeter and 3-axis digital electronic compass\n"
                    "- 5ATM water resistance rating: swimming and monsoon storm ready\n"
                    "- 14-day trekking battery reserve with power saving modes"
                ),
            },
            {
                "title": "65W GaN Multi-Port USB-C Fast Wall Charger",
                "slug": "demo-65w-gan-multi-port-usb-c-charger",
                "category_slug": "chargers-cables",
                "price": Decimal("2950.00"),
                "compare_at_price": Decimal("3600.00"),
                "stock": 35,
                "weight_grams": 180,
                "image_url": "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?auto=format&fit=crop&w=600&h=600&q=80",
                "image_filename": "demo_65w_gan_fast_charger.jpg",
                "specifications": {"is_demo": True, "power": "65W Max Power Delivery", "technology": "GaN III Semiconductor", "ports": "2x USB-C + 1x USB-A"},
                "description": (
                    "### Compact GaN Power for Laptop & Phone\n"
                    "Gallium Nitride technology enables high-speed 65W Power Delivery charging in a pocket-sized form factor.\n\n"
                    "### Key Highlights\n"
                    "- 65W Max Power Delivery fast charging for laptops, tablets, and phones\n"
                    "- 3 ports: 2x USB-C PD 3.0 + 1x USB-A Quick Charge 3.0\n"
                    "- Advanced GaN III semiconductor runs 50% cooler and smaller than silicon bricks\n"
                    "- Dynamic power distribution allocates power intelligently between devices\n"
                    "- Multi-layer protection against over-voltage, overheating, and short-circuits"
                ),
            },
            {
                "title": "Braided Nylon 100W USB-C to USB-C Fast Cable 2M",
                "slug": "demo-braided-nylon-100w-usb-c-cable-2m",
                "category_slug": "chargers-cables",
                "price": Decimal("850.00"),
                "compare_at_price": Decimal("1100.00"),
                "stock": 50,
                "weight_grams": 85,
                "image_url": "https://images.unsplash.com/photo-1585338107529-13afc5f02586?auto=format&fit=crop&w=600&h=600&q=80",
                "image_filename": "demo_100w_usbc_cable_2m.jpg",
                "specifications": {"is_demo": True, "power": "100W (20V/5A) PD Fast Charge", "length": "2.0 Meters (6.6 ft)", "jacket": "Double-Braided Nylon"},
                "description": (
                    "### Ultra-Durable 100W Heavy-Duty Charging\n"
                    "High-density braided nylon cable supporting up to 100W PD 5A fast charging and 480Mbps high-speed data sync.\n\n"
                    "### Key Highlights\n"
                    "- Supports 100W (20V/5A) Power Delivery charging for MacBook, laptops, and phones\n"
                    "- Integrated E-Marker smart IC chip regulates current safety\n"
                    "- 25,000+ bend-tested reinforced aluminum alloy connector housings\n"
                    "- Generous 2-meter length for desk and bedside convenience"
                ),
            },
            {
                "title": "Universal 3-in-1 Fast Charging Cable 1.2M",
                "slug": "demo-universal-3-in-1-fast-charging-cable",
                "category_slug": "chargers-cables",
                "price": Decimal("750.00"),
                "compare_at_price": Decimal("950.00"),
                "stock": 48,
                "weight_grams": 70,
                "image_url": "https://images.unsplash.com/photo-1588508065123-287b28e013da?auto=format&fit=crop&w=600&h=600&q=80",
                "image_filename": "demo_universal_3in1_cable.jpg",
                "specifications": {"is_demo": True, "tips": "USB-C + Lightning + Micro-USB", "output": "3.0A Fast Charge", "length": "1.2 Meters"},
                "description": (
                    "### One Cable for All Your Daily Devices\n"
                    "Eliminate cable clutter with a single rugged cable equipped with USB-C, Lightning, and Micro-USB connectors.\n\n"
                    "### Key Highlights\n"
                    "- 3 integrated output tips: Type-C, Lightning (iOS), and Micro-USB\n"
                    "- 3.0A total power output charges up to 3 devices simultaneously\n"
                    "- Tangle-free high-tensile braided nylon exterior\n"
                    "- Gold-plated pins ensure steady connection and minimal resistance"
                ),
            },
            {
                "title": "27-Inch Ultra-Slim IPS Full HD 100Hz Monitor",
                "slug": "demo-27-inch-ips-fhd-100hz-monitor",
                "category_slug": "monitors-accessories",
                "price": Decimal("18500.00"),
                "compare_at_price": Decimal("22000.00"),
                "stock": 10,
                "weight_grams": 4200,
                "image_url": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?auto=format&fit=crop&w=600&h=600&q=80",
                "image_filename": "demo_27inch_ips_monitor.jpg",
                "specifications": {"is_demo": True, "size": "27 Inch IPS Panel", "resolution": "1920x1080 Full HD", "refresh": "100Hz with FreeSync", "ports": "HDMI & VGA"},
                "description": (
                    "### Edge-to-Edge Fluid Visual Clarity\n"
                    "27-inch Full HD (1920x1080) IPS panel featuring a smooth 100Hz refresh rate, 99% sRGB color gamut, and frameless bezels.\n\n"
                    "### Key Highlights\n"
                    "- 27\" IPS panel with wide 178-degree viewing angles and natural color accuracy\n"
                    "- Smooth 100Hz refresh rate reduces motion blur in games and document scrolling\n"
                    "- 3-sided micro-edge frameless aesthetic for clean multi-monitor setups\n"
                    "- Low Blue Light and Flicker-Free eye care technology\n"
                    "- HDMI and VGA connectivity with tilt-adjustable sturdy stand"
                ),
            },
            {
                "title": "Ergonomic Aluminum Laptop & Monitor Riser Stand",
                "slug": "demo-aluminum-laptop-monitor-riser-stand",
                "category_slug": "monitors-accessories",
                "price": Decimal("2650.00"),
                "compare_at_price": Decimal("3200.00"),
                "stock": 30,
                "weight_grams": 820,
                "image_url": "https://images.unsplash.com/photo-1587614382346-4ec70e388b28?auto=format&fit=crop&w=600&h=600&q=80",
                "image_filename": "demo_aluminum_laptop_riser.jpg",
                "specifications": {"is_demo": True, "material": "CNC Anodized Aluminum", "capacity": "Holds up to 10kg", "compatibility": "Laptops 10\"-17.3\""},
                "description": (
                    "### Improve Posture & Desk Ergonomics\n"
                    "CNC-machined aluminum stand elevates your laptop screen to eye level to alleviate neck and shoulder strain.\n\n"
                    "### Key Highlights\n"
                    "- Solid sandblasted anodized aerospace-grade aluminum construction\n"
                    "- Supports laptops and monitors up to 10kg with zero wobble\n"
                    "- Open airflow channel promotes natural passive laptop heat dissipation\n"
                    "- Anti-slip silicone pads prevent scratching and sliding\n"
                    "- Under-stand storage area fits keyboard and mouse when not in use"
                ),
            },
            {
                "title": "Large Extended Gaming & Office Desk Mat 800x300mm",
                "slug": "demo-extended-desk-mat-800x300mm",
                "category_slug": "monitors-accessories",
                "price": Decimal("1150.00"),
                "compare_at_price": Decimal("1500.00"),
                "stock": 45,
                "weight_grams": 480,
                "image_url": "https://images.unsplash.com/photo-1616469829941-c7200edec809?auto=format&fit=crop&w=600&h=600&q=80",
                "image_filename": "demo_extended_desk_mat.jpg",
                "specifications": {"is_demo": True, "dimensions": "800 x 300 x 3 mm", "surface": "Micro-Weave Cloth", "base": "Non-Slip Natural Rubber"},
                "description": (
                    "### Full-Desk Precision Control Surface\n"
                    "Spacious 800x300mm micro-weave cloth mat accommodating your full-size keyboard and mouse smoothly.\n\n"
                    "### Key Highlights\n"
                    "- Ultra-smooth micro-textured fabric engineered for pixel-precise mouse tracking\n"
                    "- Spill-resistant surface coating wipes clean easily with a damp cloth\n"
                    "- Heavy-duty anti-slip natural rubber base prevents desk slippage\n"
                    "- 360-degree precision anti-fraying stitched border"
                ),
            },
            {
                "title": "7-in-1 Aluminum USB-C Hub with 4K HDMI & 100W PD",
                "slug": "demo-7-in-1-aluminum-usb-c-hub",
                "category_slug": "monitors-accessories",
                "price": Decimal("3400.00"),
                "compare_at_price": Decimal("4200.00"),
                "stock": 25,
                "weight_grams": 110,
                "image_url": "https://images.unsplash.com/photo-1625842268584-8f3296236761?auto=format&fit=crop&w=600&h=600&q=80",
                "image_filename": "demo_7in1_usbc_hub.jpg",
                "specifications": {"is_demo": True, "hdmi": "4K @ 30Hz Output", "pd": "100W Pass-Through Charging", "usb": "2x USB 3.0 (5Gbps)", "card": "SD & TF/MicroSD"},
                "description": (
                    "### Instant Workstation Port Expansion\n"
                    "Expand a single USB-C port into a full workstation hub with 4K HDMI, 100W Power Delivery, SD/TF card readers, and dual USB 3.0 ports.\n\n"
                    "### Key Highlights\n"
                    "- 4K @ 30Hz HDMI video output for external monitors and conference projectors\n"
                    "- 100W USB-C Power Delivery pass-through charges your laptop while working\n"
                    "- 2x high-speed USB 3.0 ports supporting up to 5Gbps data transfer\n"
                    "- Dedicated SD and MicroSD / TF card reader slots for photography workflow\n"
                    "- Heat-dissipating space gray aluminum alloy housing"
                ),
            },
        ]

        self.stdout.write(f"Preparing to seed {len(products_data)} demonstration products...")

        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        created_count = 0
        updated_count = 0

        for item in products_data:
            cat = cat_map.get(item["category_slug"])
            if not cat:
                self.stderr.write(f"Category slug '{item['category_slug']}' not found. Skipping {item['slug']}.")
                continue

            with transaction.atomic():
                prod, created = Product.objects.get_or_create(
                    slug=item["slug"],
                    defaults={
                        "title": item["title"],
                        "category": cat,
                        "product_type": Product.TYPE_PHYSICAL,
                        "description": item["description"],
                        "specifications": item["specifications"],
                        "is_cod_eligible": True,
                        "is_internationally_available": False,
                        "approval_status": Product.STATUS_APPROVED,
                        "is_active": True,
                    },
                )

                if not created and force:
                    prod.title = item["title"]
                    prod.category = cat
                    prod.description = item["description"]
                    prod.specifications = item["specifications"]
                    prod.is_active = True
                    prod.approval_status = Product.STATUS_APPROVED
                    prod.save()

                if created:
                    created_count += 1
                else:
                    updated_count += 1

                # Variant & Inventory
                sku = f"SKU-{item['slug'].replace('demo-', '').upper()[:16]}"
                variant, _ = ProductVariant.objects.get_or_create(
                    product=prod,
                    defaults={
                        "sku": sku,
                        "variant_name": "Standard",
                        "price": item["price"],
                        "compare_at_price": item.get("compare_at_price"),
                        "currency": "NPR",
                        "weight_grams": item["weight_grams"],
                        "is_active": True,
                    },
                )
                if force:
                    variant.price = item["price"]
                    variant.compare_at_price = item.get("compare_at_price")
                    variant.save()

                inventory, _ = ProductInventory.objects.get_or_create(
                    variant=variant,
                    defaults={
                        "quantity": item["stock"],
                        "reserved_quantity": 0,
                        "low_stock_threshold": 5,
                    },
                )
                if force or inventory.quantity == 0:
                    inventory.quantity = item["stock"]
                    inventory.save()

                # Product Image handling
                if not skip_images and prod.images.count() == 0:
                    img_data = None
                    try:
                        req = urllib.request.Request(
                            item["image_url"],
                            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                        )
                        with urllib.request.urlopen(req, context=ssl_ctx, timeout=12) as resp:
                            if resp.status == 200:
                                img_data = resp.read()
                    except Exception as e:
                        self.stderr.write(f"Warning: Could not fetch image for {item['slug']}: {e}")

                    if img_data:
                        try:
                            cf = ContentFile(img_data, name=item["image_filename"])
                            ProductImage.objects.create(
                                product=prod,
                                image=cf,
                                alt_text=item["title"],
                                is_primary=True,
                                display_order=0,
                            )
                            self.stdout.write(f"  [IMG OK] Attached photo to {item['slug']}")
                        except Exception as exc:
                            self.stderr.write(f"  [IMG FAIL] Could not save image for {item['slug']}: {exc}")
                    else:
                        self.stdout.write(f"  [FALLBACK] Using category icon fallback for {item['slug']}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nFinished seeding marketplace demonstration catalog! "
                f"Created: {created_count}, Updated: {updated_count}, Total products processed: {len(products_data)}"
            )
        )
