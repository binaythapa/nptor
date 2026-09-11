from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_initial")]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="is_platform_admin",
            field=models.BooleanField(default=False, db_index=True, help_text="Explicit NPTOR platform administrator permission."),
        ),
        migrations.AddField(
            model_name="notification",
            name="notification_type",
            field=models.CharField(default="system", max_length=50),
        ),
        migrations.AddField(
            model_name="notification",
            name="priority",
            field=models.CharField(choices=[("info", "Info"), ("success", "Success"), ("warning", "Warning"), ("critical", "Critical")], default="info", max_length=20),
        ),
        migrations.AddField(
            model_name="notification",
            name="target_url",
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name="notification",
            name="metadata",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="notification",
            name="dedupe_key",
            field=models.CharField(blank=True, db_index=True, max_length=200, null=True, unique=True),
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["notification_type", "created_at"], name="notification_type_date_idx"),
        ),
    ]
