from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from organizations.permissions import org_admin_required
from organizations.services.payment_gateway import get_payment_gateway
from organizations.services.public_resource_checkout import (
    PublicResourceCheckoutError,
    complete_organization_checkout,
)
from subscriptions.models import Payment


@require_http_methods(["GET", "POST"])
@org_admin_required
def organization_payment_checkout(request, slug, payment_id):
    payment = get_object_or_404(
        Payment.objects.select_related("subscription", "subscription__plan", "organization"),
        pk=payment_id,
        organization=request.organization,
    )

    if request.method == "POST":
        reference = request.POST.get("reference") or f"DUMMY-{payment.pk}"
        try:
            complete_organization_checkout(
                payment.pk,
                actor=request.user,
                reference=reference,
            )
        except PublicResourceCheckoutError as exc:
            messages.error(request, str(exc))
            return redirect(
                "organizations_admin:organization_payment_checkout",
                slug=slug,
                payment_id=payment.pk,
            )

        messages.success(
            request,
            "Payment successful. The organization subscription is now active and the resource can be assigned to students.",
        )
        return redirect("organizations_admin:courses", slug=slug)

    gateway = get_payment_gateway()
    checkout = gateway.create_checkout(payment=payment)
    return render(
        request,
        "organizations/admin/payment/checkout.html",
        {
            "payment": payment,
            "subscription": payment.subscription,
            "gateway": gateway,
            "reference": checkout.reference,
            "organization": request.organization,
        },
    )
