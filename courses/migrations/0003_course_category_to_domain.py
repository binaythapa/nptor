from django.db import migrations, models
import django.db.models.deletion


def copy_categories_to_legacy_column(apps, schema_editor):
    Course = apps.get_model("courses", "Course")
    Course.objects.update(legacy_category_id=models.F("category_id"))


def restore_categories_from_legacy_column(apps, schema_editor):
    Course = apps.get_model("courses", "Course")
    Course.objects.update(category_id=models.F("legacy_category_id"))


def migrate_categories_to_domains(apps, schema_editor):
    Course = apps.get_model("courses", "Course")
    Category = apps.get_model("quiz", "Category")

    category_domains = dict(
        Category.objects.exclude(domain_id=None).values_list("id", "domain_id")
    )

    for course in Course.objects.exclude(legacy_category_id=None).only(
        "id", "legacy_category_id"
    ):
        Course.objects.filter(pk=course.pk).update(
            category_id=category_domains.get(course.legacy_category_id)
        )


def clear_domain_values_before_reverse(apps, schema_editor):
    Course = apps.get_model("courses", "Course")
    Course.objects.update(category_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0002_initial"),
        ("quiz", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="course",
            name="legacy_category_id",
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.RunPython(
            copy_categories_to_legacy_column,
            reverse_code=restore_categories_from_legacy_column,
        ),
        migrations.RemoveField(
            model_name="course",
            name="category",
        ),
        migrations.AddField(
            model_name="course",
            name="category",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="courses",
                to="quiz.domain",
                help_text="The broad subject/domain covered by this course.",
            ),
        ),
        migrations.RunPython(
            migrate_categories_to_domains,
            reverse_code=clear_domain_values_before_reverse,
        ),
        migrations.RemoveField(
            model_name="course",
            name="legacy_category_id",
        ),
    ]
