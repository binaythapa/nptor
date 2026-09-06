from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cv", "0009_ai_suggestions"),
    ]

    operations = [
        migrations.AddField(
            model_name="atsanalysis",
            name="job_description",
            field=models.TextField(blank=True),
        ),
    ]
