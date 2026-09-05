from django.db import migrations, models
import django.db.models.deletion


ACADEMIC_DOMAIN_SLUGS = {
    "mbbs-entrance",
    "ioe-entrance",
    "class-11-entrance",
    "mba-entrance",
}


GOVERNMENT_DOMAIN_SLUGS = {
    "government",
    "government-exams",
    "government-exam",
}


def classify_existing_domains(apps, schema_editor):
    Domain = apps.get_model("quiz", "Domain")
    ContentVertical = apps.get_model("quiz", "ContentVertical")

    academic = ContentVertical.objects.filter(
        vertical_type="academic_exam",
    ).first()
    government = ContentVertical.objects.filter(
        vertical_type="government_exam",
    ).first()
    professional = ContentVertical.objects.filter(
        vertical_type="professional_certification",
    ).first()

    if academic:
        Domain.objects.filter(
            organization__isnull=True,
            slug__in=ACADEMIC_DOMAIN_SLUGS,
        ).update(content_vertical_id=academic.pk)

    if government:
        Domain.objects.filter(
            organization__isnull=True,
            slug__in=GOVERNMENT_DOMAIN_SLUGS,
        ).update(content_vertical_id=government.pk)

    if professional:
        Domain.objects.filter(
            organization__isnull=True,
            content_vertical__isnull=True,
        ).update(content_vertical_id=professional.pk)


def unclassify_domains(apps, schema_editor):
    Domain = apps.get_model("quiz", "Domain")
    Domain.objects.update(content_vertical_id=None)


class Migration(migrations.Migration):
    dependencies = [
        ("quiz", "0006_preparationprogram"),
    ]

    operations = [
        migrations.AddField(
            model_name="domain",
            name="content_vertical",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="domains",
                to="quiz.contentvertical",
            ),
        ),
        migrations.RunPython(classify_existing_domains, unclassify_domains),
    ]
