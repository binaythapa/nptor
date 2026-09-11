from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from organizations.forms.access_request import OrganizationAccessRequestForm
from organizations.models.access_request import OrganizationAccessRequest
from organizations.services.access_requests import submit_access_request


@login_required
@require_http_methods(["GET", "POST"])
def request_access(request):
    if request.method == "POST":
        form = OrganizationAccessRequestForm(request.POST)
        if form.is_valid():
            try:
                access_request = submit_access_request(
                    request.user,
                    form.cleaned_data["organization"],
                    form.cleaned_data["service"],
                    form.cleaned_data["requested_role"],
                    form.cleaned_data["reason"],
                )
            except ValidationError as exc:
                form.add_error(None, exc.message)
            else:
                messages.success(request, "Your organization access request has been submitted for review.")
                return redirect("organizations_public:request_status")
    else:
        form = OrganizationAccessRequestForm()
    return render(request, "organizations/access_requests/form.html", {"form": form})


@login_required
def request_status(request):
    requests = OrganizationAccessRequest.objects.filter(user=request.user).select_related("organization", "reviewed_by")[:50]
    return render(request, "organizations/access_requests/status.html", {"requests": requests})
