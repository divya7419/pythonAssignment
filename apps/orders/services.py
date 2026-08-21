import logging
from collections import defaultdict

from django.db import transaction
from django.shortcuts import get_object_or_404

from apps.search.cache import bump_search_cache_version
from apps.stores.models import Inventory, Store

from .models import Order, OrderItem

logger = logging.getLogger(__name__)


def create_order(store_id, items):
    """Evaluate and persist an order atomically.

    `items` is a list of {"product_id": int, "quantity_requested": int}.
    All-or-nothing: if every product has enough stock at the store, all
    quantities are deducted and the order is CONFIRMED; otherwise nothing
    is deducted and the order is REJECTED. Inventory rows are locked with
    select_for_update (ordered by product_id to avoid deadlocks) so
    concurrent orders against the same store/product can't over-sell.
    """
    store = get_object_or_404(Store, pk=store_id)

    requested_totals = defaultdict(int)
    for item in items:
        requested_totals[item["product_id"]] += item["quantity_requested"]
    product_ids = sorted(requested_totals)

    with transaction.atomic():
        inventory_by_product = {
            inv.product_id: inv
            for inv in Inventory.objects.select_for_update()
            .filter(store=store, product_id__in=product_ids)
            .order_by("product_id")
        }

        sufficient = all(
            inventory_by_product.get(pid) is not None
            and inventory_by_product[pid].quantity >= qty
            for pid, qty in requested_totals.items()
        )

        order = Order.objects.create(
            store=store,
            status=Order.Status.CONFIRMED if sufficient else Order.Status.REJECTED,
        )
        OrderItem.objects.bulk_create(
            OrderItem(
                order=order,
                product_id=item["product_id"],
                quantity_requested=item["quantity_requested"],
            )
            for item in items
        )

        if sufficient:
            for pid, qty in requested_totals.items():
                inventory_by_product[pid].quantity -= qty
            # bulk_update() does not fire post_save signals, so the
            # products/stores signal-based invalidation never sees this
            # write — bump the search cache explicitly.
            Inventory.objects.bulk_update(
                [inventory_by_product[pid] for pid in requested_totals], ["quantity"]
            )
            bump_search_cache_version()

        if sufficient:
            transaction.on_commit(lambda: _dispatch_confirmation(order.pk))

    return order


def _dispatch_confirmation(order_id):
    # The order is already committed by the time this runs. A broker
    # hiccup here must not surface as a request failure for an order that
    # was, in fact, successfully confirmed — so swallow and log instead.
    from .tasks import send_order_confirmation

    try:
        send_order_confirmation.delay(order_id)
    except Exception:
        logger.exception(
            "Failed to enqueue send_order_confirmation for order %s", order_id
        )
