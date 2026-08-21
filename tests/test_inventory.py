from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .base import make_category, make_inventory, make_product, make_store


class InventoryListingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = make_category()
        self.store = make_store()

    def test_inventory_listing_sorted_alphabetically_by_product_title(self):
        titles = ["Zebra Mug", "Apple Case", "Mango Stand"]
        for title in titles:
            product = make_product(self.category, title=title, price="1.00")
            make_inventory(self.store, product, quantity=5)

        url = reverse("stores:store-inventory", kwargs={"store_id": self.store.id})
        response = self.client.get(url)

        returned_titles = [row["product_title"] for row in response.data["results"]]
        self.assertEqual(returned_titles, sorted(titles))


class SearchCacheInvalidationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        cache.clear()
        self.category = make_category()
        self.store = make_store()
        self.product = make_product(self.category, title="Gadget", price="1.00")
        make_inventory(self.store, self.product, quantity=5)

    def test_product_write_invalidates_cached_search_results(self):
        url = reverse("search:product-search")
        first = self.client.get(url, {"q": "Gadget"})
        self.assertEqual(len(first.data["results"]), 1)

        self.product.title = "Renamed Item"
        self.product.save()

        second = self.client.get(url, {"q": "Gadget"})
        self.assertEqual(len(second.data["results"]), 0)
