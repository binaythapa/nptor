from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from organizations.models.access_request import OrganizationAccessRequest
from organizations.permissions import platform_admin_required
from organizations.services.access_requests import approve_access_request, reject_access_request


@platform_admin_required
def organization_requests(request):
    status = request.GET.get("status", OrganizationAccessRequest.STATUS_PENDING)
    service = request.GET.get("service")
    qs = OrganizationAccessRequest.objects.select_related("user", "organization", "reviewed_by")
    if status:
        qs = qs.filter(status=status)
    if service:
        qs = qs.filter(service=service)
    return render(request, "accounts/admin/organization_requests.html", {"requests": qs[:100], "status": status, "services": OrganizationAccessRequest.SERVICE_CHOICES})


@platform_admin_required
def organization_request_detail(request, pk):
    access_request = get_object_or_404(OrganizationAccessRequest.objects.select_related("user", "organization", "reviewed_by"), pk=pk)
    return render(request, "accounts/admin/organization_request_detail.html", {"access_request": access_request})


@platform_admin_required
@require_POST
def organization_request_approve(request, pk):
    access_request = get_object_or_404(OrganizationAccessRequest, pk=pk)
    try:
        approve_access_request(access_request, request.user, request.POST.get("review_notes", ""))
    except ValidationError as exc:
        messages.error(request, exc.message)
    else:
        messages.success(request, "Organization access request approved.")
    return redirect("accounts:organization_request_detail", pk=pk)


@platform_admin_required
@require_POST
def organization_request_reject(request, pk):
    access_request = get_object_or_404(OrganizationAccessRequest, pk=pk)
    try:
        reject_access_request(access_request, request.user, request.POST.get("review_notes", ""))
    except ValidationError as exc:
        messages.error(request, exc.message)
    else:
        messages.success(request, "Organization access request rejected.")
    return redirect("accounts:organization_request_detail", pk=pk)
