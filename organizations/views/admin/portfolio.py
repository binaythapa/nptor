from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from organizations.models import OrganizationPortfolioSection, OrganizationPortalConfig, OrganizationProfile
from organizations.permissions import org_admin_required


@org_admin_required
@require_http_methods(["GET", "POST"])
def org_portfolio(request, slug):
    organization = request.organization
    profile, _ = OrganizationProfile.objects.get_or_create(
        organization=organization,
        defaults={"display_name": organization.name},
    )
    config, _ = OrganizationPortalConfig.objects.get_or_create(
        organization=organization,
        defaults={"hero_title": organization.name, "primary_color": organization.primary_color or ""},
    )
    if request.method == "POST":
        action = request.POST.get("action", "save")
        if action == "publish":
            config.is_published = True
            config.save(update_fields=["is_published", "updated_at"])
            messages.success(request, "Organization portal published.")
        elif action == "unpublish":
            config.is_published = False
            config.save(update_fields=["is_published", "updated_at"])
            messages.success(request, "Organization portal unpublished.")
        else:
            profile.display_name = request.POST.get("display_name", "").strip() or organization.name
            profile.tagline = request.POST.get("tagline", "").strip()
            profile.description = request.POST.get("description", "")
            profile.website = request.POST.get("website", "").strip()
            profile.email = request.POST.get("email", "").strip()
            profile.phone = request.POST.get("phone", "").strip()
            profile.address = request.POST.get("address", "")
            profile.city = request.POST.get("city", "").strip()
            profile.country = request.POST.get("country", "").strip()
            if request.FILES.get("logo"):
                profile.logo = request.FILES["logo"]
            if request.FILES.get("cover_image"):
                profile.cover_image = request.FILES["cover_image"]
            profile.save()
            config.primary_color = request.POST.get("primary_color", "").strip()
            config.secondary_color = request.POST.get("secondary_color", "").strip()
            config.hero_title = request.POST.get("hero_title", "").strip()
            config.hero_subtitle = request.POST.get("hero_subtitle", "")
            config.welcome_message = request.POST.get("welcome_message", "")
            config.custom_footer_text = request.POST.get("custom_footer_text", "")
            config.show_courses = "show_courses" in request.POST
            config.show_tracks = "show_tracks" in request.POST
            config.show_exams = "show_exams" in request.POST
            config.show_about = "show_about" in request.POST
            config.show_testimonials = "show_testimonials" in request.POST
            config.show_contact = "show_contact" in request.POST
            if request.FILES.get("hero_image"):
                config.hero_image = request.FILES["hero_image"]
            config.save()
            messages.success(request, "Portfolio draft saved. Publish when ready.")
        return redirect("organizations_admin:portfolio", slug=organization.slug)
    return render(request, "organizations/admin/portfolio.html", {
        "org": organization,
        "profile": profile,
        "config": config,
        "sections": OrganizationPortfolioSection.objects.filter(organization=organization),
    })
