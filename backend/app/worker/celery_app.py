import os

from celery import Celery
from celery.schedules import crontab

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

app = Celery(
    "viral_clip_studio",
    broker=redis_url,
    backend=redis_url,
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "scrape-periodic": {
            "task": "app.worker.tasks.scrape_and_score",
            "schedule": 60.0,
        },
        "check-scheduled-posts": {
            "task": "app.worker.tasks.check_scheduled_posts",
            "schedule": 60.0,
        },
    },
)

app.autodiscover_tasks(["app.worker"])
