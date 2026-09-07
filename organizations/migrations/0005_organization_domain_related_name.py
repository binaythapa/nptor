from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0004_organization_audit"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organizationdomain",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="organization_domains",
                to="organizations.organization",
            ),
        ),
    ]
