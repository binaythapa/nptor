from django.db import models


# =====================================================
# DOMAIN (Snowflake, Power BI, Tableau)
# =====================================================

class Domain(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="domains",
        null=True,
        blank=True,
        help_text="Organization that owns this domain",
    )

    content_vertical = models.ForeignKey(
        "quiz.ContentVertical",
        on_delete=models.SET_NULL,
        related_name="domains",
        null=True,
        blank=True,
        help_text="Top-level catalog vertical for this platform domain.",
    )

    name = models.CharField(max_length=50)

    slug = models.SlugField(
        max_length=100,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("organization", "slug")
        ordering = ["name"]

    def __str__(self):
        return self.name


# =====================================================
# CATEGORY (Hierarchical Question Classification)
# =====================================================

class Category(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="categories",
        null=True,
        blank=True,
    )

    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name="categories",
        null=True,
        blank=True,
    )

    name = models.CharField(
        max_length=200,
        default="Unknown",
    )

    slug = models.SlugField(
        max_length=150,
    )

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="children",
        on_delete=models.CASCADE,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("organization", "slug")
        ordering = ["name"]

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} → {self.name}"

        return self.name

    # -------------------------------------------------
    # Helpers
    # -------------------------------------------------

    def get_descendants_include_self(self):
        """
        Return this category ID together with all descendant IDs.
        """

        ids = [self.id]

        for child in self.children.all():
            ids.extend(child.get_descendants_include_self())

        return ids

    @property
    def is_root(self):
        return self.parent_id is None

    @property
    def has_children(self):
        return self.children.exists()

    def get_ancestors(self):
        """
        Returns ancestors ordered from root -> parent.
        """

        ancestors = []
        node = self.parent

        while node:
            ancestors.insert(0, node)
            node = node.parent

        return ancestors

    def full_path(self):
        """
        Example:
        Azure -> Data Factory -> Copy Activity
        """

        ancestors = self.get_ancestors()

        names = [c.name for c in ancestors]
        names.append(self.name)

        return " → ".join(names)
