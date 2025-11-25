def render_review_page():
    render_hero("Review Letter", "Finalize and send")
    
    civic_targets = st.session_state.get("civic_targets", [])
    is_civic = len(civic_targets) > 0
    
    if is_civic:
        st.info(f"🏛️ **Civic Blast:** Letter will be sent to {len(civic_targets)} reps.")
    
    is_sent = st.session_state.get("letter_sent", False)
    st.text_area("Body", st.session_state.get("transcribed_text", ""), height=300, disabled=is_sent)
    
    if not is_sent:
        if st.button("🚀 Send Letter", type="primary", use_container_width=True):
            if database and st.session_state.get("user"):
                u = st.session_state.user
                email = ""
                if isinstance(u, dict): email = u.get("email")
                elif hasattr(u, "email"): email = u.email
                elif hasattr(u, "user"): email = u.user.email
                
                tier = st.session_state.get("locked_tier", "Standard")
                text = st.session_state.get("transcribed_text", "")
                price = st.session_state.get("temp_price", 2.99)
                
                # --- CAPTURE RECIPIENT DATA ---
                recipient_data = {
                    "name": st.session_state.get("to_name", ""),
                    "street": st.session_state.get("to_street", ""),
                    "city": st.session_state.get("to_city", ""),
                    "state": st.session_state.get("to_state", ""),
                    "zip": st.session_state.get("to_zip", "")
                }
                
                if is_civic:
                    names = ", ".join([t['name'] for t in civic_targets])
                    text = f"[CIVIC BLAST TARGETS: {names}]\n\n{text}"
                    # For Civic, we just note it's a blast
                    recipient_data["name"] = "Civic Blast (Multiple)"
                
                # PASS RECIPIENT DATA TO DB
                database.save_draft(email, text, tier, price, recipient_data)
                
                # Notification Trigger (Admin)
                if "Heirloom" in tier and mailer:
                    mailer.send_heirloom_notification(email, text)
            
            st.session_state.letter_sent = True
            st.rerun()