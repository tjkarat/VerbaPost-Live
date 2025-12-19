import csv
import io
import logging
import audit_engine
import mailer
from address_standard import StandardAddress

logger = logging.getLogger(__name__)

def parse_csv(file_obj):
    """
    Parses a CSV file using positional indexing to ensure 100% reliability 
    regardless of header naming or hidden characters.
    """
    contacts = []
    try:
        if hasattr(file_obj, "getvalue"):
            content = file_obj.getvalue().decode("utf-8")
        else:
            content = file_obj
            
        # Use standard reader to avoid DictReader header-matching failures
        f = io.StringIO(content)
        reader = csv.reader(f)
        
        # Skip the header row
        headers = next(reader, None)
        if not headers:
            return []

        for row in reader:
            # Ensure the row has enough columns (name, street, city, state, zip = 5)
            if len(row) < 5:
                logger.warning(f"Skipping row with insufficient data: {row}")
                continue
                
            # Direct positional mapping based on your Seniors.csv:
            # 0: name, 1: street, 2: city, 3: state, 4: zip
            normalized = {
                "name": row[0].strip() if row[0] else "",
                "street": row[1].strip() if row[1] else "",
                "city": row[2].strip() if row[2] else "",
                "state": row[3].strip() if row[3] else "",
                "zip": row[4].strip() if row[4] else "",
                "address_line2": "" # Fallback for bulk formatting
            }
            
            # Validation: Name and Street are the bare minimum requirements
            if normalized["name"] and normalized["street"]:
                contacts.append(normalized)
            else:
                logger.warning(f"Skipping incomplete row: {row}")
                
        return contacts
    except Exception as e:
        logger.error(f"Critical CSV Parse Error: {e}")
        return []

def run_bulk_campaign(user_email, contacts, pdf_bytes, tier_name="Campaign"):
    """
    Processes the validated contact list and executes the mailing loop.
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
        description=f"Campaign started for {len(contacts)} recipients.",
        details={"tier": tier_name}
    )

    for contact_data in contacts:
        try:
            addr_to = StandardAddress.from_dict(contact_data)
            
            # This calls the mailer.py logic you already have in production
            success, response = mailer.send_letter(
                pdf_bytes=pdf_bytes,
                addr_to=addr_to,
                addr_from=None, # Defaults to VerbaPost corporate return address
                tier=tier_name
            )

            if success:
                results["success"] += 1
                letter_id = response if isinstance(response, str) else "unknown_id"
                results["letter_ids"].append(letter_id)
                
                audit_engine.log_event(
                    user_email=user_email,
                    event_type="LETTER_SENT",
                    description=f"Campaign mail dispatched to {addr_to.name}",
                    details={"letter_id": letter_id}
                )
            else:
                results["failed"] += 1
                logger.error(f"Mailing failed for {contact_data.get('name')}: {response}")

        except Exception as e:
            results["failed"] += 1
            logger.error(f"Bulk Process Exception for {contact_data.get('name')}: {e}")

    audit_engine.log_event(
        user_email=user_email,
        event_type="BULK_CAMPAIGN_COMPLETE",
        description=f"Campaign finished. Sent: {results['success']} | Failed: {results['failed']}",
        details={"total_attempted": len(contacts)}
    )

    return results