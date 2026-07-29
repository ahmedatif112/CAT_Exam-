import sqlite3
from notification_engine import WalletRepository


class SQLiteWalletRepository(WalletRepository):
    def __init__(self, connection: sqlite3.Connection):
        # Store the SQLite connection so we can use it later
        self.connection = connection

    def get_status(self, msg_id: str) -> str:
        cursor = self.connection.execute(
            """
            SELECT status
            FROM messages
            WHERE msg_id = ?
            """,
            (msg_id,)
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def save_status(self, msg_id: str, phone: str, status: str):
        self.connection.execute(
            """
            INSERT INTO messages (msg_id, phone, status)
            VALUES (?, ?, ?)
            """,
            (msg_id, phone, status)
        )
        self.connection.commit()


class BrokenSQLiteWalletRepository(WalletRepository):
    """A deliberately buggy repository — writes to the WRONG table name.
    Used to demonstrate the 'Mock Lie': this bug is invisible to unit tests
    (which use Mock and never touch real SQL) but caught immediately by
    integration tests (which use a real database schema)."""

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def get_status(self, msg_id: str) -> str:
        cursor = self.connection.execute(
            """
            SELECT status
            FROM msg_logs
            WHERE msg_id = ?
            """,
            (msg_id,)
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def save_status(self, msg_id: str, phone: str, status: str):
        self.connection.execute(
            """
            INSERT INTO msg_logs (msg_id, phone, status)
            VALUES (?, ?, ?)
            """,
            (msg_id, phone, status)
        )
        self.connection.commit()