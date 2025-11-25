# ... (inside the selected_id logic) ...
                        
                        if st.button("Mark as Sent & Notify User"):
                            # 1. Update DB
                            database.mark_as_sent(selected_id)
                            
                            # 2. Send Email to User
                            if mailer:
                                with st.spinner("Sending notification email..."):
                                    user_email = letter_data.get('user_email')
                                    # Pass the whole letter_data dict which now has recipient fields
                                    mailer.send_shipping_confirmation(user_email, letter_data)
                                    st.success("✅ Status updated & User notified!")
                            else:
                                st.success("✅ Status updated (Emailer offline)")
                                
                            st.rerun()