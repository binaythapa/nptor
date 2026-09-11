from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0002_align_current_models"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscriptionplan",
            name="scope",
            field=models.CharField(
                choices=[
                    ("resource", "Resource"),
                    ("all_access", "All Access"),
                ],
                db_index=True,
                default="resource",
                help_text="Resource plans are attached to courses/tracks; all-access plans unlock the whole platform.",
                max_length=20,
            ),
        ),
        migrations.AddIndex(
            model_name="subscriptionplan",
            index=models.Index(
                fields=["scope", "is_active"],
                name="sub_plan_scope_active_idx",
            ),
        ),
    ]
