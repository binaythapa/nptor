from django.contrib import messages
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from organizations.forms.account_request import OrganizationAccountRequestForm
from organizations.models.account_request import OrganizationAccountRequest
from organizations.permissions import platform_admin_required
from organizations.services.account_requests import (
    approve_organization_account_request,
    reject_organization_account_request,
    submit_organization_account_request,
)


@login_required
def organization_account_request(request):
    existing = OrganizationAccountRequest.objects.filter(user=request.user).order_by("-created_at").first()
    if existing and existing.status == OrganizationAccountRequest.STATUS_PENDING:
        return redirect("quiz:profile")
    if existing and existing.status == OrganizationAccountRequest.STATUS_APPROVED:
        return redirect("quiz:profile")

    if request.method == "POST":
        form = OrganizationAccountRequestForm(request.POST)
        if form.is_valid():
            try:
                submit_organization_account_request(request.user, form.cleaned_data)
            except ValidationError as exc:
                form.add_error(None, exc.message)
            else:
                messages.success(request, "Your organization account request has been submitted for review.")
                return redirect("quiz:profile")
    else:
        form = OrganizationAccountRequestForm(
            initial={"contact_email": request.user.email}
        )

    return render(
        request,
        "accounts/organization_account_request.html",
        {"form": form},
    )


@platform_admin_required
def organization_account_requests(request):
    status = request.GET.get("status", OrganizationAccountRequest.STATUS_PENDING)
    qs = OrganizationAccountRequest.objects.select_related("user", "organization", "reviewed_by")
    if status and status != "ALL":
        qs = qs.filter(status=status)
    return render(
        request,
        "accounts/admin/organization_account_requests.html",
        {
            "requests": qs[:100],
            "status": status,
            "status_choices": OrganizationAccountRequest.STATUS_CHOICES,
        },
    )


@platform_admin_required
def organization_account_request_detail(request, pk):
    access_request = get_object_or_404(
        OrganizationAccountRequest.objects.select_related("user", "organization", "reviewed_by"),
        pk=pk,
    )
    return render(
        request,
        "accounts/admin/organization_account_request_detail.html",
        {"access_request": access_request},
    )


@platform_admin_required
@require_POST
def organization_account_request_approve(request, pk):
    access_request = get_object_or_404(OrganizationAccountRequest, pk=pk)
    try:
        approve_organization_account_request(
            access_request,
            request.user,
            request.POST.get("review_notes", ""),
        )
    except ValidationError as exc:
        messages.error(request, exc.message)
    else:
        messages.success(request, "Organization account request approved.")
    return redirect("accounts:organization-account-request-detail", pk=pk)


@platform_admin_required
@require_POST
def organization_account_request_reject(request, pk):
    access_request = get_object_or_404(OrganizationAccountRequest, pk=pk)
    try:
        reject_organization_account_request(
            access_request,
            request.user,
            request.POST.get("review_notes", ""),
        )
    except ValidationError as exc:
        messages.error(request, exc.message)
    else:
        messages.success(request, "Organization account request rejected.")
    return redirect("accounts:organization-account-request-detail", pk=pk)
