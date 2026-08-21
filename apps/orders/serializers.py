from rest_framework import serializers

from apps.products.models import Product

from .models import Order, OrderItem


class OrderItemInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity_requested = serializers.IntegerField(min_value=1)

    def validate_product_id(self, value):
        if not Product.objects.filter(pk=value).exists():
            raise serializers.ValidationError(f"Product {value} does not exist.")
        return value


class OrderCreateSerializer(serializers.Serializer):
    store_id = serializers.IntegerField()
    items = OrderItemInputSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one item is required.")
        return value


class OrderItemOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["product", "quantity_requested"]


class OrderDetailSerializer(serializers.ModelSerializer):
    items = OrderItemOutputSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ["id", "store", "status", "created_at", "items"]


class OrderListSerializer(serializers.ModelSerializer):
    total_items = serializers.IntegerField(read_only=True)

    class Meta:
        model = Order
        fields = ["id", "status", "created_at", "total_items"]
