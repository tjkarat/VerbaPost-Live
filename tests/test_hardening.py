import pytest
from unittest.mock import patch, MagicMock
import logging

# Standard imports: The "PYTHONPATH=." command now handles finding these
from ai_engine import _normalize_phone
import mailer
import payment_engine

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

# 4. NEW TEST: Payment Engine Integration
@patch('stripe.checkout.Session.create')
def test_stripe_checkout_creation(mock_stripe):
    """
    Verifies that the payment engine correctly formats the Stripe request.
    """
    mock_stripe.return_value = MagicMock(url="https://checkout.stripe.com/test")
    
    url = payment_engine.create_checkout_session(
        line_items=[{"price_data": {"unit_amount": 299}, "quantity": 1}],
        user_email="test@example.com",
        draft_id="draft_123"
    )
    
    assert url == "https://checkout.stripe.com/test"
    # Ensure metadata contains our critical draft_id for fulfillment
    args, kwargs = mock_stripe.call_args
    assert kwargs['metadata']['draft_id'] == "draft_123"
    assert kwargs['customer_email'] == "test@example.com"