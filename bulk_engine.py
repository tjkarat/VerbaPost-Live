import csv
import io
import logging
import audit_engine
import mailer
from address_standard import StandardAddress

logger = logging.getLogger(__name__)

def parse_csv(file_obj):
    """
    Parses a CSV file and returns a list of dictionaries.
    Uses flexible header matching to prevent skipping rows.
    """
    contacts = []
    try:
        # Handle Streamlit UploadedFile vs string buffer
        if hasattr(file_obj, "getvalue"):
            content = file_obj.getvalue().decode("utf-8")
        else:
            content = file_obj
            
        reader = csv.DictReader(io.StringIO(content))
        
        # Flexible Header Mapping (Normalization)
        for row in reader:
            # Clean up keys (lowercase and strip whitespace)
            clean_row = {k.lower().strip(): v for k, v in row.items() if k}
            
            # Map variations to standard keys
            normalized = {
                "name": clean_row.get("name") or clean_row.get("recipient") or clean_row.get("organization") or "",
                "street": clean_row.get("street") or clean_row.get("address") or clean_row.get("address_line1") or "",
                "address_line2": clean_row.get("address_line2") or clean_row.get("apt") or clean_row.get("suite") or "",
                "city": clean_row.get("city") or clean_row.get("address_city") or "",
                "state": clean_row.get("state") or clean_row.get("address_state") or clean_row.get("prov") or "",
                "zip": clean_row.get("zip") or clean_row.get("zip_code") or clean_row.get("postal") or clean_row.get("address_zip") or ""
            }
            
            # Validation: Only add if we have at least a name and street
            if normalized["name"] and normalized["street"]:
                contacts.append(normalized)
            else:
                logger.warning(f"Skipping incomplete row: {row}")
                
        return contacts
    except Exception as e:
        logger.error(f"CSV Parse Error: {e}")
        return []

def run_bulk_campaign(user_email, contacts, pdf_bytes, tier_name="Campaign"):
    """
    Processes a list of contacts, sends mail via mailer.py, and logs to Audit Engine.
    """
    results = {
        "success": 0,
        "failed": 0,
        "letter_ids": []
    }

    if not contacts:
        return results

    audit_engine.log_event(
        user_email=user_email,
        event_type="BULK_CAMPAIGN_START",
        description=f"Starting campaign for {len(contacts)} recipients.",
        details={"tier": tier_name}
    )

    for contact_data in contacts:
        try:
            # 1. Standardize the address object
            addr_to = StandardAddress.from_dict(contact_data)
            
            # 2. Use mailer.py to send (This handles PostGrid API)
            # Assuming sender info is VerbaPost corporate or user profile-based
            # For campaigns, we usually use the user's return address
            success, response = mailer.send_letter(
                pdf_bytes=pdf_bytes,
                addr_to=addr_to,
                addr_from=None, # mailer.py will use VerbaPost default if None
                tier=tier_name
            )

            if success:
                results["success"] += 1
                letter_id = response if isinstance(response, str) else "unknown_id"
                results["letter_ids"].append(letter_id)
                
                # Log individual success for security trail
                audit_engine.log_event(
                    user_email=user_email,
                    event_type="LETTER_SENT",
                    description=f"Campaign letter sent to {addr_to.name}",
                    details={"letter_id": letter_id, "recipient": addr_to.name}
                )
            else:
                results["failed"] += 1
                logger.error(f"Failed to send to {addr_to.name}: {response}")

        except Exception as e:
            results["failed"] += 1
            logger.error(f"Bulk Process Exception for {contact_data.get('name')}: {e}")

    # Final Campaign Summary Log
    audit_engine.log_event(
        user_email=user_email,
        event_type="BULK_CAMPAIGN_COMPLETE",
        description=f"Campaign finished: {results['success']} sent, {results['failed']} failed.",
        details={"total": len(contacts)}
    )

    return results