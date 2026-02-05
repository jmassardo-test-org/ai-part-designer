"""
Celery worker configuration and task definitions.

Provides async task processing for:
- CAD generation
- AI processing
- File conversion
- Analytics event processing
"""

from celery import Celery

from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "ai_part_designer",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.worker.tasks.cad",
        "app.worker.tasks.ai",
        "app.worker.tasks.export",
        "app.worker.tasks.analytics",
        "app.worker.tasks.maintenance",
        "app.worker.tasks.extraction",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Task execution
    task_track_started=True,
    task_time_limit=settings.CAD_WORKER_TIMEOUT,
    task_soft_time_limit=settings.CAD_WORKER_TIMEOUT - 30,
    # Result backend
    result_expires=3600,  # 1 hour
    # Worker settings
    worker_prefetch_multiplier=1,  # Disable prefetch for long-running tasks
    worker_concurrency=settings.MAX_CONCURRENT_JOBS,
    # Rate limiting
    task_default_rate_limit="100/m",
    # Retry settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Task routing
    task_routes={
        "app.worker.tasks.cad.*": {"queue": "cad"},
        "app.worker.tasks.ai.*": {"queue": "ai"},
        "app.worker.tasks.export.*": {"queue": "export"},
        "app.worker.tasks.analytics.*": {"queue": "analytics"},
        "app.worker.tasks.maintenance.*": {"queue": "maintenance"},
    },
    # Queue configuration
    task_queues={
        "cad": {
            "exchange": "cad",
            "routing_key": "cad",
        },
        "ai": {
            "exchange": "ai",
            "routing_key": "ai",
        },
        "export": {
            "exchange": "export",
            "routing_key": "export",
        },
        "analytics": {
            "exchange": "analytics",
            "routing_key": "analytics",
        },
        "maintenance": {
            "exchange": "maintenance",
            "routing_key": "maintenance",
        },
    },
    # Beat schedule for periodic tasks
    beat_schedule={
        "cleanup-old-jobs": {
            "task": "app.worker.tasks.maintenance.cleanup_old_jobs",
            "schedule": 3600.0,  # Every hour
        },
        "process-analytics-events": {
            "task": "app.worker.tasks.analytics.process_pending_events",
            "schedule": 60.0,  # Every minute
        },
        "backup-database": {
            "task": "app.worker.tasks.maintenance.backup_database",
            "schedule": 86400.0,  # Daily
            "options": {"queue": "maintenance"},
        },
        "cleanup-temp-files": {
            "task": "app.worker.tasks.maintenance.cleanup_temp_files",
            "schedule": 3600.0,  # Hourly
        },
        "check-stale-jobs": {
            "task": "app.worker.tasks.maintenance.check_stale_jobs",
            "schedule": 300.0,  # Every 5 minutes
        },
        "purge-expired-trash": {
            "task": "app.worker.tasks.maintenance.purge_expired_trash",
            "schedule": 86400.0,  # Daily
            "options": {"queue": "maintenance"},
        },
        "send-trash-deletion-warnings": {
            "task": "app.worker.tasks.maintenance.send_trash_deletion_warnings",
            "schedule": 86400.0,  # Daily
            "options": {"queue": "maintenance"},
        },
        "check-data-integrity": {
            "task": "app.worker.tasks.maintenance.check_data_integrity",
            "schedule": 604800.0,  # Weekly (7 days)
            "options": {"queue": "maintenance"},
        },
        "verify-backups": {
            "task": "app.worker.tasks.maintenance.verify_backups",
            "schedule": 604800.0,  # Weekly (7 days)
            "options": {"queue": "maintenance"},
        },
    },
)
