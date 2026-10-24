import json
from decimal import Decimal
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import models, transaction
from django.db.models import Avg, Count, Max, Min, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from store.forms import (
    ProductCustomerReviewForm,
    ProductDigitalAssetForm,
    ProductForm,
    ProductInventoryForm,
    ProductReviewActionForm,
    ProductReviewReportForm,
    ProductVariantForm,
)
from store.models import (
    Category,
    Product,
    ProductImage,
    ProductInventory,
    ProductReview,
    ProductReviewHelpfulVote,
    ProductReviewImage,
    ProductReviewReport,
    ProductVariant,
    ProductVideo,
    Wishlist,
)
from orders.models import OrderItem, SubOrder
from vendors.permissions import get_vendor_profile, vendor_required


# ==============================================================================
# PUBLIC STOREFRONT VIEWS
# ==============================================================================

def product_list(request):
    """Public Store catalog listing with multi-faceted filtering, sorting, and pagination."""
    products = (
        Product.objects
        .filter(approval_status=Product.STATUS_APPROVED, is_active=True)
        .select_related("category", "vendor")
        .prefetch_related("variants", "images", "reviews")
    )

    category_slug = request.GET.get("category", "").strip()
    selected_category = None
    if category_slug:
        selected_category = get_object_or_404(Category, slug=category_slug)
        cat_ids = [selected_category.id] + list(selected_category.children.values_list("id", flat=True))
        products = products.filter(category_id__in=cat_ids)

    q = request.GET.get("q", "").strip()
    if q:
        products = products.filter(Q(title__icontains=q) | Q(description__icontains=q))

    # Price range filtering
    min_price = request.GET.get("min_price", "").strip()
    if min_price:
        try:
            min_p_val = Decimal(min_price)
            products = products.filter(variants__price__gte=min_p_val)
        except Exception:
            min_price = ""

    max_price = request.GET.get("max_price", "").strip()
    if max_price:
        try:
            max_p_val = Decimal(max_price)
            products = products.filter(variants__price__lte=max_p_val)
        except Exception:
            max_price = ""

    # In-stock filter
    in_stock = request.GET.get("in_stock", "").strip()
    if in_stock in ("1", "true", "True"):
        products = products.filter(variants__inventory__quantity__gt=0)

    # Distinct before sorting if joined across variants
    products = products.distinct()

    # Sorting
    sort = request.GET.get("sort", "newest").strip()
    if sort == "price_low":
        products = products.annotate(annotated_min_price=Min("variants__price")).order_by("annotated_min_price", "-created_at")
    elif sort == "price_high":
        products = products.annotate(annotated_max_price=Max("variants__price")).order_by("-annotated_max_price", "-created_at")
    elif sort == "rating":
        products = products.annotate(
            annotated_rating=Avg("reviews__rating", filter=Q(reviews__status=ProductReview.STATUS_APPROVED))
        ).order_by(models.F("annotated_rating").desc(nulls_last=True), "-created_at")
    elif sort == "title_asc":
        products = products.order_by("title")
    else:
        sort = "newest"
        products = products.order_by("-created_at")

    total_count = products.count()

    # Pagination: 12 products per page
    paginator = Paginator(products, 12)
    page_number = request.GET.get("page", 1)
    try:
        page_obj = paginator.get_page(page_number)
    except Exception:
        page_obj = paginator.get_page(1)

    categories = Category.objects.filter(is_active=True, parent=None).prefetch_related("children")

    user_wishlist_ids = set()
    if request.user.is_authenticated:
        user_wishlist_ids = set(Wishlist.objects.filter(user=request.user).values_list("product_id", flat=True))

    return render(
        request,
        "store/product_list.html",
        {
            "products": page_obj.object_list,
            "page_obj": page_obj,
            "total_count": total_count,
            "categories": categories,
            "selected_category": selected_category,
            "search_query": q,
            "min_price": min_price,
            "max_price": max_price,
            "in_stock": in_stock in ("1", "true", "True"),
            "sort": sort,
            "user_wishlist_ids": user_wishlist_ids,
        },
    )


