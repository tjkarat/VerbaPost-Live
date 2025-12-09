# pricing_engine.py

TIER_PRICING = {
    "Standard": 2.99,
    "Heirloom": 5.99,
    "Civic": 6.99,
    "Santa": 9.99,
    "Campaign": 2.99 # Base price for first letter
}

CAMPAIGN_UNIT_PRICE = 1.99
INTL_SURCHARGE = 2.00
CERTIFIED_SURCHARGE = 12.00

def calculate_total(tier, is_intl=False, is_certified=False, qty=1):
    """
    Server-side price calculation.
    Returns price as a float (e.g., 14.99).
    """
    # 1. Base Price
    base = TIER_PRICING.get(tier, 2.99)
    
    # 2. Campaign Logic
    total = 0.0
    if tier == "Campaign":
        # First letter at base price, rest at unit price
        if qty < 1: qty = 1
        total = base + ((qty - 1) * CAMPAIGN_UNIT_PRICE)
    else:
        total = base

    # 3. Add-ons (Per Letter Logic)
    # Note: If campaign, surcharges apply to ALL letters
    surcharges = 0.0
    if is_intl: surcharges += INTL_SURCHARGE
    if is_certified: surcharges += CERTIFIED_SURCHARGE
    
    if tier == "Campaign":
        total += (surcharges * qty)
    else:
        total += surcharges
        
    return round(total, 2)
