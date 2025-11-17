import os
import json
import base64
from email.mime.text import MIMEText

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
]


class GmailClient:
    def __init__(self, client_secrets_file='credentials.json', token_file='token.json'):
        self.client_secrets_file = client_secrets_file
        self.token_file = token_file

    def get_authorization_url(self, redirect_uri=None):
        redirect = redirect_uri or os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:5000/oauth2callback')
        flow = Flow.from_client_secrets_file(
            self.client_secrets_file,
            scopes=SCOPES,
            redirect_uri=redirect,
        )
        auth_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
        return auth_url, state

    def fetch_and_store_token(self, authorization_response, state, redirect_uri=None):
        redirect = redirect_uri or os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:5000/oauth2callback')
        flow = Flow.from_client_secrets_file(
            self.client_secrets_file,
            scopes=SCOPES,
            state=state,
            redirect_uri=redirect,
        )
        flow.fetch_token(authorization_response=authorization_response)
        creds = flow.credentials
        with open(self.token_file, 'w') as f:
            f.write(creds.to_json())
        return creds

    def _load_credentials(self):
        if not os.path.exists(self.token_file):
            raise FileNotFoundError('token file not found; run /authorize first')
        data = json.load(open(self.token_file, 'r'))
        creds = Credentials.from_authorized_user_info(data, SCOPES)
        return creds

    def _build_service(self):
        creds = self._load_credentials()
        service = build('gmail', 'v1', credentials=creds)
        return service

    def list_unread_emails(self, max_results=20):
        service = self._build_service()
        try:
            resp = service.users().messages().list(userId='me', q='is:unread', maxResults=max_results).execute()
            msgs = resp.get('messages', [])
            results = []
            for m in msgs:
                msg = service.users().messages().get(userId='me', id=m['id'], format='full').execute()
                snippet = msg.get('snippet', '')
                headers = {h['name']: h['value'] for h in msg.get('payload', {}).get('headers', [])}
                subject = headers.get('Subject', '')
                sender = headers.get('From', '')
                results.append({'id': m['id'], 'subject': subject, 'from': sender, 'snippet': snippet})
            return results
        except HttpError as e:
            raise

    def send_message(self, to_address, subject, body):
        service = self._build_service()
        message = MIMEText(body)
        message['to'] = to_address
        message['from'] = 'me'
        message['subject'] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        return service.users().messages().send(userId='me', body={'raw': raw}).execute()
