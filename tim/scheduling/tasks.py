from celery import shared_task
from .models import Block, Schedule, Event
from integrations.models import Integration
from .scheduler import build_schedule
from datetime import datetime, timedelta
from django.utils.timezone import now
from integrations.integrators.base import Integrator
from .utils import find_availability
import logging

@shared_task
def update_all_schedules():
    for schedule in Schedule.objects.all():
        update_schedule.delay(schedule.pk)

@shared_task
def update_schedule(schedule_pk: str):
    logging.debug(f"Loading schedule {schedule_pk}...")

    schedule: Schedule = Schedule.objects.get(pk=schedule_pk)

    # Figure out the time period to schedule
    schedule_block = schedule.get_current_scheduling_block()
    if schedule_block is None:
        logging.debug("No active scheduling block!")
        return
    else:
        start, end = schedule_block
    logging.debug(f"Found schedule. Will build schedule between {start} and {end}...")

    logging.debug(f"Connecting integrations...")
    integrators: [Integrator] = [
        integration.connect()
        for integration in Integration.objects.filter(schedule=schedule)
    ]
    logging.debug("Connected to all integrations!")

    logging.debug(f"Loading events from integrations...")
    incoming_events = []
    for integrator in integrators:
        logging.debug(f"Synchonizing events from {type(integrator)}...")
        incoming_events.extend(integrator.get_pending_events())
        incoming_events.extend(integrator.get_completed_events())
    logging.debug(
        f"Loaded {len(incoming_events)} events from integrations. Synchronizing..."
    )
    schedule.process_integration_events(incoming_events)
    logging.debug("Synchronized events!")

    logging.debug("Bumping overdue events...")
    schedule.clear_overdue_events()
    logging.debug("Overdue events bumped!")

    logging.debug("Clearing scheduled times of future completed events...")
    schedule.clear_future_completed_events()
    logging.debug("Future completed events cleared!")

    logging.debug("Unscheduling postponed events...")
    schedule.unschedule_postponed_events()
    logging.debug("Postponed events unscheduled!")

    # Load blocks from integrations
    logging.debug("Loading blocks from integrations...")
    blocks = []
    for integrator in integrators:
        logging.debug(f"Synchonizing blocks from {type(integrator)}...")
        blocks.extend(integrator.get_blocks())
    logging.debug(f"Loaded {len(blocks)} blocks from integrations.")

    # Build schedule
    logging.debug("Building schedule...")
    scheduling_results: [Event] = build_schedule(schedule, blocks, start, end)
    for event in scheduling_results:
        event.save()
    logging.debug("New schedule built and saved!")

    # Publish schedule
    logging.debug("Publishing schedule...")
    events = list(schedule.event_set.filter(updated__gt=now() - timedelta(weeks=1)))
    for integrator in integrators:
        # Write all events that have recent changes. There's a week of buffer to
        # deal with rescheduled old events, moved things, and other... potential
        # problems.
        logging.debug(f"Publishing schedule to {type(integrator)}...")
        integrator.write_events(events)
    logging.debug("Schedule published to all integrations!")
