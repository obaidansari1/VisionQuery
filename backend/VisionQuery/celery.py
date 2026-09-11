import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "VisionQuery.settings")

app = Celery("VisionQuery")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
