from scheduling.models import Event
from datetime import datetime

class IntegrationError(Exception):
    pass

class Integrator:
    def __init__(self, configuration: dict, authentication: dict):
        pass

    def get_todos(self, until: datetime=None) -> [Event]:
        return []

    def get_completed(self, after: datetime=None) -> [Event]:
        return []

    def write_events(self, events: [Event]):
        pass
