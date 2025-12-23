import audit_engine
import json
import sys

def test_audit_system():
    print("🔍 Starting Audit Engine Validation...")

    # 1. Define Test Data
    test_email = "validation_test@verbapost.com"
    test_event = "VALIDATION_CHECK"
    test_session_id = "sess_test_12345"
    test_details = {"status": "running", "check": "columns_exist"}

    # 2. Try to Log an Event (WRITE Test)
    try:
        print(f"   Attempting to log event: {test_event}...")
        audit_engine.log_event(test_email, test_event, test_session_id, test_details)
        print("   ✅ Write Success: Event sent to database engine.")
    except Exception as e:
        print(f"   ❌ Write Failed: {e}")
        return

    # 3. Try to Retrieve the Event (READ Test)
    try:
        print("   Attempting to read back the event...")
        db = audit_engine.get_session()
        
        # Query for the event we just made
        record = db.query(audit_engine.AuditEvent).filter(
            audit_engine.AuditEvent.stripe_session_id == test_session_id
        ).first()

        if record:
            print(f"   ✅ Read Success: Found Record ID {record.id}")
            print(f"      - Timestamp: {record.timestamp}")
            print(f"      - Email: {record.user_email}")
            print(f"      - Event: {record.event_type}")
            print(f"      - Details: {record.details}")
            
            # 4. Verify Columns (Implicit Check)
            # If we accessed .details and .stripe_session_id without error, the columns exist.
            if record.stripe_session_id == test_session_id:
                print("   ✅ Schema Validation: All required columns appear to be present.")
        else:
            print("   ❌ Read Failed: Record not found (Write might have failed silently).")

        db.close()

    except Exception as e:
        print(f"   ❌ Read/Schema Failed: {e}")
        print("   (This usually means the database table 'audit_events' is missing a column or the table doesn't exist.)")

if __name__ == "__main__":
    test_audit_system()
