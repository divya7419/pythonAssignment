from django.urls import path

from .views import AutocompleteView, ProductSearchView

app_name = "search"

urlpatterns = [
    path("products/", ProductSearchView.as_view(), name="product-search"),
    path("suggest/", AutocompleteView.as_view(), name="autocomplete"),
]
