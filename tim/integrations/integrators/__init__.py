from .base import IntegrationError
from .gcal import GcalIntegrator
from .ics import IcsIntegrator
from .todoist import TodoistIntegrator


def load_integration(name: str, configuration: dict, authentication: dict):
    if name == "todoist":
        return TodoistIntegrator(configuration, authentication)
    if name == "ics":
        return IcsIntegrator(configuration, authentication)
    if name == "gcal":
        return GcalIntegrator(configuration, authentication)
    raise IntegrationError(f"unknown integration '{name}'")
