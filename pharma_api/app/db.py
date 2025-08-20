from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
from contextlib import contextmanager
from .config import settings

pool = ConnectionPool(
    conninfo=settings.DATABASE_URL,
    kwargs={"autocommit": False},
    min_size=1,
    max_size=10,
    max_idle=60,
    timeout=30,
)

@contextmanager
def get_conn():
    with pool.connection() as conn:
        conn.row_factory = dict_row
        # Safe defaults for read paths
        with conn.cursor() as cur:
            cur.execute(f"SET LOCAL statement_timeout = {settings.STATEMENT_TIMEOUT_MS};")
            cur.execute("SET LOCAL idle_in_transaction_session_timeout = 60000;")
            cur.execute("SET LOCAL application_name = 'pharma_api';")
        yield conn
