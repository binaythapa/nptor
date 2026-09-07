from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("subscriptions", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="subscriptionentitlement",
            name="unique_sub_course_entitlement",
        ),
        migrations.RemoveConstraint(
            model_name="subscriptionentitlement",
            name="unique_sub_track_entitlement",
        ),
        migrations.RemoveConstraint(
            model_name="subscriptionentitlement",
            name="unique_sub_exam_entitlement",
        ),
    ]