def product_detail(request, slug):
    """Public product detail page with variant matrix, dynamic pricing/stock, media gallery, and genuine reviews."""
    product = get_object_or_404(
        Product.objects
        .select_related("category", "category__parent", "vendor")
        .prefetch_related(
            "variants",
            "variants__inventory",
            "variants__image",
            "images",
            "videos",
            "reviews",
            "reviews__user",
            "reviews__images",
        ),
        slug=slug,
    )

    if not (product.approval_status == Product.STATUS_APPROVED and product.is_active):
        vendor = get_vendor_profile(request.user)
        if not (request.user.is_staff or (vendor and product.vendor == vendor)):
            raise PermissionDenied("This product is not currently available on the storefront.")

    primary_variant = product.variants.first()

    # Variant matrix serialized for client-side JS
    variants_list = []
    attributes_map = {}

    for v in product.variants.filter(is_active=True):
        stock_qty = v.inventory.available_quantity if hasattr(v, "inventory") and v.inventory else 0
        img_url = v.image.image.url if v.image and v.image.image else (product.primary_image.image.url if product.primary_image else "")
        v_dict = {
            "id": v.id,
            "sku": v.sku,
            "variant_name": v.variant_name,
            "price": str(v.price),
            "compare_at_price": str(v.compare_at_price) if v.compare_at_price else "",
            "currency": v.currency,
            "stock": stock_qty,
            "attributes": v.attributes or {},
            "image_url": img_url,
        }
        variants_list.append(v_dict)

        for attr_key, attr_val in (v.attributes or {}).items():
            key_clean = attr_key.strip().capitalize()
            if key_clean not in attributes_map:
                attributes_map[key_clean] = []
            if str(attr_val) not in attributes_map[key_clean]:
                attributes_map[key_clean].append(str(attr_val))

    variants_json = json.dumps(variants_list)

    # Approved customer reviews
    approved_reviews = product.reviews.filter(status=ProductReview.STATUS_APPROVED).select_related("user").prefetch_related("images").order_by("-created_at")

    has_user_reviewed = False
    is_verified_buyer = False
    is_wishlisted = False

    if request.user.is_authenticated:
        has_user_reviewed = product.reviews.filter(user=request.user).exists()
        is_verified_buyer = OrderItem.objects.filter(
            suborder__master_order__user=request.user,
            variant__product=product,
            suborder__fulfillment_status=SubOrder.FULFILLMENT_DELIVERED,
        ).exists()
        is_wishlisted = Wishlist.objects.filter(user=request.user, product=product).exists()

    related_products = (
        Product.objects
        .filter(approval_status=Product.STATUS_APPROVED, is_active=True, category=product.category)
        .exclude(pk=product.pk)
        .select_related("category", "vendor")
        .prefetch_related("variants", "images")[:4]
    )

    recent_ids = request.session.get("store_recently_viewed", [])
    if product.id in recent_ids:
        recent_ids.remove(product.id)
    recent_ids.insert(0, product.id)
    request.session["store_recently_viewed"] = recent_ids[:8]
    request.session.modified = True

    display_recent_ids = [pid for pid in recent_ids if pid != product.id][:4]
    recently_viewed_products = (
        Product.objects
        .filter(id__in=display_recent_ids, approval_status=Product.STATUS_APPROVED, is_active=True)
        .select_related("category", "vendor")
        .prefetch_related("variants", "images")
    ) if display_recent_ids else []

    review_form = ProductCustomerReviewForm()

    return render(
        request,
        "store/product_detail.html",
        {
            "product": product,
            "primary_variant": primary_variant,
            "variants_list": variants_list,
            "variants_json": variants_json,
            "attributes_map": attributes_map,
            "is_preview": product.approval_status != Product.STATUS_APPROVED,
            "approved_reviews": approved_reviews,
            "has_user_reviewed": has_user_reviewed,
            "is_verified_buyer": is_verified_buyer,
            "is_wishlisted": is_wishlisted,
            "related_products": related_products,
            "recently_viewed_products": recently_viewed_products,
            "review_form": review_form,
        },
    )


@login_required
@require_POST
def submit_product_review(request, slug):
    """Submits a customer product review with optional photo attachments and verified purchase validation."""
    product = get_object_or_404(Product, slug=slug, approval_status=Product.STATUS_APPROVED, is_active=True)

    if ProductReview.objects.filter(product=product, user=request.user).exists():
        messages.warning(request, "You have already reviewed this product. Only one review per product is permitted.")
        return redirect(f"{reverse('store:product_detail', kwargs={'slug': slug})}#reviews")

    form = ProductCustomerReviewForm(request.POST, request.FILES)
    if form.is_valid():
        is_verified = OrderItem.objects.filter(
            suborder__master_order__user=request.user,
            variant__product=product,
            suborder__fulfillment_status=SubOrder.FULFILLMENT_DELIVERED,
        ).exists()

        review = form.save(commit=False)
        review.product = product
        review.user = request.user
        review.is_verified_purchase = is_verified
        review.status = ProductReview.STATUS_APPROVED
        review.save()

        files = request.FILES.getlist("review_images")
        for f in files[:3]:
            ProductReviewImage.objects.create(review=review, image=f)

        messages.success(request, "Thank you! Your review has been published.")
    else:
        for err in form.errors.values():
            messages.error(request, "; ".join(err))

    return redirect(f"{reverse('store:product_detail', kwargs={'slug': slug})}#reviews")


