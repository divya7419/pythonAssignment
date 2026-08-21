from django.db import models

from apps.products.models import Product


class Store(models.Model):
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Inventory(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="inventory")
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="inventory_rows"
    )
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "inventory"
        constraints = [
            models.UniqueConstraint(
                fields=["store", "product"], name="unique_inventory_per_store_product"
            )
        ]
        indexes = [models.Index(fields=["store", "product"])]

    def __str__(self):
        return f"{self.store} / {self.product} = {self.quantity}"
