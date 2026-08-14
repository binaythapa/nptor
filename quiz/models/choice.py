from django.db import models


class Choice(models.Model):

    question = models.ForeignKey(
        "Question",
        on_delete=models.CASCADE,
        related_name="choices",
    )

    text = models.CharField(
        max_length=500,
    )

    is_correct = models.BooleanField(
        default=False,
    )

    order = models.IntegerField(
        default=0,
    )

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.text