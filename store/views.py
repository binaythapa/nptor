from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from store.forms import (
    ProductDigitalAssetForm,
    ProductForm,
    ProductInventoryForm,
    ProductReviewActionForm,
    ProductVariantForm,
)
from store.models import Category, Product, ProductInventory, ProductVariant
from vendors.permissions import get_vendor_profile, vendor_required


# ==============================================================================
# PUBLIC STOREFRONT VIEWS
# ==============================================================================

def product_list(request):
    """Public Store catalog listing only approved and active products."""
    products = (
        Product.objects
        .filter(approval_status=Product.STATUS_APPROVED, is_active=True)
        .select_related("category", "vendor")
        .prefetch_related("variants", "images")
        .order_by("-created_at")
    )

    category_slug = request.GET.get("category")
    selected_category = None
    if category_slug:
        selected_category = get_object_or_404(Category, slug=category_slug)
        # Include children categories if any
        cat_ids = [selected_category.id] + list(selected_category.children.values_list("id", flat=True))
        products = products.filter(category_id__in=cat_ids)

    q = request.GET.get("q", "").strip()
    if q:
        products = products.filter(title__icontains=q)

    categories = Category.objects.filter(is_active=True, parent=None).prefetch_related("children")

    return render(
        request,
        "store/product_list.html",
        {
            "products": products,
            "categories": categories,
            "selected_category": selected_category,
            "search_query": q,
        },
    )


def product_detail(request, slug):
    """Public product detail page."""
    product = get_object_or_404(
        Product.objects
        .select_related("category", "vendor")
        .prefetch_related("variants", "variants__inventory", "images"),
        slug=slug,
    )

    # If product is not approved/active, only the owner seller or staff can preview it
    if not (product.approval_status == Product.STATUS_APPROVED and product.is_active):
        vendor = get_vendor_profile(request.user)
        if not (request.user.is_staff or (vendor and product.vendor == vendor)):
            raise PermissionDenied("This product is not currently available on the storefront.")

    primary_variant = product.variants.first()

    return render(
        request,
        "store/product_detail.html",
        {
            "product": product,
            "primary_variant": primary_variant,
            "is_preview": product.approval_status != Product.STATUS_APPROVED,
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
