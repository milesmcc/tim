import base64
import logging
import pickle

from dateutil.parser import parse as parse_time
from django.utils.timezone import (datetime, is_aware, make_aware, now,
                                   timedelta, timezone)
from google.auth.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from scheduling.models import Block, Event

from .base import Integrator


def _get(obj, path):
    if obj is None:
        return None
    for route in path.split("."):
        if route not in obj:
            return None
        obj = obj[route]
    return obj


def _event_up_to_date(sup: dict, child: dict) -> bool:
    for key in child.keys():
        c = child.get(key)
        s = sup.get(key)
        if isinstance(c, dict):
            if not _event_up_to_date(s, c):
                return False
            else:
                continue
        try:
            c = datetime.fromisoformat(c)
            s = datetime.fromisoformat(s)
            if (c - s).total_seconds() != 0:
                return False
            else:
                continue
        except ValueError:
            pass
        except TypeError:
            pass
        if c != s:
            return False
    return True


class GcalIntegrator(Integrator):
    def __init__(self, configuration: dict, authentication: dict):
        self.credentials = pickle.loads(base64.b64decode(authentication["token"]))
        self.credentials.refresh(Request())
        self.service = build("calendar", "v3", credentials=self.credentials)
        self.cal_id = None
        self.other_cal_ids = []
        for cal in self.service.calendarList().list().execute()["items"]:
            if cal.get("accessRole") == "owner" and "[TIM]" in cal.get(
                "description", ""
            ):
                self.cal_id = cal.get("id")
            else:
                self.other_cal_ids.append(cal.get("id"))
        if self.cal_id is None:
            logging.error("Unable to find a valid calendar to write to!")
        else:
            logging.debug("Successfully identified Tim calendar!")
        self.events = (
            self.service.events()
            .list(calendarId=self.cal_id, singleEvents=True)
            .execute()["items"]
        )

    def _gcal_event(self, event: Event) -> dict:
        for candidate in self.events:
            if (
                _get(candidate, "extendedProperties.private.sourceId")
                == event.source_id
            ):
                return candidate

    def _gcal_id(self, event: Event) -> str:
        return _get(self._gcal_event(event), "id")

    def _gcal_contents_current(self, event: Event, body: dict):
        remote_event = self._gcal_event(event)
        if remote_event is None:
            return False
        return _event_up_to_date(remote_event, body)

    def get_blocks(self, after: datetime = None, until: datetime = None):
        blocks = []
        if after is None:
            after = now() - timedelta(weeks=1)
            until = now() + timedelta(weeks=1)
        resp = (
            self.service.freebusy()
            .query(
                body={
                    "timeMin": after.isoformat(),
                    "timeMax": until.isoformat(),
                    "items": [{"id": item} for item in self.other_cal_ids],
                }
            )
            .execute()
        )
        for calendar in resp["calendars"].values():
            for block in calendar["busy"]:
                blocks.append(
                    Block(parse_time(block["start"]), parse_time(block["end"]))
                )
        logging.debug(f"Successfully loaded {len(blocks)} busy blocks from calendar.")
        return blocks

    def write_events(self, events: [Event]):
        for event in events:
            existing_id = self._gcal_id(event)

            if event.duration is None or event.duration < 1 or event.scheduled is None:
                if existing_id is not None:
                    logging.debug(
                        f"Deleting previously scheduled event that's now unscheduled ({event})..."
                    )
                    self.service.events().delete(
                        calendarId=self.cal_id, eventId=existing_id
                    ).execute()
                continue

            suffix = ""
            if event.completed:
                suffix += "✅"
            if event.is_ongoing():
                suffix += "⏳"
            if event.has_flag("deadline"):
                suffix += "⏰"
            if event.has_flag("p1"):
                suffix += "🔴"
            if event.has_flag("p2"):
                suffix += "🟠"
            if event.has_flag("p3"):
                suffix += "🟢"
            if event.has_flag("minor"):
                suffix += "🤷"

            body = {
                "start": {"dateTime": event.scheduled.isoformat()},
                "end": {
                    "dateTime": (event.scheduled + event.get_duration()).isoformat()
                },
                "summary": f"{event.content} {suffix}".strip(),
                "extendedProperties": {"private": {"sourceId": event.source_id,}},
                "source": {
                    "title": f"Via {event.source.capitalize()}, scheduled by Tim",
                    "url": event.source_url,
                },
                "description": event.get_description(),
                "transparency": "transparent",
            }

            if existing_id is not None:
                if not self._gcal_contents_current(event, body):
                    logging.debug(f"Event {event} out of date, updating...")
                    self.service.events().patch(
                        calendarId=self.cal_id, eventId=existing_id, body=body
                    ).execute()
                else:
                    logging.debug(
                        f"Event {event} is up to date in the calendar, taking no action..."
                    )
            else:
                logging.debug(f"Adding {event} to the calendar...")
                self.service.events().insert(
                    calendarId=self.cal_id, body=body
                ).execute()
