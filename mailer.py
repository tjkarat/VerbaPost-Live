def send_shipping_confirmation(user_email, recipient_info):
    """
    Notifies the user that their letter has been mailed.
    """
    if not resend.api_key: return False

    # Safely handle potential None values
    r_name = recipient_info.get('recipient_name') or "Recipient"
    r_street = recipient_info.get('recipient_street') or ""
    r_city = recipient_info.get('recipient_city') or ""
    r_state = recipient_info.get('recipient_state') or ""
    
    formatted_address = f"{r_name}<br>{r_street}<br>{r_city}, {r_state}"

    subject = "🚀 Your Letter is on the way!"
    
    html_content = f"""
    <div style="font-family: sans-serif; padding: 20px; color: #333; max-width: 600px;">
        <h2 style="color: #2a5298;">VerbaPost Shipment Update</h2>
        <p>Great news! Your letter has been printed, stamped, and handed off to the USPS.</p>
        
        <div style="background: #f8f9fa; border-left: 4px solid #2a5298; padding: 15px; margin: 20px 0;">
            <p style="margin: 0; color: #666; font-size: 12px;">MAILED TO:</p>
            <p style="margin: 5px 0 0 0; font-weight: bold; font-size: 16px;">
                {formatted_address}
            </p>
        </div>
        
        <p>Thank you for using VerbaPost to send real mail.</p>
    </div>
    """

    try:
        # Use sender from secrets or default
        sender = st.secrets["email"].get("sender_email", "onboarding@resend.dev")
        
        resend.Emails.send({
            "from": f"VerbaPost Support <{sender}>",
            "to": user_email,
            "subject": subject,
            "html": html_content
        })
        return True
    except Exception as e:
        print(f"❌ Shipping Email Failed: {e}")
        return False