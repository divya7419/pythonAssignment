import random

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.products.models import Category, Product
from apps.search.cache import bump_search_cache_version
from apps.stores.models import Inventory, Store

try:
    from faker import Faker
except ImportError:  # pragma: no cover
    Faker = None

CATEGORY_NAMES = [
    "Groceries",
    "Electronics",
    "Home & Kitchen",
    "Beauty & Personal Care",
    "Sports & Outdoors",
    "Toys & Games",
    "Books & Stationery",
    "Health & Wellness",
    "Automotive",
    "Pet Supplies",
    "Clothing & Apparel",
    "Footwear",
]

MIN_CATEGORIES = 10
MIN_PRODUCTS = 1000
MIN_STORES = 20
MIN_INVENTORY_PER_STORE = 300


class Command(BaseCommand):
    help = (
        "Seed the database with dummy categories, products, stores, and "
        "per-store inventory for local development and demos."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing Category/Product/Store/Inventory rows first.",
        )

    def handle(self, *args, **options):
        if Faker is None:
            self.stderr.write(
                self.style.ERROR("Faker is not installed. Run: pip install Faker")
            )
            return

        fake = Faker()
        Faker.seed(42)
        random.seed(42)

        if options["flush"]:
            self.stdout.write("Flushing existing Category/Product/Store/Inventory data...")
            Inventory.objects.all().delete()
            Product.objects.all().delete()
            Store.objects.all().delete()
            Category.objects.all().delete()

        with transaction.atomic():
            categories = self._seed_categories()
            products = self._seed_products(fake, categories)
            stores = self._seed_stores(fake)
            self._seed_inventory(stores, products)

        # bulk_create/bulk_update above skip signals; bump explicitly so
        # a warm cache from a prior run doesn't mask the new seed data.
        bump_search_cache_version()

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(categories)} categories, {len(products)} products, "
                f"{len(stores)} stores, inventory for each store."
            )
        )

    def _seed_categories(self):
        existing = {c.name: c for c in Category.objects.all()}
        names = list(dict.fromkeys(CATEGORY_NAMES))
        while len(names) < MIN_CATEGORIES:
            names.append(f"Category {len(names) + 1}")

        to_create = [Category(name=name) for name in names if name not in existing]
        Category.objects.bulk_create(to_create, ignore_conflicts=True)
        return list(Category.objects.all())

    def _seed_products(self, fake, categories):
        existing_count = Product.objects.count()
        to_add = max(0, MIN_PRODUCTS - existing_count)
        batch = []
        for _ in range(to_add):
            batch.append(
                Product(
                    title=fake.unique.catch_phrase(),
                    description=fake.sentence(nb_words=12),
                    price=round(random.uniform(2.5, 999.99), 2),
                    category=random.choice(categories),
                )
            )
        Product.objects.bulk_create(batch, batch_size=500)
        fake.unique.clear()
        return list(Product.objects.all())

    def _seed_stores(self, fake):
        existing_count = Store.objects.count()
        to_add = max(0, MIN_STORES - existing_count)
        batch = [
            Store(name=f"{fake.city()} Store", location=fake.address().replace("\n", ", "))
            for _ in range(to_add)
        ]
        Store.objects.bulk_create(batch)
        return list(Store.objects.all())

    def _seed_inventory(self, stores, products):
        existing_pairs = set(
            Inventory.objects.values_list("store_id", "product_id")
        )
        rows = []
        for store in stores:
            already = sum(1 for s_id, _ in existing_pairs if s_id == store.id)
            needed = max(0, MIN_INVENTORY_PER_STORE - already)
            if needed == 0:
                continue
            sample_size = min(needed, len(products))
            for product in random.sample(products, sample_size):
                if (store.id, product.id) in existing_pairs:
                    continue
                rows.append(
                    Inventory(
                        store=store,
                        product=product,
                        quantity=random.randint(0, 500),
                    )
                )
                existing_pairs.add((store.id, product.id))
        Inventory.objects.bulk_create(rows, batch_size=1000, ignore_conflicts=True)
