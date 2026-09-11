import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0008_class_resource_assignment"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="OrganizationAccessRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("service", models.CharField(choices=[("ORGANIZATION_ACCESS", "Organization access")], default="ORGANIZATION_ACCESS", max_length=40)),
                ("requested_role", models.CharField(blank=True, choices=[("org_owner", "Organization Owner"), ("org_admin", "Organization Admin"), ("staff", "Staff / Teacher"), ("student", "Student")], max_length=20, null=True)),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("APPROVED", "Approved"), ("REJECTED", "Rejected"), ("REVOKED", "Revoked")], db_index=True, default="PENDING", max_length=20)),
                ("reason", models.TextField(blank=True)),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("review_notes", models.TextField(blank=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="access_requests", to="organizations.organization")),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_organization_access_requests", to=settings.AUTH_USER_MODEL)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="organization_access_requests", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-requested_at"],
                "indexes": [
                    models.Index(fields=["organization", "status"], name="org_access_req_org_status_idx"),
                    models.Index(fields=["user", "status"], name="org_access_req_user_status_idx"),
                    models.Index(fields=["service", "status"], name="org_access_req_service_idx"),
                ],
            },
        ),
    ]
