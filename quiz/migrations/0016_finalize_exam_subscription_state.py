from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("quiz", "0015_merge_20260914_0150"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RemoveField(
                    model_name="exam",
                    name="subscription_plans",
                ),
            ],
        ),
    ]
