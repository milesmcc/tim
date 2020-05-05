from scheduling.models import Event, Block
from django.utils.timezone import datetime, timedelta

class IntegrationError(Exception):
    pass

class Integrator:
    def __init__(self, configuration: dict, authentication: dict):
        pass

    def get_pending_events(self, until: datetime=None) -> [Event]:
        return []

    def get_completed_events(self, after: datetime=None) -> [Event]:
        return []

    def get_blocks(self, after: datetime=None, until: datetime=None) -> [Block]:
        return []

    def write_events(self, events: [Event]):
        pass
