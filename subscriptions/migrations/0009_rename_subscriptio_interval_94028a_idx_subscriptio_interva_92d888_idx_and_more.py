from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("subscriptions", "0008_rename_subs_plan_interval_active_idx_subscriptio_interval_94028a_idx"),
    ]

    operations = [
        migrations.RenameIndex(
            model_name="subscriptionplan",
            new_name="subscriptio_interva_92d888_idx",
            old_name="subscriptio_interval_94028a_idx",
        ),
        migrations.AlterField(
            model_name="subscriptionplan",
            name="duration_days",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Legacy duration in days. NULL means lifetime for legacy plans.",
                null=True,
            ),
        ),
    ]
