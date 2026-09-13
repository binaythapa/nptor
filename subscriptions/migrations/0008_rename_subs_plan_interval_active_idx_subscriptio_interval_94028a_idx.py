from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("subscriptions", "0007_merge_20260914_0150"),
    ]

    operations = [
        migrations.RenameIndex(
            model_name="subscriptionplan",
            new_name="subscriptio_interval_94028a_idx",
            old_name="subs_plan_interval_active_idx",
        ),
    ]
