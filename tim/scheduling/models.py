from django.db import models
from django.utils.timezone import datetime, timedelta, now
from pytz import timezone
from datetime import time
from accounts.models import User
import logging
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
    start_day_at = models.TimeField(default=time(hour=7))
    end_day_at = models.TimeField(default=time(hour=22))
    days_of_week = models.TextField(default="Mon Tue Wed Thu Fri Sat Sun")
    reschedule_after = models.IntegerField(default=1800)

    def __str__(self):
        return f"{self.user} (#{self.pk})"

    def get_timezone(self):
        return timezone(self.default_timezone)

    def get_current_scheduling_block(self) -> (datetime, datetime):
        tz = self.get_timezone()
        rn = tz.normalize(now())
        start = max(rn, tz.localize(datetime.combine(rn.date(), self.start_day_at)))
        end = tz.localize(datetime.combine(rn.date(), self.end_day_at))
        if rn.time() >= self.end_day_at:
            # The end time has passed; time to schedule tomorrow
            start = tz.localize(
                datetime.combine(rn.date(), self.start_day_at)
            ) + timedelta(days=1)
            end = tz.localize(datetime.combine(rn.date(), self.end_day_at)) + timedelta(
                days=1
            )

        return (start, end)

    def process_integration_events(self, incoming_events):
        events = list(self.event_set.all())
        # TODO: only deal with events from the last month or so to keep this small
        for event in incoming_events:
            try:
                existing_index = [event.source_id for event in events].index(
                    event.source_id
                )
                events[existing_index].update_from(event)
            except ValueError:
                events.append(event)

            # Mark older events with the same recurrence id as completed
            if event.recurrence_id != "":
                for old_event in [
                    old_event
                    for old_event in events
                    if old_event.recurrence_id == event.recurrence_id
                    and old_event.source_id != event.source_id
                ]:
                    old_event.completed = True
        for event in events:
            event.schedule = self
            event.save()

    def clear_overdue_events(self):
        overdue_candidates = self.event_set.filter(
            scheduled__lte=now(), completed=False
        )
        for candidate in overdue_candidates:
            if candidate.is_overdue():
                logging.debug(f"Event {candidate} is overdue, bumping off old time...")
                candidate.scheduled = None
                candidate.save()

    def clear_future_completed_events(self):
        self.event_set.filter(
            scheduled__gt=now(), completed=True
        ).update(scheduled=None)


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
    duration = models.IntegerField(null=True, blank=True)  # seconds
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

    def get_duration(self) -> timedelta:
        if self.duration is None:
            return None
        return timedelta(seconds=self.duration)

    def get_flags(self) -> [str]:
        return set(self.flags.lower().split())

    def has_flag(self, flag: str) -> bool:
        return flag.lower() in self.get_flags()

    def get_contexts(self) -> [str]:
        return set(self.contexts.lower().split())

    def is_overdue(self) -> bool:
        if self.scheduled is None:
            return False
        expected_end = self.scheduled
        if self.get_duration() is not None:
            expected_end += self.get_duration()
        return expected_end + timedelta(seconds=self.schedule.reschedule_after) < now()

    def update_from(self, other):
        update_fields = [
            "content",
            "inception",
            "deadline",
            "duration",
            "completed",
            "flags",
            "contexts",
            "source_metadata",
            "recurrence_id",
            "source_url",
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

    def contains(self, time: datetime) -> bool:
        return time >= self.start and time <= self.end

    def overlaps(self, start: datetime, end: datetime) -> bool:
        return not (self.start >= end or self.end <= start)
