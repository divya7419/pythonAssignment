from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .base import make_category, make_inventory, make_product, make_store


class ProductSearchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.electronics = make_category("Electronics")
        self.books = make_category("Books")
        self.cheap = make_product(
            self.electronics, title="Wireless Mouse", price="15.00"
        )
        self.expensive = make_product(
            self.electronics, title="Wireless Keyboard", price="85.00"
        )
        self.unrelated = make_product(self.books, title="Novel", price="10.00")
        self.store = make_store()
        make_inventory(self.store, self.cheap, quantity=0)
        make_inventory(self.store, self.expensive, quantity=20)

    def test_keyword_and_category_and_price_filters_narrow_results(self):
        url = reverse("search:product-search")
        response = self.client.get(
            url, {"q": "wireless", "category": "Electronics", "price_max": "50"}
        )
        self.assertEqual(response.status_code, 200)
        titles = [item["title"] for item in response.data["results"]]
        self.assertEqual(titles, ["Wireless Mouse"])

    def test_in_stock_filter_excludes_zero_quantity_for_store(self):
        url = reverse("search:product-search")
        response = self.client.get(
            url, {"q": "wireless", "store_id": self.store.id, "in_stock": "true"}
        )
        titles = [item["title"] for item in response.data["results"]]
        self.assertEqual(titles, ["Wireless Keyboard"])

    def test_sort_by_price_orders_ascending(self):
        url = reverse("search:product-search")
        response = self.client.get(url, {"q": "wireless", "sort": "price"})
        prices = [item["price"] for item in response.data["results"]]
        self.assertEqual(prices, sorted(prices))

    def test_store_id_attaches_per_store_quantity(self):
        url = reverse("search:product-search")
        response = self.client.get(
            url, {"q": "Wireless Keyboard", "store_id": self.store.id}
        )
        self.assertEqual(response.data["results"][0]["store_quantity"], 20)


class AutocompleteTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        category = make_category()
        make_product(category, title="Proactive Widget", price="1.00")
        make_product(category, title="Reactive Widget", price="1.00")
        make_product(category, title="Proton Charger", price="1.00")

    def test_query_shorter_than_three_chars_returns_empty(self):
        url = reverse("search:autocomplete")
        response = self.client.get(url, {"q": "pr"})
        self.assertEqual(response.data["results"], [])

    def test_prefix_matches_ranked_before_contains_matches(self):
        url = reverse("search:autocomplete")
        response = self.client.get(url, {"q": "Pro"})
        results = response.data["results"]
        # Both "Proactive Widget" and "Proton Charger" start with "Pro";
        # "Reactive Widget" only contains it and must rank after both.
        self.assertIn("Proactive Widget", results[:2])
        self.assertIn("Proton Charger", results[:2])
        self.assertNotIn("Reactive Widget", results)
