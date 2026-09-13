from django.db import migrations


def move_primary_categories_to_categories(apps, schema_editor):
    """Preserve legacy exam primary categories in the unified category set."""
    Exam = apps.get_model("quiz", "Exam")

    for exam in Exam.objects.exclude(primary_category_id__isnull=True).iterator():
        exam.categories.add(exam.primary_category_id)


class Migration(migrations.Migration):

    dependencies = [
        ("quiz", "0013_remove_exam_subscription_plans"),
    ]

    operations = [
        migrations.RunPython(move_primary_categories_to_categories, migrations.RunPython.noop),
        migrations.RemoveIndex(
            model_name="exam",
            name="exam_primary_cat_idx",
        ),
        migrations.RemoveField(
            model_name="exam",
            name="primary_category",
        ),
    ]
