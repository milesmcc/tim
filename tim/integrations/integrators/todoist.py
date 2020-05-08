import json
import logging
import re
from hashlib import sha1

import requests
from dateutil.parser import parse as parse_time
from django.utils.timezone import datetime, is_aware, make_aware, timedelta, timezone
from pytimeparse import parse as parse_duration

from scheduling import FLAGS
from scheduling.models import Event

from .base import Integrator

API_ROOT = "https://api.todoist.com/sync/v8/"


class TodoistIntegrator(Integrator):
    def __init__(self, configuration: dict, authentication: dict):
        logging.debug("Todoist integration connecting...")
        self.token = authentication["token"]
        self.state = requests.get(
            API_ROOT + "sync", params={"token": self.token, "resource_types": '["all"]'}
        ).json()
        self.completed = requests.get(
            API_ROOT + "completed/get_all", params={"token": self.token}
        ).json()["items"]
        logging.debug(
            f"Todoist integration loaded state with {len(self.state['items'])} pending items and {len(self.completed)} completed items."
        )

    def _timezone(self) -> timezone:
        return timezone(timedelta(hours=int(self.state["user"]["tz_info"]["hours"])))

    def _label_id(self, name: str) -> int:
        for label in self.state["labels"]:
            if label["name"].lower() == name.lower():
                return label["id"]

    def _label_name(self, id: int) -> str:
        for label in self.state["labels"]:
            if label["id"] == id:
                return label["name"]

    def _project_names(self, id: int) -> [str]:
        # Returns the names of the project and its parents
        for project in self.state["projects"]:
            if project["id"] == id:
                if project["parent_id"] is not None:
                    return self._project_names(project["parent_id"]) + [project["name"]]
                else:
                    return [project["name"]]

    def _apply_source_metadata(self, event: Event, item: dict):
        event.source = "todoist"
        id_data = sha1()
        id_data.update(str(item.get("task_id", item.get("id"))).encode("utf-8"))
        if event.recurrence_id != "":
            id_data.update(str(event.deadline or event.inception).encode("utf-8"))
        event.source_id = id_data.hexdigest()
        event.source_url = f"https://todoist.com/showTask?id={item['id']}"
        event.source_metadata = json.dumps(item)

    def get_pending_events(self, until: datetime = None) -> [Event]:
        events = []
        for item in self.state["items"]:
            event = Event()

            # Get name
            event.content = re.sub(r"\[.+\]\s?", "", item["content"]).strip()
            project_names = self._project_names(item["project_id"])
            if len(project_names) > 0:
                event.content = project_names[-1] + " / " + event.content

            # Find & load times
            event.inception = parse_time(item["date_added"])
            due_date = None
            if item["due"] is not None:
                # If there is a due date, it's treated as the do-after date (inception time)
                # UNLESS it has the 'deadline' label, in which case it's considered the
                # deadline.

                due_date = parse_time(item["due"]["date"])
                if not is_aware(due_date):
                    due_date = make_aware(due_date, timezone=self._timezone())

                if item["due"]["is_recurring"]:
                    event.recurrence_id = str(item["id"])

                if self._label_id("deadline") in item["labels"]:
                    event.deadline = due_date
                else:
                    event.inception = due_date

            # Extract Tim-specific metadata
            metadata_matches = re.finditer(r"\[(?P<metadata>.+)\]", item["content"])
            for match in metadata_matches:
                for component in match.group("metadata").split(","):
                    if match := re.match(
                        r"(?P<progression>([\w\-])+)(\s+)?#(?P<ordering>\d+(.\d+)?)",
                        component.strip(),
                    ):
                        event.progression = match.group("progression")
                        event.progression_order = float(match.group("ordering"))
                    if (duration := parse_duration(component)):
                        event.duration = duration

            # Find flags
            event.flags = " ".join(
                [
                    self._label_name(label)
                    for label in item["labels"]
                    if self._label_name(label) in FLAGS
                ]
                + [f"p{5 - item['priority']}"]
            )

            # Find contexts
            event.contexts = " ".join(
                [
                    self._label_name(label)
                    for label in item["labels"]
                    if self._label_name(label) not in FLAGS
                ]
                + self._project_names(item["project_id"])
            )

            # Add source metadata
            self._apply_source_metadata(event, item)

            events.append(event)
        return events

    def get_completed_events(self, after: datetime = None):
        events = []
        for item in self.completed:
            event = Event()
            event.completed = True
            self._apply_source_metadata(event, item)
            events.append(event)
        return events
