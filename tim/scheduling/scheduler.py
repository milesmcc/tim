import logging
from datetime import datetime, time, timedelta
from statistics import mean

from django.db.models import Q
from django.utils import timezone

from .models import Block, Event, Schedule
from .utils import find_availability

def _requested_time(event: Event) -> (time, time, bool):
    earliest = []
    latest = []
    if event.has_flag("morning"):
        earliest.append(time(hour=7))
        latest.append(time(hour=12))
    if event.has_flag("afternoon"):
        earliest.append(time(hour=12))
        latest.append(time(hour=17))
    if event.has_flag("evening"):
        earliest.append(time(hour=17))
        latest.append(time(hour=22))
    if event.has_flag("daytime"):
        earliest.append(time(hour=7))
        latest.append(time(hour=17))
    if len(earliest) == 0 or len(latest) == 0:
        return None
    return (min(earliest), max(latest), event.has_flag("flex"))


def _viable_at(schedule: Schedule, start: datetime, end: datetime, event: Event):
    if event.has_flag("nobox"):
        return False
    if event.inception is not None and event.inception > start:
        return False
    if event.get_duration() is not None and start + event.get_duration() > end:
        return False
    requested_time = _requested_time(event)
    if requested_time is not None:
        earliest, latest, flex = requested_time
        if not flex:
            t = start.astimezone(tz=schedule.get_timezone()).time()
            if t < earliest or t > latest:
                return False
    return True


def _priority_at(schedule: Schedule, start: datetime, event: Event) -> float:
    # Find base priority
    priority = 1.0
    if event.has_flag("p1"):
        priority = 4.0
    elif event.has_flag("p2"):
        priority = 3.0
    elif event.has_flag("p3"):
        priority = 2.0
    elif event.has_flag("p4"):
        priority = 1.0
    elif event.has_flag("minor"):
        priority = 0.0

    # Give old tasks higher weight, up to 1 point
    if event.inception is not None:
        priority += min((start - event.inception).days, 28) / 28.0

    # Multiply the task's priority by a deadline coefficient,
    # starting at 1 and steadily increasing as the deadline approaches
    if event.deadline is not None:
        priority *= max(1, ((event.deadline - start).days + 14) / 7.0)

    logging.debug(f"Priority for event {event} on {start} is {priority}.")

    return priority


def _suitability_at(
    schedule: Schedule, start: datetime, also_scheduled: [Event], event: Event
):
    factors = [0]

    # Time suitability
    requested_time = _requested_time(event)
    if requested_time is not None:
        earliest, latest, _ = requested_time
        t = start.astimezone(tz=schedule.get_timezone()).time()
        if t < earliest or t > latest:
            factors.append(-10)
        else:
            factors.append(10)

    # Context suitability
    scheduled_before = list(
        filter(
            lambda k: k.scheduled < start,
            sorted(also_scheduled, key=lambda k: k.scheduled),
        )
    )
    if len(scheduled_before) > 0:
        prior = scheduled_before[-1]
        factors.append(len(prior.get_contexts() & event.get_contexts()))

    # Prior time suitability
    if schedule.rescheduling_behavior == "CONSISTENCY" and event.scheduled is not None:
        factors.append(max(0, 12 - 6 * abs((event.scheduled - start).hours)))

    return mean(factors)


def build_schedule(
    schedule: Schedule, blocks: [Block], start: datetime, end: datetime
) -> [Event]:
    # Builds a hypothetical schedule. Returns modified Event objects.
    # Save them to commit to the schedule.
    for event in Event.objects.filter(  # Currently ongoing
        Q(schedule=schedule, completed=False, scheduled__lte=start)
    ):
        if event.is_ongoing():
            blocks.extend(event.get_blocks())

    events: [Event] = sorted(
        Event.objects.filter(
            Q(schedule=schedule, completed=False)
            & (Q(inception=None) | Q(inception__lt=end))
            & (Q(scheduled=None) | Q(scheduled__gte=start))
        ),
        key=lambda k: _priority_at(schedule, end, k),
        reverse=True,
    )

    scheduled: [Event] = []
    unschedulable: [Event] = []

    while len(events) > 0:
        availability = find_availability(start, end, blocks)
        event = events.pop(0)
        best_time = None
        highest_suitability = None
        for block_start, block_end in availability:
            while block_start < block_end:
                if _viable_at(schedule, block_start, block_end, event):
                    suitability = _suitability_at(
                        schedule, block_start, scheduled, event
                    )
                    if highest_suitability is None or suitability > highest_suitability:
                        highest_suitability = suitability
                        best_time = block_start
                block_start += timedelta(minutes=1)
        if best_time is not None:
            logging.debug(f"Scheduled event {event} for {best_time}.")
            event.scheduled = best_time
            if event.get_duration() is not None:
                blocks.extend(event.get_blocks())
            scheduled.append(event)
        else:
            logging.debug(f"Unable to find a good time for {event}...")
            event.scheduled = None
            unschedulable.append(event)

    return scheduled + unschedulable
