from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("quiz", "0008_alter_domain_content_vertical"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="learningshortlist",
            name="uniq_shortlist_user_course",
        ),
        migrations.RemoveConstraint(
            model_name="learningshortlist",
            name="uniq_shortlist_user_track",
        ),
        migrations.RemoveConstraint(
            model_name="learningshortlist",
            name="uniq_shortlist_user_exam",
        ),
        migrations.RemoveConstraint(
            model_name="userexam",
            name="one_active_attempt_per_exam",
        ),
    ]
