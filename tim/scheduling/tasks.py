from celery import shared_task
from .models import Block, Schedule, Event
from integrations.models import Integration
from integrations.integrators.base import Integrator

import logging

@shared_task
def update_schedule(schedule_pk: str):
    print("task running")
    logging.debug(f"Loading schedule {schedule_pk}...")

    schedule: Schedule = Schedule.objects.get(pk=schedule_pk)

    logging.debug(f"Found schedule. Loading known events...")
    events: [Event] = list(Event.objects.filter(schedule=schedule))
    logging.debug(f"Found {len(events)} events. Connecting integrations...")
    integrators: [Integrator] = [
        integration.connect()
        for integration in Integration.objects.filter(schedule=schedule)
    ]
    logging.debug("Connected to all integrations!")

    # Load all events from integrations
    for integrator in integrators:
        for event in (
            integrator.get_pending_events() + integrator.get_completed_events()
        ):
            # Update and/or insert event
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

    # Save events
    for event in events:
        event.schedule = schedule
        event.save()
