from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("organizations", "0005_organization_domain_related_name")]

    operations = [
        migrations.RemoveConstraint(
            model_name="organizationdomain",
            name="org_one_primary_domain",
        ),
    ]