@login_required
@require_POST
def vote_review_helpful(request, review_id):
    """Votes a review as helpful with duplicate vote prevention."""
    review = get_object_or_404(ProductReview, pk=review_id)
    vote, created = ProductReviewHelpfulVote.objects.get_or_create(review=review, user=request.user)

    if created:
        review.helpful_count = models.F("helpful_count") + 1
        review.save(update_fields=["helpful_count"])
        review.refresh_from_db(fields=["helpful_count"])
        messages.success(request, "Thank you for your feedback.")
    else:
        messages.info(request, "You have already marked this review as helpful.")

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"status": "ok", "helpful_count": review.helpful_count, "created": created})

    return redirect(request.META.get("HTTP_REFERER", reverse("store:product_list")))


@login_required
@require_POST
def report_product_review(request, review_id):
    """Reports a product review for customer moderation."""
    review = get_object_or_404(ProductReview, pk=review_id)
    reason = request.POST.get("reason", "").strip() or "Inappropriate content"
    ProductReviewReport.objects.create(review=review, reporter=request.user, reason=reason)
    messages.success(request, "Thank you. The review has been reported to moderators for inspection.")
    return redirect(request.META.get("HTTP_REFERER", reverse("store:product_list")))


@login_required
def wishlist_toggle(request, product_id):
    """Adds or removes a product from the customer's wishlist."""
    product = get_object_or_404(Product, pk=product_id, approval_status=Product.STATUS_APPROVED, is_active=True)
    item = Wishlist.objects.filter(user=request.user, product=product).first()

    if item:
        item.delete()
        added = False
        messages.info(request, f"Removed '{product.title}' from your wishlist.")
    else:
        Wishlist.objects.create(user=request.user, product=product)
        added = True
        messages.success(request, f"Added '{product.title}' to your wishlist.")

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"status": "ok", "added": added, "product_id": product_id})

    return redirect(request.META.get("HTTP_REFERER", reverse("store:product_list")))


@login_required
def wishlist_view(request):
    """Displays the customer's saved wishlist products."""
    wishlist_items = (
        Wishlist.objects
        .filter(user=request.user)
        .select_related("product", "product__category", "product__vendor")
        .prefetch_related("product__variants", "product__images")
        .order_by("-created_at")
    )
    return render(
        request,
        "store/wishlist.html",
        {
            "wishlist_items": wishlist_items,
        },
    )


# ==============================================================================
# SELLER PORTAL VIEWS (TENANT ISOLATED)
# ==============================================================================

@vendor_required
def vendor_product_list(request):
    """Seller's view of their own products with zero cross-tenant leakage."""
    vendor = request.user.vendor_profile
    products = (
        Product.objects
        .filter(vendor=vendor)
        .select_related("category")
        .prefetch_related("variants")
        .order_by("-updated_at")
    )
    return render(
        request,
        "store/vendor/product_list.html",
        {
            "vendor": vendor,
            "products": products,
        },
    )


@vendor_required
def vendor_product_create(request):
    """Seller creates a new product in draft status with initial variant and inventory."""
    vendor = request.user.vendor_profile

    if request.method == "POST":
        p_form = ProductForm(request.POST)
        v_form = ProductVariantForm(request.POST)
        i_form = ProductInventoryForm(request.POST)

        if p_form.is_valid() and v_form.is_valid() and i_form.is_valid():
            with transaction.atomic():
                product = p_form.save(vendor=vendor, commit=True)
                product.approval_status = Product.STATUS_DRAFT
                product.is_active = False
                product.save(update_fields=["approval_status", "is_active"])

                variant = v_form.save(commit=False)
                variant.product = product
                variant.currency = "NPR"
                variant.save()

                inventory = i_form.save(commit=False)
                inventory.variant = variant
                inventory.save()

            messages.success(request, f"Product '{product.title}' created as Draft. You can now submit it for review.")
            return redirect(reverse("store:vendor_product_list"))
    else:
        p_form = ProductForm()
        v_form = ProductVariantForm(initial={"variant_name": "Standard"})
        i_form = ProductInventoryForm(initial={"quantity": 10, "low_stock_threshold": 2})

    return render(
        request,
        "store/vendor/product_form.html",
        {
            "p_form": p_form,
            "v_form": v_form,
            "i_form": i_form,
            "action_title": "Create Product",
        },
    )


