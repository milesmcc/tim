import base64
import pickle

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]

flow = InstalledAppFlow.from_client_secrets_file("google_creds.json", SCOPES)
creds = flow.run_local_server(port=0)
print(base64.b64encode(pickle.dumps(creds)))
