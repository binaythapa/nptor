from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0004_organization_audit"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organizationdomain",
            name="organization",
            field=__import__("django.db.models", fromlist=["ForeignKey"]).ForeignKey(
                on_delete=__import__("django.db.models.deletion", fromlist=["CASCADE"]).CASCADE,
                related_name="organization_domains",
                to="organizations.organization",
            ),
        ),
    ]
