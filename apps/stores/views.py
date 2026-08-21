from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView

from .models import Inventory, Store
from .serializers import InventoryListSerializer


class StoreInventoryListView(ListAPIView):
    """GET /stores/<store_id>/inventory/ — sorted alphabetically by product title."""

    serializer_class = InventoryListSerializer
    queryset = Inventory.objects.none()

    def get_queryset(self):
        store_id = self.kwargs.get("store_id")
        if store_id is None:  # schema generation introspection, no real request
            return Inventory.objects.none()
        store = get_object_or_404(Store, pk=store_id)
        return (
            Inventory.objects.filter(store=store)
            .select_related("product", "product__category")
            .order_by("product__title")
        )
