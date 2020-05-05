from datetime import timedelta, datetime, time
from django.utils import timezone
from .utils import find_availability
from .models import Event, Schedule, Block
from statistics import mean
from django.db.models import Q

import logging


def _viable_at(schedule: Schedule, start: datetime, end: datetime, event: Event):
    if event.has_flag("nobox"):
        return False
    if event.inception is not None and event.inception > start:
        return False
    if event.get_duration() is not None and event.get_duration() > (end - start):
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
    if earliest != [] and latest != []:
        t = start.astimezone(tz=schedule.get_timezone()).time()
        if t < min(earliest) or t > max(latest):
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
    events: [Event] = sorted(
        Event.objects.filter(
            Q(schedule=schedule, completed=False)
            & (Q(inception=None) | Q(inception__lt=end))
        ),
        key=lambda k: _priority_at(schedule, end, k),
        reverse=True,
    )
    for event in events:
        if event.scheduled is not None and event.scheduled <= timezone.now():
            expected_end = event.scheduled
            if event.get_duration() is not None:
                expected_end += event.get_duration()
            if (
                expected_end + timedelta(minutes=schedule.reschedule_after)
                > timezone.now()
            ):
                logging.debug(f"Not rescheduling {event.content}, currently ongoing...")
                events.remove(event)
                blocks.append(Block(event.scheduled, expected_end))

    scheduled: [Event] = []
    unschedulable: [Event] = []

    while len(events) > 0:
        availability = find_availability(start, end, blocks)
        event = events.pop(0)
        best_time = None
        highest_suitability = None
        for block_start, block_end in availability:
            while block_start < block_end:
                if _viable_at(schedule, block_start, end, event):
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
                blocks.append(Block(best_time, best_time + event.get_duration()))
            scheduled.append(event)
        else:
            logging.debug(f"Unable to find a good time for {event}...")
            event.scheduled = None
            unschedulable.append(event)

    return scheduled + unschedulable
