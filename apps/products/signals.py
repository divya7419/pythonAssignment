from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.search.cache import bump_search_cache_version

from .models import Product


@receiver(post_save, sender=Product)
@receiver(post_delete, sender=Product)
def invalidate_search_cache_on_product_change(sender, **kwargs):
    bump_search_cache_version()
