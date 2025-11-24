# ... inside the "store" block, at the bottom of col2 ...
                
                # Logic to generate link if missing
                current_config = f"{service_tier}_{price}_{language}"
                if "stripe_url" not in st.session_state or st.session_state.get("last_config") != current_config:
                     success_link = f"{YOUR_APP_URL}?tier={tier_name}&lang={language}"
                     user_email = st.session_state.get("user_email", "guest@verbapost.com")
                     
                     # Save draft
                     draft_id = database.save_draft(user_email, "", "", "", "", "")
                     
                     if draft_id:
                         success_link += f"&letter_id={draft_id}"
                         # Generate Link
                         url, session_id = payment_engine.create_checkout_session(
                            f"VerbaPost {service_tier}", int(price * 100), success_link, YOUR_APP_URL
                        )
                         if url:
                             st.session_state.stripe_url = url
                             st.session_state.stripe_session_id = session_id
                             st.session_state.last_config = current_config
                         else:
                             st.session_state.stripe_url = None
                
                # DISPLAY BUTTON OR ERROR
                if st.session_state.stripe_url:
                    st.link_button(f"Pay ${price} & Begin", st.session_state.stripe_url, type="primary", use_container_width=True)
                else:
                    st.error("⚠️ Payment System Offline")
                    st.caption("Check Streamlit Secrets: Is `STRIPE_SECRET_KEY` set?")