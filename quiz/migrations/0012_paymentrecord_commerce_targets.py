import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("quiz", "0011_examtrack_courses"),
        ("courses", "0002_initial"),
        ("subscriptions", "0003_subscriptionplan_scope"),
    ]

    operations = [
        migrations.AddField(
            model_name="paymentrecord",
            name="course",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="payment_records",
                to="courses.course",
            ),
        ),
        migrations.AddField(
            model_name="paymentrecord",
            name="subscription_plan",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="payment_records",
                to="subscriptions.subscriptionplan",
            ),
        ),
    ]
