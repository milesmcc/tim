from celery import shared_task
from .models import Block, Schedule, Event
from integrations.models import Integration
from .scheduler import build_schedule
from datetime import datetime, timedelta
from integrations.integrators.base import Integrator
from .utils import find_availability
import logging


@shared_task
def update_schedule(schedule_pk: str):
    logging.debug(f"Loading schedule {schedule_pk}...")

    schedule: Schedule = Schedule.objects.get(pk=schedule_pk)

    logging.debug(f"Found schedule. Connecting integrations...")
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

    # Load blocks from integrations
    logging.debug("Loading blocks from integrations...")
    blocks = []
    for integrator in integrators:
        logging.debug(f"Synchonizing blocks from {type(integrator)}...")
        blocks.extend(integrator.get_blocks())
    logging.debug(f"Loaded {len(blocks)} blocks from integrations.")

    # Figure out the time period to schedule
    start, end = schedule.get_current_scheduling_block()
    logging.debug(f"Will build schedule between {start} and {end}...")
    
    # Build schedule
    logging.debug("Building schedule...")
    scheduling_results: [Event] = build_schedule(schedule, blocks, start, end)
    for event in scheduling_results:
        event.save()
    logging.debug("New schedule built and saved!")