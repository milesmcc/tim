import logging

import requests
from dateutil.parser import parse as parse_time
from django.utils.timezone import (datetime, is_aware, make_aware, timedelta,
                                   timezone)
from ics import Calendar, Event, parse
from pytimeparse import parse as parse_duration

from scheduling.models import Block

from .base import Integrator


def _is_busy(event: Event):
    return not (event.status == "CANCELLED" or event.transparent)


class IcsIntegrator(Integrator):
    def __init__(self, configuration: dict, authentication: dict):
        self.url = configuration["url"]
        self.calendar = Calendar(requests.get(self.url).text)

    def get_blocks(self, after: datetime = None, until: datetime = None):
        return [
            Block(event.begin.datetime, event.end.datetime)
            for event in self.calendar.events
            if _is_busy(event)
            and (until is None or event.begin.datetime < until)
            and (after is None or event.end.datetime > after)
        ]
