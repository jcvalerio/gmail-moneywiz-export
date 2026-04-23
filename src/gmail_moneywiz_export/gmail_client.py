from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from gmail_moneywiz_export.message_text import extract_message_text
from gmail_moneywiz_export.models import GmailMessage

GMAIL_MODIFY_SCOPE = "https://www.googleapis.com/auth/gmail.modify"


class LabelResolutionError(ValueError):
    pass


class GmailClient:
    def __init__(self, credentials_path: Path, token_path: Path):
        self._credentials_path = credentials_path
        self._token_path = token_path
        self._creds = self._load_credentials()
        self._service = build("gmail", "v1", credentials=self._creds)
        self._label_cache: dict[str, str] | None = None

    def list_message_ids(self, query: str, limit: int | None = None) -> list[str]:
        message_ids: list[str] = []
        page_token: str | None = None

        while True:
            result = (
                self._service.users()
                .messages()
                .list(userId="me", q=query, pageToken=page_token, maxResults=min(limit or 100, 100))
                .execute()
            )
            messages = result.get("messages", [])
            for message in messages:
                message_ids.append(message["id"])
                if limit is not None and len(message_ids) >= limit:
                    return message_ids
            page_token = result.get("nextPageToken")
            if not page_token:
                return message_ids

    def get_message(self, message_id: str) -> GmailMessage:
        result = (
            self._service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        payload = result.get("payload", {})
        headers = payload.get("headers", [])
        subject = next((header["value"] for header in headers if header["name"].lower() == "subject"), "")
        sender = next((header["value"] for header in headers if header["name"].lower() == "from"), "")
        return GmailMessage(
            message_id=result["id"],
            subject=subject,
            sender=sender,
            label_ids=result.get("labelIds", []),
            text=extract_message_text(payload),
        )

    def ensure_label(self, label_name: str) -> str:
        label_id = self._find_label_id(label_name)
        if label_id:
            return label_id
        try:
            created = (
                self._service.users()
                .labels()
                .create(
                    userId="me",
                    body={
                        "name": label_name,
                        "labelListVisibility": "labelShow",
                        "messageListVisibility": "show",
                    },
                )
                .execute()
            )
            self._label_cache = None
            return created["id"]
        except HttpError as error:
            if getattr(error.resp, "status", None) != 409:
                raise
            self._label_cache = None
            label_id = self._find_label_id(label_name)
            if label_id:
                return label_id

            labels = self.list_labels()
            target = label_name.casefold()
            similar_labels = sorted(
                name
                for name in labels
                if target in name.casefold()
                or name.casefold() in target
                or name.casefold().startswith(f"{target}/")
                or target.startswith(f"{name.casefold()}/")
            )
            similar = ", ".join(similar_labels) if similar_labels else "none"
            raise LabelResolutionError(
                f"Could not resolve Gmail label '{label_name}'. Gmail reported a name conflict. Similar labels: {similar}"
            ) from error

    def list_labels(self) -> dict[str, str]:
        if self._label_cache is not None:
            return self._label_cache
        result = self._service.users().labels().list(userId="me").execute()
        self._label_cache = {label["name"]: label["id"] for label in result.get("labels", [])}
        return self._label_cache

    def _find_label_id(self, label_name: str) -> str | None:
        labels = self.list_labels()
        exact_match = labels.get(label_name)
        if exact_match:
            return exact_match

        target = label_name.casefold()
        for existing_name, label_id in labels.items():
            if existing_name.casefold() == target:
                return label_id
        return None

    def mark_processed_and_archive(self, message_id: str, processed_label_name: str) -> None:
        label_id = self.ensure_label(processed_label_name)
        (
            self._service.users()
            .messages()
            .modify(
                userId="me",
                id=message_id,
                body={
                    "addLabelIds": [label_id],
                    "removeLabelIds": ["INBOX"],
                },
            )
            .execute()
        )

    def _load_credentials(self) -> Credentials:
        creds: Credentials | None = None
        if self._token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self._token_path), [GMAIL_MODIFY_SCOPE])
            if not creds.has_scopes([GMAIL_MODIFY_SCOPE]):
                creds = None

        if creds and creds.valid:
            return creds

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            if creds.has_scopes([GMAIL_MODIFY_SCOPE]):
                self._token_path.parent.mkdir(parents=True, exist_ok=True)
                self._token_path.write_text(creds.to_json(), encoding="utf-8")
                return creds
            creds = None

        flow = InstalledAppFlow.from_client_secrets_file(str(self._credentials_path), [GMAIL_MODIFY_SCOPE])
        creds = flow.run_local_server(port=0)
        self._token_path.parent.mkdir(parents=True, exist_ok=True)
        self._token_path.write_text(creds.to_json(), encoding="utf-8")
        return creds
