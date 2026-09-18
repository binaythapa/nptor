from django.db import migrations, models
import django.db.models.deletion


def migrate_course_categories_to_domains(apps, schema_editor):
    Course = apps.get_model("courses", "Course")
    Category = apps.get_model("quiz", "Category")

    category_domains = dict(
        Category.objects.exclude(domain_id=None).values_list("id", "domain_id")
    )

    for course in Course.objects.exclude(category_id=None).only("id", "category_id"):
        domain_id = category_domains.get(course.category_id)
        Course.objects.filter(pk=course.pk).update(category_id=domain_id)


def reverse_domains_to_categories(apps, schema_editor):
    # A Domain cannot be reliably converted back to a single Category because
    # a domain may contain multiple categories. Clear the relationship on reverse.
    Course = apps.get_model("courses", "Course")
    Course.objects.update(category_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0002_initial"),
        ("quiz", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            migrate_course_categories_to_domains,
            reverse_code=reverse_domains_to_categories,
        ),
        migrations.AlterField(
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
    ]
