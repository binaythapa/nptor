from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0009_organization_access_request"),
    ]

    operations = [
        migrations.AddField(
            model_name="organizationstudent",
            name="contact_phone",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="organizationstudent",
            name="guardian_email",
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name="organizationstudent",
            name="guardian_relationship",
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
