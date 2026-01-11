# quiz/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Category
from .utils import clear_leaf_category_cache

@receiver(post_save, sender=Category)
def _on_category_save(sender, instance, **kwargs):
    clear_leaf_category_cache()

@receiver(post_delete, sender=Category)
def _on_category_delete(sender, instance, **kwargs):
    clear_leaf_category_cache()


