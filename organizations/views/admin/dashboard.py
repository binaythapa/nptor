from django.shortcuts import render

from organizations.models import AcademicYear, ClassSection, OrganizationClass
from organizations.permissions import org_admin_required
from organizations.services.dashboard import get_overview


@org_admin_required
def org_dashboard(request, slug):
    org = request.organization
    overview = get_overview(org)
    academic_year_count = AcademicYear.objects.filter(organization=org).count()
    academic_class_count = OrganizationClass.objects.filter(organization=org, is_active=True).count()
    academic_section_count = ClassSection.objects.filter(organization=org, is_active=True).count()
    return render(
        request,
        "organizations/admin/dashboard.html",
        {
            "org": org,
            "stats": overview,
            "overview": overview,
            "academic_year_count": academic_year_count,
            "academic_class_count": academic_class_count,
            "academic_section_count": academic_section_count,
        },
    )
