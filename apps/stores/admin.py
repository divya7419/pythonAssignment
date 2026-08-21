from django.contrib import admin

from .models import Inventory, Store


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "location")
    search_fields = ("name", "location")


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ("id", "store", "product", "quantity")
    list_filter = ("store",)
    search_fields = ("product__title",)
