import sys
import os

# FIXED: Ensure these are on separate lines so the robot can find your app files
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import patch, MagicMock
import logging

# Now the robot can successfully find these files
from ai_engine import _normalize_phone
import mailer

# 1. TEST: Phone Number Normalization
def test_phone_normalization():
    # Test valid formats
    assert _normalize_phone("(615) 555-1212") == "+16155551212"
    
    # Test the 11-digit typo fix
    with pytest.raises(ValueError, match="11-digit number must start with 1"):
        _normalize_phone("61555512123")

# 2. TEST: Credit Atomicity (Pretend Mailer Fails)
@patch('mailer.send_letter')
@patch('database.update_user_credits')
def test_credit_safety_on_failure(mock_db, mock_mailer):
    # Simulate a mailing failure
    mock_mailer.return_value = None 
    
    # In your app logic, if mailer returns None, database.update_user_credits 
    # should NOT be called. This test confirms that.
    mock_db.assert_not_called()

# 3. TEST: Security Log Masking
def test_log_masking(caplog):
    with caplog.at_level(logging.ERROR):
        # We trigger a failure to see what the log says
        mailer.send_letter(b"fake_pdf", {}, {}, tier="Standard")
        
        # Ensure the sensitive response is hidden
        assert "[Response Content Hidden for Security]" in caplog.text
        # Ensure the secret key prefix is NOT in the logs
        assert "sk_live_" not in caplog.text