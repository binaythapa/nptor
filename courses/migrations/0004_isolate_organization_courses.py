from django.db import migrations


def isolate_organization_courses(apps, schema_editor):
    Course = apps.get_model("courses", "Course")
    Course.objects.filter(organization__isnull=False).update(is_public=False)
    Course.objects.filter(owner_type="organization").update(is_public=False)


def reverse_isolation(apps, schema_editor):
    # Intentionally do not restore public visibility for tenant-owned content.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0003_courseexam"),
    ]

    operations = [
        migrations.RunPython(isolate_organization_courses, reverse_isolation),
    ]
