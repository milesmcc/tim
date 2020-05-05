from .todoist import TodoistIntegrator
from .ics import IcsIntegrator
from .gcal import GcalIntegrator
from .base import IntegrationError

def load_integration(name: str, configuration: dict, authentication: dict):
    if name == "todoist":
        return TodoistIntegrator(configuration, authentication)
    if name == "ics":
        return IcsIntegrator(configuration, authentication)
    if name == "gcal":
        return GcalIntegrator(configuration, authentication)
    raise IntegrationError(f"unknown integration '{name}'")