@vendor_required
def vendor_product_edit(request, pk):
    """Seller edits their existing draft or changes_required product."""
    vendor = request.user.vendor_profile
    # Hard-filtered to ensure zero tenant leakage: 404 if not owned by this seller
    product = get_object_or_404(Product, pk=pk, vendor=vendor)

    if product.approval_status == Product.STATUS_PENDING:
        messages.warning(request, "This product is currently under review and cannot be edited until reviewed.")
        return redirect(reverse("store:vendor_product_list"))

    variant = product.variants.first()
    inventory = getattr(variant, "inventory", None) if variant else None

    if request.method == "POST":
        p_form = ProductForm(request.POST, instance=product)
        v_form = ProductVariantForm(request.POST, instance=variant) if variant else None
        i_form = ProductInventoryForm(request.POST, instance=inventory) if inventory else None

        forms_valid = p_form.is_valid() and (not v_form or v_form.is_valid()) and (not i_form or i_form.is_valid())
        if forms_valid:
            with transaction.atomic():
                p_form.save(vendor=vendor)
                if v_form:
                    v_form.save()
                if i_form:
                    i_form.save()

            messages.success(request, f"Product '{product.title}' updated successfully.")
            return redirect(reverse("store:vendor_product_list"))
    else:
        p_form = ProductForm(instance=product)
        v_form = ProductVariantForm(instance=variant) if variant else None
        i_form = ProductInventoryForm(instance=inventory) if inventory else None

    return render(
        request,
        "store/vendor/product_form.html",
        {
            "p_form": p_form,
            "v_form": v_form,
            "i_form": i_form,
            "product": product,
            "action_title": f"Edit {product.title}",
        },
    )


@vendor_required
def vendor_product_submit(request, pk):
    """Seller submits a product for administrative moderation review."""
    if request.method != "POST":
        raise PermissionDenied("POST required.")

    vendor = request.user.vendor_profile
    product = get_object_or_404(Product, pk=pk, vendor=vendor)

    if product.approval_status not in (Product.STATUS_DRAFT, Product.STATUS_CHANGES_REQUIRED):
        messages.error(request, "Only Draft or Changes-Required products can be submitted for review.")
        return redirect(reverse("store:vendor_product_list"))

    product.approval_status = Product.STATUS_PENDING
    product.submitted_at = timezone.now()
    product.save(update_fields=["approval_status", "submitted_at", "updated_at"])

    messages.success(request, f"Product '{product.title}' submitted for review!")
    return redirect(reverse("store:vendor_product_list"))


# ==============================================================================
# ADMINISTRATIVE MODERATION VIEWS
# ==============================================================================

@staff_member_required
def admin_moderation_queue(request):
    """Staff view of products awaiting moderation."""
    status_filter = request.GET.get("status", Product.STATUS_PENDING)
    products = (
        Product.objects
        .filter(approval_status=status_filter)
        .select_related("vendor", "category", "reviewed_by")
        .prefetch_related("variants")
        .order_by("-submitted_at", "-updated_at")
    )
    return render(
        request,
        "store/admin/moderation_queue.html",
        {
            "products": products,
            "status_filter": status_filter,
            "pending_count": Product.objects.filter(approval_status=Product.STATUS_PENDING).count(),
        },
    )


@staff_member_required
def admin_moderate_product(request, pk):
    """Staff reviews and approves, requests changes, or rejects a product."""
    product = get_object_or_404(
        Product.objects.select_related("vendor", "category").prefetch_related("variants", "variants__inventory"),
        pk=pk,
    )

    if request.method == "POST":
        form = ProductReviewActionForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data["action"]
            notes = form.cleaned_data["review_notes"]

            product.reviewed_by = request.user
            product.reviewed_at = timezone.now()
            product.review_notes = notes

            if action == ProductReviewActionForm.ACTION_APPROVE:
                product.approval_status = Product.STATUS_APPROVED
                product.is_active = True
                messages.success(request, f"Product '{product.title}' has been approved and published to the store!")
            elif action == ProductReviewActionForm.ACTION_CHANGES_REQUIRED:
                product.approval_status = Product.STATUS_CHANGES_REQUIRED
                product.is_active = False
                messages.warning(request, f"Product '{product.title}' returned to seller with changes required.")
            elif action == ProductReviewActionForm.ACTION_REJECT:
                product.approval_status = Product.STATUS_REJECTED
                product.is_active = False
                messages.error(request, f"Product '{product.title}' has been rejected.")

            product.save(update_fields=["approval_status", "is_active", "reviewed_by", "reviewed_at", "review_notes", "updated_at"])
            return redirect(reverse("store:admin_moderation_queue"))
    else:
        form = ProductReviewActionForm()

    return render(
        request,
        "store/admin/moderate_product.html",
        {
            "product": product,
            "form": form,
        },
    )
