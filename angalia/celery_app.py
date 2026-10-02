from .tasks import celery_app  # re‑export the Celery instance

__all__ = ["celery_app"]
