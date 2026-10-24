from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from store.models import Product
from vendors.forms import VendorOnboardingForm
from vendors.models import VendorProfile
from vendors.permissions import get_vendor_profile


@login_required
def vendor_onboarding(request):
    """Allow an authenticated user to apply to become a seller."""
    existing_profile = get_vendor_profile(request.user)
    if existing_profile:
        return redirect(reverse("vendors:dashboard"))

    if request.method == "POST":
        form = VendorOnboardingForm(request.POST)
        if form.is_valid():
            profile = form.save(user=request.user)
            messages.success(
                request,
                f"Application for '{profile.store_name}' submitted successfully! It is pending review.",
            )
            return redirect(reverse("vendors:dashboard"))
    else:
        form = VendorOnboardingForm(initial={"business_email": request.user.email})

    return render(request, "vendors/onboarding.html", {"form": form})


@login_required
def vendor_dashboard(request):
    """Seller portal dashboard."""
    profile = get_vendor_profile(request.user)
    if not profile:
        return redirect(reverse("vendors:onboarding"))

    products = Product.objects.filter(vendor=profile)
    stats = {
        "total_products": products.count(),
        "draft_products": products.filter(approval_status=Product.STATUS_DRAFT).count(),
        "pending_products": products.filter(approval_status=Product.STATUS_PENDING).count(),
        "approved_products": products.filter(approval_status=Product.STATUS_APPROVED).count(),
    }

    return render(
        request,
        "vendors/dashboard.html",
        {
            "profile": profile,
            "stats": stats,
            "recent_products": products.order_by("-updated_at")[:5],
        },
    )


@staff_member_required
def admin_vendor_queue(request):
    """Staff moderation queue for pending seller applications."""
    status_filter = request.GET.get("status", VendorProfile.STATUS_PENDING)
    vendors = VendorProfile.objects.filter(status=status_filter).select_related("user").order_by("-created_at")
    return render(
        request,
        "vendors/admin_queue.html",
        {
            "vendors": vendors,
            "status_filter": status_filter,
            "pending_count": VendorProfile.objects.filter(status=VendorProfile.STATUS_PENDING).count(),
        },
    )


@staff_member_required
def admin_vendor_action(request, pk):
    """Staff action to approve, suspend, or reactivate a seller."""
    if request.method != "POST":
        raise PermissionDenied("POST required.")

    vendor = get_object_or_404(VendorProfile, pk=pk)
    action = request.POST.get("action")

    if action == "approve":
        vendor.status = VendorProfile.STATUS_ACTIVE
        vendor.approved_by = request.user
        vendor.approved_at = timezone.now()
        vendor.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        messages.success(request, f"Vendor '{vendor.store_name}' approved successfully!")
    elif action == "suspend":
        vendor.status = VendorProfile.STATUS_SUSPENDED
        vendor.save(update_fields=["status", "updated_at"])
        messages.warning(request, f"Vendor '{vendor.store_name}' suspended.")
    elif action == "reactivate":
        vendor.status = VendorProfile.STATUS_ACTIVE
        vendor.save(update_fields=["status", "updated_at"])
        messages.success(request, f"Vendor '{vendor.store_name}' reactivated.")
    else:
        messages.error(request, "Invalid moderation action.")

    return redirect(reverse("vendors:admin_queue"))
