from django.db import models


class Organization(models.Model):
    TYPE_SCHOOL = "school"
    TYPE_COLLEGE = "college"
    TYPE_INSTITUTE = "institute"
    TYPE_COMPANY = "company"

    ORG_TYPE_CHOICES = (
        (TYPE_SCHOOL, "School"),
        (TYPE_COLLEGE, "College"),
        (TYPE_INSTITUTE, "Training Institute"),
        (TYPE_COMPANY, "Company"),
    )

    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    org_type = models.CharField(max_length=20, choices=ORG_TYPE_CHOICES)

    logo = models.ImageField(upload_to="org/logos/", blank=True, null=True)
    primary_color = models.CharField(max_length=20, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
