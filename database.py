def save_draft(user_email, text, tier, price, recipient_data=None):
    """
    Saves a letter with recipient details.
    """
    sb = get_client()
    if sb:
        data = {
            "user_email": user_email,
            "body_text": text,
            "tier": tier,
            "price": price,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
        
        # Add address if provided
        if recipient_data:
            data.update({
                "recipient_name": recipient_data.get("name"),
                "recipient_street": recipient_data.get("street"),
                "recipient_city": recipient_data.get("city"),
                "recipient_state": recipient_data.get("state"),
                "recipient_zip": recipient_data.get("zip")
            })
            
        sb.table("letters").insert(data).execute()