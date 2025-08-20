import os
from typing import Iterator
from contextlib import contextmanager
from psycopg import connect
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

@contextmanager
def get_conn():
    dsn = os.environ["DATABASE_URL"]
    with connect(dsn, row_factory=dict_row, autocommit=False) as conn:
        yield conn

@contextmanager
def get_cursor():
    with get_conn() as conn:
        with conn.cursor() as cur:
            yield cur
        conn.commit() 