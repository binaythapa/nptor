from django.db import migrations, models
import django.db.models.deletion
from django.db.models.functions import Lower


def create_portal_defaults(apps, schema_editor):
    Organization = apps.get_model("organizations", "Organization")
    Profile = apps.get_model("organizations", "OrganizationProfile")
    PortalConfig = apps.get_model("organizations", "OrganizationPortalConfig")
    for organization in Organization.objects.all().iterator():
        Profile.objects.get_or_create(
            organization_id=organization.pk,
            defaults={
                "display_name": organization.name,
                "logo": organization.logo.name if organization.logo else None,
            },
        )
        PortalConfig.objects.get_or_create(
            organization_id=organization.pk,
            defaults={
                "primary_color": organization.primary_color or "",
                "hero_title": organization.name,
                "is_published": False,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("organizations", "0002_initial")]

    operations = [
        migrations.CreateModel(
            name="OrganizationDomain",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("domain", models.CharField(max_length=255)),
                ("domain_type", models.CharField(choices=[("nptor_subdomain", "NPTOR Subdomain"), ("custom", "Custom Domain")], default="custom", max_length=30)),
                ("is_primary", models.BooleanField(default=False)),
                ("is_verified", models.BooleanField(default=False)),
                ("verification_token", models.CharField(blank=True, max_length=128)),
                ("ssl_status", models.CharField(choices=[("pending", "Pending"), ("active", "Active"), ("error", "Error")], default="pending", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="domains", to="organizations.organization")),
            ],
            options={
                "ordering": ["-is_primary", "domain"],
                "indexes": [models.Index(fields=["organization", "is_verified"], name="org_domain_verified_idx")],
                "constraints": [
                    models.UniqueConstraint(Lower("domain"), name="org_domain_ci_unique"),
                    models.UniqueConstraint(fields=["organization"], condition=models.Q(is_primary=True), name="org_one_primary_domain"),
                ],
            },
        ),
        migrations.CreateModel(
            name="OrganizationPortfolioSection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("section_type", models.CharField(choices=[("hero", "Hero"), ("about", "About"), ("featured_courses", "Featured Courses"), ("learning_programs", "Learning Programs"), ("achievements", "Achievements"), ("testimonials", "Testimonials"), ("contact", "Contact"), ("custom_text", "Custom Text")], max_length=40)),
                ("title", models.CharField(blank=True, max_length=255)),
                ("subtitle", models.CharField(blank=True, max_length=255)),
                ("content", models.TextField(blank=True)),
                ("image", models.ImageField(blank=True, null=True, upload_to="org/portfolios/")),
                ("display_order", models.PositiveIntegerField(default=0)),
                ("is_enabled", models.BooleanField(default=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="portfolio_sections", to="organizations.organization")),
            ],
            options={"ordering": ["display_order", "id"], "indexes": [models.Index(fields=["organization", "is_enabled", "display_order"], name="org_portal_section_idx")]},
        ),
        migrations.CreateModel(
            name="OrganizationPortalConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("primary_color", models.CharField(blank=True, max_length=20)),
                ("secondary_color", models.CharField(blank=True, max_length=20)),
                ("hero_title", models.CharField(blank=True, max_length=255)),
                ("hero_subtitle", models.TextField(blank=True)),
                ("hero_image", models.ImageField(blank=True, null=True, upload_to="org/portals/hero/")),
                ("welcome_message", models.TextField(blank=True)),
                ("show_courses", models.BooleanField(default=True)),
                ("show_tracks", models.BooleanField(default=True)),
                ("show_exams", models.BooleanField(default=True)),
                ("show_about", models.BooleanField(default=True)),
                ("show_testimonials", models.BooleanField(default=True)),
                ("show_contact", models.BooleanField(default=True)),
                ("custom_footer_text", models.TextField(blank=True)),
                ("is_published", models.BooleanField(default=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("organization", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="portal_config", to="organizations.organization")),
            ],
        ),
        migrations.CreateModel(
            name="OrganizationProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("display_name", models.CharField(blank=True, max_length=255)),
                ("tagline", models.CharField(blank=True, max_length=255)),
                ("description", models.TextField(blank=True)),
                ("logo", models.ImageField(blank=True, null=True, upload_to="org/profiles/logos/")),
                ("cover_image", models.ImageField(blank=True, null=True, upload_to="org/profiles/covers/")),
                ("favicon", models.ImageField(blank=True, null=True, upload_to="org/profiles/favicons/")),
                ("website", models.URLField(blank=True)),
                ("email", models.EmailField(blank=True)),
                ("phone", models.CharField(blank=True, max_length=50)),
                ("address", models.TextField(blank=True)),
                ("city", models.CharField(blank=True, max_length=100)),
                ("country", models.CharField(blank=True, max_length=100)),
                ("social_links", models.JSONField(blank=True, default=dict)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("organization", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="profile", to="organizations.organization")),
            ],
        ),
        migrations.RunPython(create_portal_defaults, migrations.RunPython.noop),
    ]
