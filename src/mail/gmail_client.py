import base64
import os
from typing import List, Tuple
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailClient:
	def __init__(self, credentials_path: str = "secrets/credentials.json", token_path: str = "secrets/token.json"):
		self.creds = None
		if os.path.exists(token_path):
			self.creds = Credentials.from_authorized_user_file(token_path, SCOPES)
		if not self.creds or not self.creds.valid:
			if self.creds and self.creds.expired and self.creds.refresh_token:
				self.creds.refresh(Request())
			else:
				flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
				self.creds = flow.run_local_server(port=0)
			os.makedirs(os.path.dirname(token_path), exist_ok=True)
			with open(token_path, "w") as token:
				token.write(self.creds.to_json())
		self.service = build("gmail", "v1", credentials=self.creds)

	def search_messages(self, user_id: str = "me", query: str = "", max_results: int = 500) -> List[str]:
		svc = self.service.users().messages()
		msg_ids: List[str] = []
		page_token = None
		while True:
			req = svc.list(userId=user_id, q=query, pageToken=page_token, maxResults=min(500, max_results))
			res = req.execute()
			for m in res.get("messages", []):
				msg_ids.append(m["id"])
			page_token = res.get("nextPageToken")
			if not page_token or len(msg_ids) >= max_results:
				break
		return msg_ids

	def fetch_pdf_attachments(self, message_id: str, user_id: str = "me") -> List[Tuple[str, bytes]]:
		svc = self.service.users().messages()
		msg = svc.get(userId=user_id, id=message_id).execute()
		attachments: List[Tuple[str, bytes]] = []

		def _walk_parts(parts):
			for part in parts:
				if part.get("filename") and part["filename"].lower().endswith(".pdf"):
					body = part.get("body", {})
					att_id = body.get("attachmentId")
					if att_id:
						att = svc.attachments().get(userId=user_id, messageId=message_id, id=att_id).execute()
						data = base64.urlsafe_b64decode(att["data"])
						attachments.append((part["filename"], data))
				if part.get("parts"):
					_walk_parts(part["parts"])

		payload = msg.get("payload", {})
		if payload.get("parts"):
			_walk_parts(payload["parts"])
		return attachments 