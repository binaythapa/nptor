from decimal import Decimal
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from orders.models import Order, SubOrder
from vendors.models import VendorLedger, VendorPayout, VendorProfile
from vendors.services.settlement_service import SettlementService


@staff_member_required
def admin_settlement_dashboard(request):
    """
    Staff settlement overview:
    - Vendor balances (holding vs available for payout)
    - Pending COD remittances awaiting courier reconciliation
    """
    vendors = VendorProfile.objects.filter(status=VendorProfile.STATUS_ACTIVE).select_related("user")
    vendor_summaries = []

    for v in vendors:
        summary = SettlementService.get_vendor_financial_summary(v)
        summary["vendor"] = v
        vendor_summaries.append(summary)

    # Suborders delivered via COD awaiting courier remittance reconciliation
    pending_cod_reconciliations = (
        SubOrder.objects
        .filter(
            master_order__payment_method=Order.PAYMENT_METHOD_COD,
            master_order__cod_collection_status=Order.COD_STATUS_COLLECTED_BY_COURIER,
        )
        .select_related("master_order", "vendor")
        .order_by("-delivered_at")[:20]
    )

    return render(
        request,
        "vendors/admin_settlement_dashboard.html",
        {
            "vendor_summaries": vendor_summaries,
            "pending_cod_reconciliations": pending_cod_reconciliations,
        },
    )


@staff_member_required
def admin_vendor_ledger_view(request, vendor_id):
    """
    Detailed auditable ledger history for a specific seller.
    """
    vendor = get_object_or_404(VendorProfile, id=vendor_id)
    summary = SettlementService.get_vendor_financial_summary(vendor)
    entries = vendor.ledger_entries.select_related("suborder").order_by("-created_at")

    return render(
        request,
        "vendors/admin_vendor_ledger.html",
        {
            "vendor": vendor,
            "summary": summary,
            "entries": entries,
        },
    )


@staff_member_required
def admin_payout_queue(request):
    """
    Auditable list of all vendor payouts across lifecycle stages:
    proposed -> approved -> submitted -> confirmed / failed.
    """
    status_filter = request.GET.get("status", "")
    payouts = VendorPayout.objects.select_related("vendor", "disbursed_by").order_by("-created_at")

    if status_filter:
        payouts = payouts.filter(status=status_filter)

    return render(
        request,
        "vendors/admin_payout_queue.html",
        {
            "payouts": payouts,
            "status_filter": status_filter,
            "status_choices": VendorPayout.STATUS_CHOICES,
        },
    )


@staff_member_required
def admin_payout_action(request, payout_id):
    """
    Transition payout state (approve, submit, confirm, reject).
    Guarantees no real bank API is called and confirmation requires manual staff audit.
    """
    if request.method != "POST":
        raise PermissionDenied("POST required.")

    payout = get_object_or_404(VendorPayout, id=payout_id)
    action = request.POST.get("action")

    try:
        if action == "approve":
            SettlementService.approve_payout(payout.id, actor=request.user)
            messages.success(request, f"Payout {payout.payout_reference} approved.")
        elif action == "submit":
            bank_ref = request.POST.get("bank_transaction_reference", "").strip()
            SettlementService.submit_payout_to_bank(payout.id, bank_transaction_reference=bank_ref, actor=request.user)
            messages.success(request, f"Payout {payout.payout_reference} marked as submitted to bank.")
        elif action == "confirm":
            SettlementService.confirm_payout(payout.id, actor=request.user)
            messages.success(request, f"Payout {payout.payout_reference} confirmed and ledger settled.")
        elif action == "reject":
            reason = request.POST.get("rejection_reason", "").strip()
            SettlementService.reject_payout(payout.id, reason=reason, actor=request.user)
            messages.warning(request, f"Payout {payout.payout_reference} rejected. Funds returned to vendor available balance.")
        else:
            messages.error(request, f"Invalid payout action '{action}'.")
    except ValidationError as err:
        messages.error(request, str(err))

    return redirect(reverse("vendors:admin_payout_queue"))
