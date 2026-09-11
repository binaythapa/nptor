from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0002_initial"),
        ("quiz", "0010_exam_created_by"),
    ]

    operations = [
        migrations.AddField(
            model_name="examtrack",
            name="courses",
            field=models.ManyToManyField(
                blank=True,
                help_text="Courses included in this track.",
                related_name="exam_tracks",
                to="courses.course",
            ),
        ),
    ]
