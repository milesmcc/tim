from django.db import models
from django.utils.timezone import datetime
from accounts.models import User
import uuid

def _default_uuid():
    return uuid.uuid4()


class Schedule(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # Rescheduling behavior
    RESCHEDULING_CHOICES = [
        ("CONSISTENCY", "Optimize for consistency"),
        ("EFFICIENCY", "Optimize for efficiency"),
    ]
    rescheduling_behavior = models.TextField(
        choices=RESCHEDULING_CHOICES, default="EFFICIENCY"
    )
    default_timezone = models.TextField(default="America/New_York")

    def __str__(self):
        return f"{self.user} (#{self.pk})"


class Event(models.Model):
    # Identity metadata & internal tracking
    uuid = models.UUIDField(primary_key=True, default=_default_uuid)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    scheduled = models.DateTimeField(null=True, blank=True)

    # Core information (provided by source)
    content = models.TextField(blank=True, default="")
    inception = models.DateTimeField(null=True, blank=True)
    deadline = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(null=True, blank=True) # seconds
    completed = models.BooleanField(default=False)
    flags = models.TextField(blank=True)
    contexts = models.TextField(blank=True)

    # Source identity data
    source = models.TextField()
    source_id = models.TextField(db_index=True)
    source_url = models.URLField(blank=True)
    recurrence_id = models.TextField(blank=True)
    source_metadata = models.TextField(default="{}")

    def __str__(self):
        return f"{str(self.uuid)[:6]}: {self.content}"

    class Meta:
        unique_together = [("schedule", "source_id")]

    def update_from(self, other):
        update_fields = [
            "content",
            "inception",
            "deadline",
            "duration",
            "completed",
            "flags",
            "contexts",
        ]

        for field in update_fields:
            if getattr(self, field) != getattr(other, field) and getattr(
                other, field
            ) != getattr(Event(), field):
                # If the field on the other event is different and isn't the default,
                # update self.
                setattr(self, field, getattr(other, field))


class Block:  # Not stored in database
    start: datetime = None
    end: datetime = None

    def __init__(self, start: datetime, end: datetime):
        self.start = start
        self.end = end
