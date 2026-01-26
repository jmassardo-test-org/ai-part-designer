"""
Celery worker package.
"""

from app.worker.celery import celery_app

__all__ = ["celery_app"]
