from apps.products.models import Category, Product
from apps.stores.models import Inventory, Store


def make_category(name="Electronics"):
    return Category.objects.create(name=name)


def make_product(category, title="Widget", price="9.99", description=""):
    return Product.objects.create(
        title=title, price=price, category=category, description=description
    )


def make_store(name="Downtown Store", location="123 Main St"):
    return Store.objects.create(name=name, location=location)


def make_inventory(store, product, quantity):
    return Inventory.objects.create(store=store, product=product, quantity=quantity)
