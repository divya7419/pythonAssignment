from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.search.cache import bump_search_cache_version

from .models import Inventory


@receiver(post_save, sender=Inventory)
@receiver(post_delete, sender=Inventory)
def invalidate_search_cache_on_inventory_change(sender, **kwargs):
    bump_search_cache_version()
