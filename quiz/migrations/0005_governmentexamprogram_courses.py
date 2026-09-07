from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0002_initial"),
        ("quiz", "0003_government_exam_catalog"),
    ]

    operations = [
        migrations.AddField(
            model_name="governmentexamprogram",
            name="courses",
            field=models.ManyToManyField(
                blank=True,
                related_name="government_exam_programs",
                to="courses.course",
            ),
        ),
    ]
