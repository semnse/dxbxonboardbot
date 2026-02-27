"""
Database connection using synchronous psycopg2 for maximum reliability on Windows
"""
import logging
from contextlib import contextmanager
from typing import Generator, Optional, Dict, Any

import psycopg2
from psycopg2 import sql

from app.config import settings

logger = logging.getLogger(__name__)


class Database:
    """Singleton database connection manager"""
    
    _instance = None
    _conn = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def _get_connection(self):
        """Create new connection"""
        try:
            conn = psycopg2.connect(
                host="localhost",
                port=5432,
                user="postgres",
                password="postgres",
                database="onboarding_bot"
            )
            # Set encoding
            conn.set_client_encoding('UTF8')
            logger.info("Database connected")
            return conn
        except Exception as e:
            logger.error(f"DB connect error: {e}")
            raise
    
    def get_connection(self):
        """Get or create connection"""
        if self._conn is None or self._conn.closed:
            self._conn = self._get_connection()
        return self._conn
    
    def close(self):
        """Close connection"""
        if self._conn and not self._conn.closed:
            self._conn.close()
        self._conn = None


# Global instance
db = Database()


def dict_fetchall(cursor) -> list:
    """Return all rows from a cursor as a list of dicts"""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def dict_fetchone(cursor) -> Optional[Dict[str, Any]]:
    """Return one row from a cursor as a dict"""
    columns = [col[0] for col in cursor.description]
    row = cursor.fetchone()
    return dict(zip(columns, row)) if row else None


@contextmanager
def get_db_cursor():
    """
    Context manager for database cursors.
    
    Usage:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM table")
            rows = dict_fetchall(cur)
    """
    conn = None
    cur = None
    try:
        conn = db.get_connection()
        cur = conn.cursor()
        yield cur
        conn.commit()
    except Exception as e:
        logger.error(f"Cursor error: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if cur:
            cur.close()
