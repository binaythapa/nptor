from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("quiz", "0009_mysql_safe_active_uniqueness"),
    ]

    operations = [
        migrations.AddField(
            model_name="exam",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="exams_created",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
