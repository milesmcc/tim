from .todoist import Todoist
from .base import IntegrationError

def load_integration(name: str, configuration: dict, authentication: dict):
    if name == "todoist":
        return Todoist(configuration, authentication)
    raise IntegrationError(f"unknown integration '{name}'")