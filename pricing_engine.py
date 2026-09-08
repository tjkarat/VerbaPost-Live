import math

# Updated Pricing Tier
TIER_PRICING = {
    "Standard": 2.99,
    "Heirloom": 5.99,
    "Civic": 6.99,
    "Santa": 9.99,
    "Campaign": 2.99,
    "Legacy": 15.99  # 🆕 THE NEW TIER
}

def calculate_total(tier, is_intl=False, is_certified=False, qty=1):
    """
    Server-side pricing logic.
    Legacy Tier includes: 
    - AI Polish (included)
    - Archival Paper (included)
    - Digital Purge (feature)
    """
    base = TIER_PRICING.get(tier, 2.99)
    
    # Bulk logic for Campaign
    if tier == "Campaign":
        total = base + ((qty - 1) * 1.99)
    else:
        total = base
    
    # International Surcharge
    if is_intl: 
        total += 2.00
    
    # Certified Mail (Often included in Legacy marketing, but added here for safety)
    if is_certified: 
        total += 12.00
    
    return round(total, 2)

# ==========================================
# 🆕 PROSPECT ACQUISITION PRICING (advisor-branded free letter)
# ==========================================
# The billable unit is the INVITATION mailed to the advisor's uploaded list.
# $20 per invitation. An advisor's FIRST campaign is a flat $500 for exactly
# 25 invitations; every campaign after that is full price. The story letter
# produced when a prospect responds is included at no extra charge.

PROSPECT_LETTER_PRICE_CENTS = 2000
FIRST_CAMPAIGN_PRICE_CENTS = 50000
FIRST_CAMPAIGN_LETTERS = 25
REPEAT_MIN_LETTERS = 1
REPEAT_MAX_LETTERS = 100


def prospect_quote(has_prior_purchase, letters=None):
    """
    Server-side quote for a prospect-letter purchase.
    Returns dict: kind, letters, unit_cents, total_cents, label.
    First campaign ignores `letters` — it is always the 25-letter bundle.
    """
    if not has_prior_purchase:
        return {
            "kind": "first_campaign",
            "letters": FIRST_CAMPAIGN_LETTERS,
            "unit_cents": FIRST_CAMPAIGN_PRICE_CENTS // FIRST_CAMPAIGN_LETTERS,
            "total_cents": FIRST_CAMPAIGN_PRICE_CENTS,
            "label": f"First Prospect Campaign — {FIRST_CAMPAIGN_LETTERS} invitations mailed",
        }
    try:
        qty = int(letters or REPEAT_MIN_LETTERS)
    except (TypeError, ValueError):
        qty = REPEAT_MIN_LETTERS
    qty = max(REPEAT_MIN_LETTERS, min(REPEAT_MAX_LETTERS, qty))
    return {
        "kind": "repeat",
        "letters": qty,
        "unit_cents": PROSPECT_LETTER_PRICE_CENTS,
        "total_cents": PROSPECT_LETTER_PRICE_CENTS * qty,
        "label": f"Prospect Invitations — {qty} × ${PROSPECT_LETTER_PRICE_CENTS / 100:.0f}",
    }
