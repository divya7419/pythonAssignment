from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.products.models import Product


class ProductSearchResultSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    store_quantity = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "title",
            "description",
            "price",
            "category",
            "category_name",
            "created_at",
            "store_quantity",
        ]

    @extend_schema_field(OpenApiTypes.INT)
    def get_store_quantity(self, obj):
        # Only populated when a store_id filter was supplied to the search
        # endpoint; None means "not requested", distinct from 0 = "no stock".
        return getattr(obj, "store_quantity", None)
