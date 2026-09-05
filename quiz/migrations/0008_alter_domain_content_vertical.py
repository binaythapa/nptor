from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("quiz", "0007_domain_content_vertical"),
    ]

    operations = [
        migrations.AlterField(
            model_name="domain",
            name="content_vertical",
            field=models.ForeignKey(
                blank=True,
                help_text="Top-level catalog vertical for this platform domain.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="domains",
                to="quiz.contentvertical",
            ),
        ),
    ]
