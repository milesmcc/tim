import logging
import uuid
from datetime import time
from functools import lru_cache

from django.conf import settings
from django.db import models
from django.shortcuts import reverse
from django.utils.timezone import datetime, now, timedelta
from pytz import timezone

from accounts.models import User


def _default_uuid():
    return uuid.uuid4()


class Block:  # Not stored in database
    start: datetime = None
    end: datetime = None

    def __init__(self, start: datetime, end: datetime, buffer: timedelta = None):
        if buffer is None:
            buffer = timedelta()

        self.start = start - buffer
        self.end = end + buffer

    def __str__(self):
        return f"{self.start.isoformat()} - {self.end.isoformat()}"

    def contains(self, time: datetime) -> bool:
        return time >= self.start and time <= self.end

    def overlaps(self, start: datetime, end: datetime) -> bool:
        return not (self.start >= end or self.end <= start)


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
    days_of_week = models.TextField(default="1 2 3 4 5 6 7")
    reschedule_after = models.IntegerField(default=1800)
    shift_after_early_completion = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user} (#{self.pk})"

    def get_reschedule_delay(self) -> timedelta:
        return timedelta(seconds=self.reschedule_after)

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

        if not str(start.isoweekday()) in self.days_of_week.split():
            return None

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

    def clear_conflicting_events(self, blocks: [Block]):
        events = self.event_set.filter(completed=False, scheduled__isnull=False)
        for event in events:
            start = event.scheduled
            end = start + (event.get_duration() or timedelta())
            for block in blocks:
                if block.overlaps(start, end):
                    logging.debug(f"Event {event} overlaps with block, rescheduling...")
                    event.scheduled = None
                    event.save()
                    break

    def clear_overdue_events(self):
        overdue_candidates = self.event_set.filter(
            scheduled__lte=now(), completed=False
        )
        for candidate in overdue_candidates:
            if candidate.is_overdue():
                logging.debug(f"Event {candidate} is overdue, bumping off old time...")
                candidate.scheduled = None
                candidate.save()

    def unschedule_postponed_events(self):
        for event in self.event_set.filter(
            completed=False, scheduled__isnull=False, inception__isnull=False
        ):
            if event.scheduled < event.inception:
                logging.debug(
                    f"Event {event} was scheduled before its inception, bumping off old time..."
                )
                event.scheduled = None
                event.save()

    def clear_future_completed_events(self):
        self.event_set.filter(scheduled__gt=now(), completed=True).update(
            scheduled=None
        )


class Event(models.Model):
    # Identity metadata & internal tracking
    uuid = models.UUIDField(primary_key=True, default=_default_uuid)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    scheduled = models.DateTimeField(null=True, blank=True)

    # Core information (provided by source)
    content = models.TextField(blank=True, default="", db_index=True)
    inception = models.DateTimeField(null=True, blank=True, db_index=True)
    deadline = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(null=True, blank=True)  # seconds
    completed = models.BooleanField(default=False, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    flags = models.TextField(blank=True, default="")
    contexts = models.TextField(blank=True, default="")
    progression = models.TextField(blank=True, default="", db_index=True)
    progression_order = models.FloatField(blank=True, default=0.0, db_index=True)

    # Source identity data
    source = models.TextField()
    source_id = models.TextField(db_index=True)
    source_url = models.URLField(blank=True)
    recurrence_id = models.TextField(blank=True)
    source_metadata = models.TextField(default="{}")

    class Meta:
        ordering = ["-scheduled"]
        unique_together = [("schedule", "source_id")]
        indexes = [
            models.Index(fields=["schedule", "-scheduled"]),
            models.Index(fields=["schedule", "-inception"]),
        ]

    def __str__(self):
        return f"{str(self.uuid)[:6]}: {self.content}"

    @lru_cache
    def get_dependencies(self, incomplete_only=True):
        if len(self.progression.strip()) == 0:
            return []
        query = models.Q(
            progression=self.progression, progression_order__lt=self.progression_order
        )
        if incomplete_only:
            query = query & models.Q(completed=False)
        return list(self.schedule.event_set.filter(query))

    @lru_cache
    def get_dependents(self, incomplete_only=True):
        if len(self.progression.strip()) == 0:
            return []
        query = models.Q(
            progression=self.progression, progression_order__gt=self.progression_order
        )
        if incomplete_only:
            query = query & models.Q(completed=False)
        return list(self.schedule.event_set.filter(query))

    def get_duration(self) -> timedelta:
        if self.duration is None:
            return None
        duration = timedelta(seconds=self.duration)
        if (
            self.completed
            and self.scheduled is not None
            and self.completed_at is not None
        ):
            if self.scheduled + duration > self.completed_at:
                # Event was completed early; return shorter duration
                return self.completed_at - self.scheduled
        return duration

    def get_flags(self) -> [str]:
        return set(self.flags.lower().split())

    def has_flag(self, flag: str) -> bool:
        return flag.lower() in self.get_flags()

    def get_contexts(self) -> [str]:
        return set(self.contexts.lower().split())

    def get_blocks(self) -> [Block]:
        if self.duration is None or self.duration == 0 or self.scheduled is None:
            return []
        return [Block(self.scheduled, self.scheduled + self.get_duration())]

    def is_overdue(self) -> bool:
        if self.scheduled is None:
            return False
        expected_end = self.scheduled
        if self.get_duration() is not None:
            expected_end += self.get_duration()
        return expected_end + timedelta(seconds=self.schedule.reschedule_after) < now()

    def is_ongoing(self) -> bool:
        if self.scheduled is not None:
            return now() > self.scheduled and not self.completed
        return False

    def get_description(self) -> str:
        desc = (
            f"🔗 {self.source_url}\n\n"
            + f"🚩 {', '.join(self.get_flags())}\n\n"
            + f"🗂️ {', '.join(self.get_contexts())}\n\n"
        )

        if self.is_ongoing():
            reschedule_after = self.schedule.get_timezone().normalize(
                (
                    self.scheduled
                    + self.get_duration()
                    + self.schedule.get_reschedule_delay()
                )
            )
            desc += f"⏳ This event is currently ongoing. It will not be rescheduled unless it remains incomplete at {reschedule_after.strftime('%-I:%M %p')}.\n\n"

        if self.completed:
            desc += f"✅ This event is complete. These links may expire.\n\n"

        if len(progression := self.progression) != 0:
            desc += f"📑 This event is part of the '{progression}' progression, with {len(self.get_dependencies())} dependencies and {len(self.get_dependents())} dependents.\n\n"

        if self.schedule.user.is_superuser:
            desc += f"📡 {settings.URL_PREFIX}{reverse('admin:scheduling_event_change', kwargs={'object_id': self.pk})}\n\n"

        return desc.strip()

    def get_status_string(self) -> str:
        string = ""
        if self.completed:
            string += "✅"
        if self.is_ongoing():
            string += "⏳"
        if self.has_flag("deadline"):
            string += "⏰"
        if self.has_flag("p1"):
            string += "🔴"
        if self.has_flag("p2"):
            string += "🟠"
        if self.has_flag("p3"):
            string += "🟢"
        if self.has_flag("minor"):
            string += "🤷"
        if self.get_dependencies():
            string += "🚧"
        if self.get_dependents(incomplete_only=False):
            string += "🛡️"
        return string

    def update_from(self, other):
        update_fields = [
            "content",
            "inception",
            "deadline",
            "duration",
            "completed",
            "completed_at",
            "flags",
            "contexts",
            "progression",
            "progression_order",
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
