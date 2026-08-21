from django.urls import path

from apps.orders.views import StoreOrderListView

from .views import StoreInventoryListView

app_name = "stores"

urlpatterns = [
    path("<int:store_id>/inventory/", StoreInventoryListView.as_view(), name="store-inventory"),
    path("<int:store_id>/orders/", StoreOrderListView.as_view(), name="store-orders"),
]
