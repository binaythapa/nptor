from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("quiz", "0012_paymentrecord_commerce_targets"),
        ("subscriptions", "0006_subscriptionplan_billing_interval"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="examtrack",
            name="courses",
        ),
        migrations.AlterField(
            model_name="exam",
            name="subscription_plans",
            field=models.ManyToManyField(
                blank=True,
                help_text="Legacy exam-plan relationship. Exams are not independently sellable.",
                related_name="exams",
                to="subscriptions.subscriptionplan",
            ),
        ),
        migrations.AlterField(
            model_name="examtrack",
            name="subscription_plans",
            field=models.ManyToManyField(
                blank=True,
                help_text="Track product plans available for this track. Exams are not sold through this relationship.",
                related_name="exam_tracks",
                to="subscriptions.subscriptionplan",
            ),
        ),
        migrations.AlterField(
            model_name="examtrack",
            name="subscription_scope",
            field=models.CharField(
                choices=[("track", "Track"), ("exam", "Exam (Legacy)")],
                default="track",
                max_length=10,
            ),
        ),
    ]
