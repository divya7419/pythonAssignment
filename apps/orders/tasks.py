import logging

from celery import shared_task
from django.core.mail import send_mail

from .models import Order

logger = logging.getLogger(__name__)


@shared_task
def send_order_confirmation(order_id: int) -> None:
    try:
        order = Order.objects.select_related("store").get(pk=order_id)
    except Order.DoesNotExist:
        logger.warning("send_order_confirmation: order %s no longer exists", order_id)
        return

    send_mail(
        subject=f"Order #{order.id} confirmed",
        message=f"Order #{order.id} at {order.store.name} has been confirmed.",
        from_email=None,
        recipient_list=[f"store-{order.store_id}@aforro.example"],
        fail_silently=False,
    )
