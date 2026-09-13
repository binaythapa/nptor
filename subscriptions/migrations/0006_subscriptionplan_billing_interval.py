from django.db import migrations, models


def populate_billing_intervals(apps, schema_editor):
    SubscriptionPlan = apps.get_model("subscriptions", "SubscriptionPlan")

    common_mappings = {
        7: ("week", 1),
        30: ("month", 1),
        90: ("month", 3),
        180: ("month", 6),
        365: ("year", 1),
    }

    for plan in SubscriptionPlan.objects.all().iterator():
        if plan.duration_days is None:
            plan.interval_unit = "lifetime"
            plan.interval_count = None
        elif plan.duration_days in common_mappings:
            plan.interval_unit, plan.interval_count = common_mappings[plan.duration_days]
        else:
            plan.interval_unit = "day"
            plan.interval_count = plan.duration_days
        plan.save(update_fields=["interval_unit", "interval_count"])


def reverse_billing_intervals(apps, schema_editor):
    SubscriptionPlan = apps.get_model("subscriptions", "SubscriptionPlan")

    for plan in SubscriptionPlan.objects.all().iterator():
        if plan.interval_unit == "lifetime":
            duration_days = None
        elif plan.interval_unit == "day":
            duration_days = plan.interval_count
        elif plan.interval_unit == "week":
            duration_days = plan.interval_count * 7
        elif plan.interval_unit == "month":
            # Reverse migration cannot exactly represent calendar months in
            # the legacy day-only field. Preserve the conventional 30-day
            # approximation for compatibility.
            duration_days = plan.interval_count * 30
        elif plan.interval_unit == "year":
            duration_days = plan.interval_count * 365
        else:
            duration_days = plan.duration_days
        plan.duration_days = duration_days
        plan.save(update_fields=["duration_days"])


class Migration(migrations.Migration):
    dependencies = [
        ("subscriptions", "0005_accountsubscriptionselection"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscriptionplan",
            name="interval_unit",
            field=models.CharField(
                blank=True,
                choices=[
                    ("day", "Day"),
                    ("week", "Week"),
                    ("month", "Month"),
                    ("year", "Year"),
                    ("lifetime", "Lifetime"),
                ],
                db_index=True,
                help_text="Billing interval unit. Use Lifetime for one-time lifetime access.",
                max_length=10,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="subscriptionplan",
            name="interval_count",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Number of interval units in one billing period. Not used for Lifetime.",
                null=True,
            ),
        ),
        migrations.RunPython(populate_billing_intervals, reverse_billing_intervals),
        migrations.AddIndex(
            model_name="subscriptionplan",
            index=models.Index(fields=["interval_unit", "is_active"], name="subs_plan_interval_active_idx"),
        ),
    ]
