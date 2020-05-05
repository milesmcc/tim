from django.db import models
from django.core.exceptions import ValidationError
from scheduling.models import Schedule
from . import integrators
import json


def _validate_json(value):
    try:
        json.loads(value)
    except json.JSONDecodeError:
        raise ValidationError("Value is not valid JSON!")


class Integration(models.Model):
    SERVICE_CHOICES = (
        ("todoist", "Todoist"),
        ("gcal", "Google Calendar"),
        ("ics", "External Calendar"),
    )

    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    service = models.TextField(choices=SERVICE_CHOICES)
    configuration = models.TextField(
        default="{}", help_text="Must be valid JSON!", validators=[_validate_json]
    )
    authentication = models.TextField(
        default="{}", help_text="Must be valid JSON!", validators=[_validate_json]
    )

    def connect(self):
        return integrators.load_integration(
            self.service,
            json.loads(self.configuration),
            json.loads(self.authentication),
        )

    def __str__(self):
        return f"{self.schedule} on {self.get_service_display()}"
