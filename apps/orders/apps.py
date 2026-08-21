from django.apps import AppConfig


class OrdersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.orders"
    label = "orders"

    def ready(self):
        # Importing this here (rather than relying on a project __init__.py,
        # which this flat layout doesn't have) registers celery_app.app as
        # Celery's default app before any @shared_task-decorated task is
        # used, so .delay()/.apply_async() pick up our broker/eager config.
        import celery_app  # noqa: F401
