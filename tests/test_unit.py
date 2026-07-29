import pytest
from unittest.mock import Mock
from notification_engine import NotificationEngine


def make_engine():
    """Helper to build a fresh engine with mocked dependencies.
    Using Mock() means we don't touch a real database or real SMS gateway —
    everything is fake and controllable."""
    mock_repo = Mock()
    mock_primary = Mock()
    mock_backup = Mock()
    engine = NotificationEngine(mock_repo, mock_primary, mock_backup)
    return engine, mock_repo, mock_primary, mock_backup


def test_valid_phone_number_passes_format_check():
    # A correctly formatted E.164 number should pass validation
    # and proceed to attempt sending via the primary gateway.
    engine, mock_repo, mock_primary, mock_backup = make_engine()
    mock_repo.get_status.return_value = "PENDING"   # not sent yet
    mock_primary.send_sms.return_value = True       # pretend sending succeeds

    result = engine.dispatch("msg1", "+250780000000", "Hello")

    assert result == "SENT_PRIMARY"


def test_invalid_phone_missing_plus_raises_value_error():
    # Missing the leading "+" breaks the E.164 format, so dispatch()
    # should raise ValueError immediately, before touching the repo.
    engine, mock_repo, mock_primary, mock_backup = make_engine()

    with pytest.raises(ValueError):
        engine.dispatch("msg1", "0780000000", "Hello")

    # Proves validation happens FIRST, before any database call.
    mock_repo.get_status.assert_not_called()


def test_invalid_phone_bad_format_raises_value_error():
    # "+00012" starts with a zero after the "+", which the regex rejects
    # (E.164 numbers can't start with 0 after the country code).
    engine, mock_repo, mock_primary, mock_backup = make_engine()

    with pytest.raises(ValueError):
        engine.dispatch("msg1", "+00012", "Hello")

    mock_repo.get_status.assert_not_called()


def test_idempotency_already_sent_skips_gateway():
    # If the repo says this message was already "SENT", dispatch()
    # should short-circuit and return immediately —
    # it must NOT try sending the SMS again (avoids duplicate messages).
    engine, mock_repo, mock_primary, mock_backup = make_engine()
    mock_repo.get_status.return_value = "SENT"

    result = engine.dispatch("msg1", "+250780000000", "Hello")

    assert result == "ALREADY_SENT"
    mock_primary.send_sms.assert_not_called()
    mock_backup.send_sms.assert_not_called()

  
def test_retry_logic_fails_once_then_succeeds():
    # side_effect lets us define a SEQUENCE of behaviors across multiple calls.
    # 1st call: raises an exception (simulating a network failure)
    # 2nd call: returns True (simulating success on retry)
    engine, mock_repo, mock_primary, mock_backup = make_engine()
    mock_repo.get_status.return_value = "PENDING"
    mock_primary.send_sms.side_effect = [Exception("Network error"), True]

    result = engine.dispatch("msg1", "+250780000000", "Hello")

    assert result == "SENT_PRIMARY"
    # Confirms the loop actually retried — called exactly twice, not once.
    assert mock_primary.send_sms.call_count == 2
    # Confirms the final successful attempt was saved as SENT.
    mock_repo.save_status.assert_called_with("msg1", "+250780000000", "SENT")  

def test_fallback_gateway_used_when_primary_fails_twice():
    # Primary fails on BOTH attempts (the loop runs range(2), so 2 tries).
    # Backup succeeds, so dispatch() should fall through to it.
    engine, mock_repo, mock_primary, mock_backup = make_engine()
    mock_repo.get_status.return_value = "PENDING"
    mock_primary.send_sms.side_effect = [Exception("fail 1"), Exception("fail 2")]
    mock_backup.send_sms.return_value = True

    result = engine.dispatch("msg1", "+250780000000", "Hello")

    assert result == "SENT_BACKUP"
    assert mock_primary.send_sms.call_count == 2
    mock_backup.send_sms.assert_called_once()
    mock_repo.save_status.assert_called_with("msg1", "+250780000000", "SENT_BACKUP")   


def test_complete_failure_both_gateways_fail():
    # Primary fails both attempts, backup also fails.
    # dispatch() should save "FAILED" status and then raise RuntimeError.
    engine, mock_repo, mock_primary, mock_backup = make_engine()
    mock_repo.get_status.return_value = "PENDING"
    mock_primary.send_sms.side_effect = [Exception("fail 1"), Exception("fail 2")]
    mock_backup.send_sms.side_effect = Exception("backup fail")

    with pytest.raises(RuntimeError):
        engine.dispatch("msg1", "+250780000000", "Hello")

    mock_repo.save_status.assert_called_with("msg1", "+250780000000", "FAILED")     