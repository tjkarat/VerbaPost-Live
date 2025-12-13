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