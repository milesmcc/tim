from __future__ import absolute_import, unicode_literals

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tim.settings')

app = Celery('tim')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

app.conf.beat_schedule = {
    "update-schedules": {
        "task": "scheduling.tasks.update_all_schedules",
        "schedule": crontab(minute='*/5'),
    },
}
