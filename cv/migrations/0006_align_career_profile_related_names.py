from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cv", "0005_document_artifact"),
    ]

    operations = [
        migrations.AlterField(
            model_name="careerachievement",
            name="profile",
            field=models.ForeignKey(
                on_delete=__import__("django.db.models.deletion", fromlist=["CASCADE"]).CASCADE,
                related_name="careerachievement_records",
                to="cv.careerprofile",
            ),
        ),
        migrations.AlterField(
            model_name="careercertification",
            name="profile",
            field=models.ForeignKey(
                on_delete=__import__("django.db.models.deletion", fromlist=["CASCADE"]).CASCADE,
                related_name="careercertification_records",
                to="cv.careerprofile",
            ),
        ),
        migrations.AlterField(
            model_name="careereducation",
            name="profile",
            field=models.ForeignKey(
                on_delete=__import__("django.db.models.deletion", fromlist=["CASCADE"]).CASCADE,
                related_name="careereducation_records",
                to="cv.careerprofile",
            ),
        ),
        migrations.AlterField(
            model_name="careerexperience",
            name="profile",
            field=models.ForeignKey(
                on_delete=__import__("django.db.models.deletion", fromlist=["CASCADE"]).CASCADE,
                related_name="careerexperience_records",
                to="cv.careerprofile",
            ),
        ),
        migrations.AlterField(
            model_name="careerproject",
            name="profile",
            field=models.ForeignKey(
                on_delete=__import__("django.db.models.deletion", fromlist=["CASCADE"]).CASCADE,
                related_name="careerproject_records",
                to="cv.careerprofile",
            ),
        ),
        migrations.AlterField(
            model_name="careerskill",
            name="profile",
            field=models.ForeignKey(
                on_delete=__import__("django.db.models.deletion", fromlist=["CASCADE"]).CASCADE,
                related_name="careerskill_records",
                to="cv.careerprofile",
            ),
        ),
    ]
