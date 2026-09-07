from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from organizations.models import OrganizationAuditLog, OrganizationPortfolioSection, OrganizationPortalConfig, OrganizationProfile
from organizations.permissions import org_admin_required


@org_admin_required
@require_http_methods(["GET", "POST"])
def org_portfolio(request, slug):
    organization = request.organization
    profile, _ = OrganizationProfile.objects.get_or_create(organization=organization, defaults={"display_name": organization.name})
    config, _ = OrganizationPortalConfig.objects.get_or_create(organization=organization, defaults={"hero_title": organization.name, "primary_color": organization.primary_color or ""})
    if request.method == "POST":
        action = request.POST.get("action", "save")
        if action in {"publish", "unpublish"}:
            config.is_published = action == "publish"
            config.save(update_fields=["is_published", "updated_at"])
            OrganizationAuditLog.objects.create(organization=organization, actor=request.user, action=f"portal_{action}", target_type="OrganizationPortalConfig", target_id=str(config.pk))
            messages.success(request, f"Organization portal {'published' if config.is_published else 'unpublished'}.")
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
            if request.FILES.get("logo"): profile.logo = request.FILES["logo"]
            if request.FILES.get("cover_image"): profile.cover_image = request.FILES["cover_image"]
            profile.save()
            config.primary_color = request.POST.get("primary_color", "").strip()
            config.secondary_color = request.POST.get("secondary_color", "").strip()
            config.hero_title = request.POST.get("hero_title", "").strip()
            config.hero_subtitle = request.POST.get("hero_subtitle", "")
            config.welcome_message = request.POST.get("welcome_message", "")
            config.custom_footer_text = request.POST.get("custom_footer_text", "")
            for field in ("courses", "tracks", "exams", "about", "testimonials", "contact"):
                setattr(config, f"show_{field}", f"show_{field}" in request.POST)
            if request.FILES.get("hero_image"): config.hero_image = request.FILES["hero_image"]
            config.save()
            OrganizationAuditLog.objects.create(organization=organization, actor=request.user, action="portal_draft_saved", target_type="OrganizationPortalConfig", target_id=str(config.pk))
            messages.success(request, "Portfolio draft saved. Publish when ready.")
        return redirect("organizations_admin:portfolio", slug=organization.slug)
    return render(request, "organizations/admin/portfolio.html", {"org": organization, "profile": profile, "config": config, "sections": OrganizationPortfolioSection.objects.filter(organization=organization)})
