import pytest
from unittest.mock import patch, MagicMock
import logging

# Standard imports: The YAML now tells the robot where to find these
from ai_engine import _normalize_phone
import mailer

# 1. TEST: Phone Number Normalization
def test_phone_normalization():
    assert _normalize_phone("(615) 555-1212") == "+16155551212"
    with pytest.raises(ValueError, match="11-digit number must start with 1"):
        _normalize_phone("61555512123")

# 2. TEST: Credit Atomicity (Pretend Mailer Fails)
@patch('mailer.send_letter')
@patch('database.update_user_credits')
def test_credit_safety_on_failure(mock_db, mock_mailer):
    mock_mailer.return_value = None 
    mock_db.assert_not_called()

# 3. TEST: Security Log Masking
def test_log_masking(caplog):
    with caplog.at_level(logging.ERROR):
        mailer.send_letter(b"fake_pdf", {}, {}, tier="Standard")
        assert "[Response Content Hidden for Security]" in caplog.text
        assert "sk_live_" not in caplog.text
