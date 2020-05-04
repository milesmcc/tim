from django.db import models

from scheduling.models import Schedule
from . import integrators
import json


class Integration(models.Model):
    SERVICE_CHOICES = (("todoist", "Todoist"), ("gcal", "Google Calendar"))

    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    service = models.TextField(choices=SERVICE_CHOICES)
    configuration = models.TextField()
    authentication = models.TextField()
