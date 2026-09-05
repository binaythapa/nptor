from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0002_initial"),
        ("quiz", "0005_governmentexamprogram_courses"),
    ]

    operations = [
        migrations.CreateModel(
            name="PreparationProgram",
            fields=[
                (
                    "id",
                    models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
                ),
                ("name", models.CharField(max_length=255)),
                ("code", models.SlugField(max_length=140)),
                ("slug", models.SlugField(max_length=140, unique=True)),
                ("description", models.TextField(blank=True)),
                ("official_website", models.URLField(blank=True)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("is_published", models.BooleanField(db_index=True, default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "content_vertical",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="preparation_programs",
                        to="quiz.contentvertical",
                    ),
                ),
                (
                    "country",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="preparation_programs",
                        to="quiz.country",
                    ),
                ),
                (
                    "courses",
                    models.ManyToManyField(
                        blank=True,
                        related_name="preparation_programs",
                        to="courses.course",
                    ),
                ),
                (
                    "exams",
                    models.ManyToManyField(
                        blank=True,
                        related_name="preparation_programs",
                        to="quiz.exam",
                    ),
                ),
            ],
            options={
                "ordering": ["name"],
                "indexes": [
                    models.Index(fields=["content_vertical", "is_active"], name="prep_prog_vert_act_idx"),
                    models.Index(fields=["country", "is_active"], name="prep_prog_country_idx"),
                    models.Index(fields=["is_published", "is_active"], name="prep_prog_pub_act_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("content_vertical", "code"),
                        name="uniq_prep_program_vertical_code",
                    ),
                ],
            },
        ),
    ]
