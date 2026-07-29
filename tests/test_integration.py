import sqlite3
from unittest.mock import Mock

import pytest

from notification_engine import (
    NotificationEngine,
    SMSGatewayClient
)
from sqlite_repository import SQLiteWalletRepository, BrokenSQLiteWalletRepository


@pytest.fixture
def sqlite_repo():
    connection = sqlite3.connect(":memory:")

    connection.execute(
        """
        CREATE TABLE messages (
            msg_id TEXT,
            phone TEXT,
            status TEXT
        )
        """
    )

    repository = SQLiteWalletRepository(connection)

    yield connection, repository

    connection.close()


def test_successful_dispatch_is_saved_in_sqlite(sqlite_repo):
    connection, repository = sqlite_repo

    mock_primary = Mock(spec=SMSGatewayClient)
    mock_primary.send_sms.return_value = True

    engine = NotificationEngine(
        repo=repository,
        primary_gateway=mock_primary
    )

    result = engine.dispatch(
        msg_id="INT001",
        phone="+250780000000",
        message="Your payment was successful"
    )

    row = connection.execute(
        """
        SELECT msg_id, phone, status
        FROM messages
        WHERE msg_id = ?
        """,
        ("INT001",)
    ).fetchone()

    assert result == "SENT_PRIMARY"
    assert row is not None

    assert row == (
        "INT001",
        "+250780000000",
        "SENT"
    )


def test_already_sent_message_is_not_resent_from_sqlite(sqlite_repo):
    connection, repository = sqlite_repo

    connection.execute(
        """
        INSERT INTO messages (msg_id, phone, status)
        VALUES (?, ?, ?)
        """,
        (
            "INT002",
            "+250780000000",
            "SENT"
        )
    )
    connection.commit()

    mock_primary = Mock(spec=SMSGatewayClient)

    engine = NotificationEngine(
        repo=repository,
        primary_gateway=mock_primary
    )

    result = engine.dispatch(
        msg_id="INT002",
        phone="+250780000000",
        message="Your payment was successful"
    )

    row_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM messages
        WHERE msg_id = ?
        """,
        ("INT002",)
    ).fetchone()[0]

    assert result == "ALREADY_SENT"
    assert row_count == 1

    mock_primary.send_sms.assert_not_called()


def test_mock_lie_integration_test_catches_broken_repo(sqlite_repo):
    # The fixture creates a table called "messages" — but this broken
    # repository tries to write to "msg_logs", which does NOT exist.
    # Unlike the unit test with a Mock repo, this test uses a REAL SQLite
    # connection, so the wrong table name causes an actual sqlite3.OperationalError.
    connection, _ = sqlite_repo
    broken_repository = BrokenSQLiteWalletRepository(connection)

    mock_primary = Mock(spec=SMSGatewayClient)
    mock_primary.send_sms.return_value = True

    engine = NotificationEngine(
        repo=broken_repository,
        primary_gateway=mock_primary
    )

    with pytest.raises(sqlite3.OperationalError):
        engine.dispatch(
            msg_id="INT003",
            phone="+250780000000",
            message="Your payment was successful"
        )