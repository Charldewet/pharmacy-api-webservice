from typing import Any

def ensure_user_notifications_table(cur) -> None:
	cur.execute(
		"""
		CREATE TABLE IF NOT EXISTS pharma.user_notifications (
		  id            bigserial PRIMARY KEY,
		  user_id       bigint NOT NULL REFERENCES pharma.users(user_id) ON DELETE CASCADE,
		  title         text NOT NULL,
		  body          text NOT NULL,
		  data          jsonb NOT NULL,
		  created_at    timestamptz NOT NULL DEFAULT now()
		)
		"""
	)


def insert_user_notification(cur, user_id: int, title: str, body: str, data: Any) -> None:
	ensure_user_notifications_table(cur)
	cur.execute(
		"""
		INSERT INTO pharma.user_notifications (user_id, title, body, data)
		VALUES (%s, %s, %s, %s)
		""",
		(user_id, title, body, data),
	) 