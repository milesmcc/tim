import pickle
import base64
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/calendar']

flow = InstalledAppFlow.from_client_secrets_file("google_creds.json", SCOPES)
creds = flow.run_local_server(port=0)
print(base64.b64encode(pickle.dumps(creds)))
