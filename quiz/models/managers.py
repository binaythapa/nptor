from django.db import models


class QuestionQuerySet(models.QuerySet):

    def active(self):
        return self.filter(
            is_active=True,
            is_deleted=False
        )