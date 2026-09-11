import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0002_initial"),
        ("subscriptions", "0003_subscriptionplan_scope"),
    ]

    operations = [
        migrations.AddField(
            model_name="paymentorder",
            name="subscription_plan",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="payment_orders",
                to="subscriptions.subscriptionplan",
            ),
        ),
        migrations.AlterField(
            model_name="paymentorder",
            name="resource_type",
            field=models.CharField(
                choices=[
                    ("course", "Course"),
                    ("track", "Track"),
                    ("subscription", "All-access subscription"),
                    ("exam", "Exam (legacy)"),
                ],
                db_index=True,
                max_length=20,
            ),
        ),
    ]
