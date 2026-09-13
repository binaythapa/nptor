from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("quiz", "0012_paymentrecord_commerce_targets"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="exam",
            name="subscription_plans",
        ),
    ]
