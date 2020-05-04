from .base import Integrator
from scheduling.models import Event
from scheduling import FLAGS
from django.utils.timezone import datetime, timedelta, timezone, is_aware, make_aware
from dateutil.parser import parse as parse_time
from pytimeparse import parse as parse_duration
from hashlib import sha1
import json
import re
import requests
import logging

API_ROOT = "https://api.todoist.com/sync/v8/"


class Todoist(Integrator):
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
                    return [project["name"]] + self._project_names(project["parent_id"])
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

            # Find duration
            duration_matches = re.finditer(r"\[(?P<duration>.+)\]", item["content"])
            for match in duration_matches:
                duration = parse_duration(match.group("duration"))
                if duration is not None:
                    event.duration = duration

            # Find flags
            event.flags = " ".join(
                [
                    self._label_name(label)
                    for label in item["labels"]
                    if self._label_name(label) in FLAGS
                ]
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
            event.content = item["content"]
            self._apply_source_metadata(event, item)
            events.append(event)
        return events
