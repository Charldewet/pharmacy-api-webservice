import imaplib
import email
from email.message import Message
from typing import List, Tuple, Dict
from datetime import datetime, timedelta
import socket


class ImapClient:
	def __init__(self, username: str, app_password: str, host: str = "imap.gmail.com", mailbox: str = "INBOX"):
		self.username = username
		self.app_password = app_password
		self.host = host
		self.mailbox = mailbox
		self.conn: imaplib.IMAP4_SSL | None = None

	def __enter__(self):
		# Set a sane network timeout to avoid long hangs
		socket.setdefaulttimeout(20)
		self.conn = imaplib.IMAP4_SSL(self.host)
		self.conn.login(self.username, self.app_password)
		self.conn.select(self.mailbox)
		return self

	def __exit__(self, exc_type, exc, tb):
		try:
			if self.conn is not None:
				self.conn.close()
				self.conn.logout()
		except Exception:
			pass

	def search_raw(self, raw_query: str, max_results: int = 500) -> List[str]:
		# Gmail IMAP supports X-GM-RAW to use Gmail search syntax
		assert self.conn is not None
		typ, data = self.conn.uid('SEARCH', 'CHARSET', 'UTF-8', 'X-GM-RAW', raw_query)
		if typ != 'OK':
			return []
		uids = data[0].decode().split()
		return uids[:max_results]

	@staticmethod
	def _imap_date(iso_date: str) -> str:
		# IMAP expects e.g. 15-Aug-2025
		d = datetime.fromisoformat(iso_date).date()
		return d.strftime('%d-%b-%Y')

	def search_by_date(self, since_iso: str, until_iso: str, max_results: int = 500) -> List[str]:
		assert self.conn is not None
		# IMAP BEFORE is strictly earlier than date; add +1 day to include until
		next_day = (datetime.fromisoformat(until_iso).date() + timedelta(days=1)).strftime('%d-%b-%Y')
		since_d = self._imap_date(since_iso)
		typ, data = self.conn.uid('SEARCH', None, f'(SINCE {since_d} BEFORE {next_day})')
		if typ != 'OK':
			return []
		uids = data[0].decode().split()
		return uids[:max_results]

	def fetch_subjects(self, uids: List[str]) -> Dict[str, str]:
		"""Return mapping uid -> subject using batched header-only fetches."""
		assert self.conn is not None
		subs: Dict[str, str] = {}
		batch = 50
		for i in range(0, len(uids), batch):
			chunk = uids[i:i+batch]
			seq = ','.join(chunk)
			typ, data = self.conn.uid('FETCH', seq, '(BODY.PEEK[HEADER.FIELDS (SUBJECT)])')
			if typ != 'OK' or not data:
				continue
			# data is a list like [(b'UID FETCH ...', b'headers'), b')', ...]
			for j in range(0, len(data), 2):
				if j+1 >= len(data):
					break
				meta = data[j]
				payload = data[j+1]
				if not isinstance(meta, tuple) or not payload:
					continue
				# Extract UID from meta line
				meta_line = meta[0].decode(errors='ignore')
				# Try to parse UID token
				uid_token = None
				for tok in meta_line.split():
					if tok.isdigit():
						uid_token = tok
						break
				if not uid_token:
					continue
				head = payload.decode(errors='ignore') if isinstance(payload, (bytes, bytearray)) else ''
				# Subject: ...\r\n
				subj = ''
				for line in head.splitlines():
					if line.lower().startswith('subject:'):
						subj = line.partition(':')[2].strip()
						break
				subs[uid_token] = subj
		return subs

	def filter_pdf_uids_by_bodystructure(self, uids: List[str]) -> List[str]:
		"""Quickly detect which messages have PDF attachments using BODYSTRUCTURE."""
		assert self.conn is not None
		pdf_uids: List[str] = []
		batch = 50
		for i in range(0, len(uids), batch):
			chunk = uids[i:i+batch]
			seq = ','.join(chunk)
			typ, data = self.conn.uid('FETCH', seq, '(BODYSTRUCTURE UID)')
			if typ != 'OK' or not data:
				continue
			for item in data:
				if not isinstance(item, tuple) or not item[0]:
					continue
				meta_line = item[0].decode(errors='ignore')
				# Extract UID from meta line: look for token after 'UID'
				uid_token = None
				parts = meta_line.replace('(', ' ').replace(')', ' ').split()
				for idx, tok in enumerate(parts):
					if tok.upper() == 'UID' and idx + 1 < len(parts):
						uid_token = parts[idx + 1]
						break
				if not uid_token:
					continue
				# More lenient: look for any PDF indicators in the bodystructure
				meta_upper = meta_line.upper()
				has_pdf = (
					'APPLICATION/PDF' in meta_upper or 
					'"PDF"' in meta_upper or 
					'.PDF' in meta_upper or
					'PDF' in meta_upper or
					'ATTACHMENT' in meta_upper
				)
				if has_pdf:
					pdf_uids.append(uid_token)
		return pdf_uids

	def filter_pdf_uids_simple(self, uids: List[str]) -> List[str]:
		"""Fallback: just check for has:attachment and return all UIDs."""
		assert self.conn is not None
		# Simple approach: just return all UIDs and let the full fetch filter
		return uids

	def fetch_pdf_attachments(self, uid: str) -> List[Tuple[str, bytes]]:
		assert self.conn is not None
		typ, msg_data = self.conn.uid('FETCH', uid, '(BODY.PEEK[])')
		if typ != 'OK' or not msg_data or not msg_data[0]:
			return []
		raw = msg_data[0][1]
		msg: Message = email.message_from_bytes(raw)
		files: List[Tuple[str, bytes]] = []
		for part in msg.walk():
			if part.get_content_maintype() == 'multipart':
				continue
			filename = part.get_filename()
			disp = part.get("Content-Disposition", "")
			if filename and filename.lower().endswith('.pdf') and 'attachment' in disp.lower():
				payload = part.get_payload(decode=True)
				if payload:
					files.append((filename, payload))
		return files

	def fetch_pdf_attachments_and_subject(self, uid: str) -> Tuple[str, List[Tuple[str, bytes]]]:
		assert self.conn is not None
		typ, msg_data = self.conn.uid('FETCH', uid, '(BODY.PEEK[])')
		if typ != 'OK' or not msg_data or not msg_data[0]:
			return "", []
		raw = msg_data[0][1]
		msg: Message = email.message_from_bytes(raw)
		subject = msg.get('Subject', '') or ''
		files: List[Tuple[str, bytes]] = []
		for part in msg.walk():
			if part.get_content_maintype() == 'multipart':
				continue
			filename = part.get_filename()
			disp = part.get("Content-Disposition", "")
			if filename and filename.lower().endswith('.pdf') and 'attachment' in disp.lower():
				payload = part.get_payload(decode=True)
				if payload:
					files.append((filename, payload))
		return subject, files 