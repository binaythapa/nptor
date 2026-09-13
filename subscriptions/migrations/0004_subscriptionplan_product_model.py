from django.db import migrations, models
from django.core.validators import MinValueValidator


def populate_product_model(apps, schema_editor):
    SubscriptionPlan = apps.get_model("subscriptions", "SubscriptionPlan")
    for plan in SubscriptionPlan.objects.all().iterator():
        if plan.scope == "all_access":
            plan.product_type = "account"
            plan.access_mode = "all_access"
            plan.save(update_fields=["product_type", "access_mode"])
            continue

        has_courses = plan.course_access_courses.exists()
        has_tracks = plan.exam_tracks.exists()
        if has_courses and has_tracks:
            raise RuntimeError(
                "Subscription plan %s is attached to both Courses and Tracks. "
                "Split the plan before applying product isolation migration." % plan.pk
            )
        plan.product_type = "track" if has_tracks else "course"
        plan.access_mode = "single_resource"
        plan.save(update_fields=["product_type", "access_mode"])


def reverse_product_model(apps, schema_editor):
    SubscriptionPlan = apps.get_model("subscriptions", "SubscriptionPlan")
    SubscriptionPlan.objects.filter(product_type="account").update(scope="all_access")
    SubscriptionPlan.objects.exclude(product_type="account").update(scope="resource")


class Migration(migrations.Migration):
    dependencies = [
        ("subscriptions", "0003_subscriptionplan_scope"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscriptionplan",
            name="product_type",
            field=models.CharField(
                choices=[("course", "Course"), ("track", "Track"), ("account", "Account")],
                db_index=True,
                default="course",
                help_text="What this plan sells: a Course, Track, or Account.",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="subscriptionplan",
            name="access_mode",
            field=models.CharField(
                choices=[
                    ("single_resource", "Single Resource"),
                    ("limited_access", "Limited Access"),
                    ("all_access", "All Access"),
                ],
                db_index=True,
                default="single_resource",
                help_text="Account plans may be limited by selectable Course/Track quotas or all-access.",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="subscriptionplan",
            name="max_courses",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Maximum Courses selectable for a limited Account plan. NULL means not applicable/unlimited by this field.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="subscriptionplan",
            name="max_tracks",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Maximum Tracks selectable for a limited Account plan. NULL means not applicable/unlimited by this field.",
                null=True,
            ),
        ),
        migrations.RunPython(populate_product_model, reverse_product_model),
        migrations.AddIndex(
            model_name="subscriptionplan",
            index=models.Index(fields=["product_type", "access_mode", "is_active"], name="subs_plan_product_mode_idx"),
        ),
    ]
