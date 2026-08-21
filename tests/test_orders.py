from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.orders.models import Order
from apps.stores.models import Inventory

from .base import make_category, make_inventory, make_product, make_store


class OrderCreationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = make_category()
        self.store = make_store()
        self.product = make_product(self.category, title="Keyboard", price="49.99")
        self.inventory = make_inventory(self.store, self.product, quantity=10)

    def test_sufficient_stock_confirms_order_and_deducts_quantity(self):
        response = self.client.post(
            reverse("orders:order-create"),
            {
                "store_id": self.store.id,
                "items": [
                    {"product_id": self.product.id, "quantity_requested": 3}
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], Order.Status.CONFIRMED)

        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 7)

    def test_insufficient_stock_rejects_order_without_deducting(self):
        response = self.client.post(
            reverse("orders:order-create"),
            {
                "store_id": self.store.id,
                "items": [
                    {"product_id": self.product.id, "quantity_requested": 999}
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], Order.Status.REJECTED)

        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 10)

    def test_one_short_item_rejects_whole_order_no_partial_deduction(self):
        other_product = make_product(self.category, title="Mouse", price="19.99")
        make_inventory(self.store, other_product, quantity=5)

        response = self.client.post(
            reverse("orders:order-create"),
            {
                "store_id": self.store.id,
                "items": [
                    {"product_id": self.product.id, "quantity_requested": 2},
                    {"product_id": other_product.id, "quantity_requested": 999},
                ],
            },
            format="json",
        )

        self.assertEqual(response.data["status"], Order.Status.REJECTED)

        # Neither item's stock should be touched — all-or-nothing.
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 10)
        other_inventory = Inventory.objects.get(store=self.store, product=other_product)
        self.assertEqual(other_inventory.quantity, 5)


class OrderListingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = make_category()
        self.store = make_store()

    def test_listing_sorted_newest_first_with_item_counts_and_no_n_plus_1(self):
        for i in range(3):
            product = make_product(self.category, title=f"Product {i}", price="5.00")
            make_inventory(self.store, product, quantity=100)
            self.client.post(
                reverse("orders:order-create"),
                {
                    "store_id": self.store.id,
                    "items": [{"product_id": product.id, "quantity_requested": 1}],
                },
                format="json",
            )

        url = reverse("stores:store-orders", kwargs={"store_id": self.store.id})
        with self.assertNumQueries(2):  # COUNT + annotated SELECT, no per-order query
            response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        results = response.data["results"]
        self.assertEqual(len(results), 3)
        # Newest first.
        created_ats = [r["created_at"] for r in results]
        self.assertEqual(created_ats, sorted(created_ats, reverse=True))
        for row in results:
            self.assertEqual(row["total_items"], 1)
