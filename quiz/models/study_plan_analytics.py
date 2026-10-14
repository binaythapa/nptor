from django.db import models


class StudyPlanAnalyticsSnapshot(models.Model):
    """
    Daily analytics snapshot for a StudyPlan.
    """

    plan = models.ForeignKey(
        "StudyPlan",
        on_delete=models.CASCADE,
        related_name="snapshots",
    )

    date = models.DateField(
        auto_now_add=True,
    )

    accuracy = models.FloatField()

    readiness = models.FloatField()

    mastery = models.FloatField()

    predicted_score = models.FloatField()

    pass_probability = models.FloatField()

    volatility = models.FloatField()

    xp = models.PositiveIntegerField()

    level = models.PositiveIntegerField()

    class Meta:
        ordering = ["date"]

    def __str__(self):
        return (
            f"{self.plan_id} - "
            f"{self.date}"
        )