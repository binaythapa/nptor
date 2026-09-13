from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("subscriptions", "0004_subscriptionplan_product_model"),
        ("courses", "0003_courseexam"),
        ("quiz", "0012_paymentrecord_commerce_targets"),
    ]

    operations = [
        migrations.CreateModel(
            name="AccountSubscriptionSelection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("course", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="account_subscription_selections", to="courses.course")),
                ("subscription", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="account_selections", to="subscriptions.subscription")),
                ("track", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="account_subscription_selections", to="quiz.examtrack")),
            ],
            options={
                "ordering": ["id"],
                "indexes": [
                    models.Index(fields=["subscription", "course"], name="acct_sel_sub_course_idx"),
                    models.Index(fields=["subscription", "track"], name="acct_sel_sub_track_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(fields=["subscription", "course"], name="unique_account_subscription_course"),
                    models.UniqueConstraint(fields=["subscription", "track"], name="unique_account_subscription_track"),
                ],
            },
        ),
    ]
