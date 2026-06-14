import base64
import re
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
HERE = Path(__file__).parent  # deal_finder/


def get_credentials(token_file=None, creds_file=None):
    token_file = Path(token_file or HERE / "email_token.json")
    creds_file = Path(creds_file or HERE / "credentials.json")

    creds = None
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
            creds = flow.run_local_server(port=0, prompt="select_account")
        token_file.write_text(creds.to_json())

    return creds


def fetch_promo_emails(max_results=50):
    service = build("gmail", "v1", credentials=get_credentials())

    response = service.users().messages().list(
        userId="me",
        labelIds=["CATEGORY_PROMOTIONS"],
        maxResults=max_results,
    ).execute()

    messages = response.get("messages", [])
    emails = []

    for msg in messages:
        detail = service.users().messages().get(
            userId="me", id=msg["id"], format="full"
        ).execute()

        headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
        body = _extract_body(detail["payload"])

        emails.append({
            "id": msg["id"],
            "subject": headers.get("Subject", ""),
            "sender": headers.get("From", ""),
            "date": headers.get("Date", ""),
            "body": body,
        })

    return emails


def _extract_body(payload):
    if "parts" in payload:
        for part in payload["parts"]:
            data = part["body"].get("data", "")
            if not data:
                continue
            text = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
            if part["mimeType"] == "text/plain":
                return text[:3000]
            if part["mimeType"] == "text/html":
                return _strip_html(text)[:3000]

    data = payload["body"].get("data", "")
    if data:
        text = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        return (_strip_html(text) if "<html" in text.lower() else text)[:3000]

    return ""


def _strip_html(html):
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()
