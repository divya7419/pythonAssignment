from django.db.models import Count
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Order
from .serializers import OrderCreateSerializer, OrderDetailSerializer, OrderListSerializer
from .services import create_order


class OrderCreateView(APIView):
    """POST /orders/ — atomic all-or-nothing order creation."""

    @extend_schema(
        request=OrderCreateSerializer,
        responses={201: OrderDetailSerializer},
        description=(
            "Creates an order for a store. If every requested item has "
            "sufficient stock, all quantities are deducted and the order "
            "is CONFIRMED; otherwise nothing is deducted and the order is "
            "REJECTED. Always returns 201 — the outcome is in `status`."
        ),
    )
    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = create_order(
            store_id=serializer.validated_data["store_id"],
            items=serializer.validated_data["items"],
        )
        return Response(
            OrderDetailSerializer(order).data, status=status.HTTP_201_CREATED
        )


class StoreOrderListView(ListAPIView):
    """GET /stores/<store_id>/orders/ — newest first, N+1-free."""

    serializer_class = OrderListSerializer
    queryset = Order.objects.none()

    def get_queryset(self):
        store_id = self.kwargs.get("store_id")
        if store_id is None:  # schema generation introspection, no real request
            return Order.objects.none()
        return (
            Order.objects.filter(store_id=store_id)
            .annotate(total_items=Count("items"))
            .order_by("-created_at")
        )
