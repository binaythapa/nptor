from django import forms

from organizations.models.access_request import OrganizationAccessRequest
from organizations.models.organization import Organization
from organizations.models.role import OrganizationRole


class OrganizationAccessRequestForm(forms.ModelForm):
    class Meta:
        model = OrganizationAccessRequest
        fields = ["organization", "service", "requested_role", "reason"]
        widgets = {"reason": forms.Textarea(attrs={"rows": 4, "placeholder": "Tell the administrator why you need access."})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["organization"].queryset = Organization.objects.filter(is_active=True).order_by("name")
        self.fields["service"].choices = OrganizationAccessRequest.SERVICE_CHOICES
        self.fields["requested_role"].choices = (
            (OrganizationRole.STUDENT, "Student"),
            (OrganizationRole.STAFF, "Staff / Teacher"),
            (OrganizationRole.ORG_ADMIN, "Organization Admin"),
            (OrganizationRole.ORG_OWNER, "Organization Owner"),
        )
