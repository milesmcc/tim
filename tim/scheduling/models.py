from django.db import models

from accounts.models import User

class Schedule(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # Rescheduling behavior
    RESCHEDULING_CHOICES = [
        ("CONSISTENCY", "Optimize for consistency"),
        ("EFFICIENCY", "Optimize for efficiency")
    ]
    rescheduling_behavior = models.TextField(choices=RESCHEDULING_CHOICES, default="EFFICIENCY")


class Event(models.Model):
    # Identity metadata
    uuid = models.UUIDField(primary_key=True)
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)

    # Core information
    inception = models.DateTimeField(null=True)
    scheduled = models.DateTimeField(null=True)
    deadline = models.DateTimeField(null=True)
    duration = models.IntegerField(default=30)
    completed = models.BooleanField(default=False)
    flags = models.TextField(blank=True)
    contexts = models.TextField(blank=True)

    # Source metadata
    source = models.TextField()
    source_id = models.TextField(db_index=True)
    source_url = models.URLField(blank=True)
    recurrence_id = models.TextField(blank=True)
