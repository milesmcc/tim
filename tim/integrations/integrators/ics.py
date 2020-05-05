from .base import Integrator
from scheduling.models import Block
from ics import Calendar, Event, parse
from django.utils.timezone import datetime, timedelta, timezone, is_aware, make_aware
from dateutil.parser import parse as parse_time
from pytimeparse import parse as parse_duration
import requests
import logging


def _is_busy(event: Event):
    return not (event.status == "CANCELLED" or event.transparent)


class IcsIntegrator(Integrator):
    def __init__(self, configuration: dict, authentication: dict):
        self.url = configuration["url"]
        self.calendar = Calendar(requests.get(self.url).text)

    def get_blocks(self):
        return [
            Block(event.begin.datetime, event.end.datetime)
            for event in self.calendar.events
            if _is_busy(event)
        ]

