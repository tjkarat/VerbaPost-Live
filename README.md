VerbaPost System Documentation (v2.5.7)
Project Name: VerbaPost Tech Stack: Python, Streamlit, Supabase (Postgres/Auth), Stripe, OpenAI (Whisper/GPT), PostGrid (Print Mail), Resend (Email). Production URL: verbapost.com Staging URL: verbapost.streamlit.app

1. High-Level Architecture
VerbaPost is a voice-to-mail web application.

Input: User records audio via browser.

Process: OpenAI Whisper transcribes audio; GPT-4 optionaly refines text.

Format: fpdf2 generates a PDF simulating handwriting (Standard/Heirloom/Santa modes).

Payment: Stripe Checkout handles transactions before final processing.

Output: PostGrid API receives the PDF and physical address for mailing.

Audit: All critical actions are logged to audit_events table.

2. File Manifest & Responsibilities
Core System
main.py: The entry point. Handles routing (splash, login, store, workspace, admin), global CSS injection, and Stripe payment return logic.

secrets_manager.py: Wraps st.secrets to safely handle API keys for local dev and cloud.

dockerfile: Deployment config. Installs ffmpeg (required for Whisper) and runs seo_injector.py.

User Interface (Views)
ui_splash.py: Landing page. Contains Hero section, Pricing Cards, and Leaderboard. Heavily styled with custom CSS.

ui_login.py: Handles Auth tabs (Login/Signup) and Password Reset flows.

ui_main.py: The primary app logic.

Store Mode: Package selection (Standard/Santa/Civic/Campaign).

Workspace Mode: Audio recording, Address inputs, Signature canvas, "Magic Editor" buttons.

Review Mode: Final text edit and "Send Letter" execution.

ui_admin.py: Back-office for Tarak. Allows viewing drafts, fixing addresses, and manually regenerating PDFs.

ui_legal.py: Privacy Policy and Terms of Service.

Backend Engines (Logic)
auth_engine.py: Supabase wrapper for sign_in, sign_up (creates User Profile), and password resets.

database.py: SQLAlchemy ORM. Manages UserProfile, LetterDraft, SavedContact. Handles Leaderboard queries.

payment_engine.py: Stripe wrapper. Creates Checkout Sessions and verifies payment_status using Session IDs.

ai_engine.py:

transcribe_audio: Uses OpenAI Whisper (local model) to convert speech to text.

refine_text: Uses OpenAI GPT to rewrite text (Grammar, Professional, Friendly).

mailer.py:

send_letter: Uploads PDF to PostGrid API.

send_tracking_email: Uses Resend to email tracking numbers.

letter_format.py: Generates PDFs. Handles font selection (Caveat for handwriting) and dynamic layouts (Santa vs Standard).

audit_engine.py: Logs critical events (Payment, API Failures) to audit_events table for debugging/refunds.

civic_engine.py: (Presumed) Lookups for government representatives based on user address.

bulk_engine.py: Parses CSV uploads for "Campaign" bulk mailing mode.

Utilities
analytics.py: Injects Google Analytics 4 tags.

seo_injector.py: Python script that modifies Streamlit's static index.html to add meta tags and NoScript content for SEO.

3. Database Schema (Postgres/SQLAlchemy)
Table: user_profiles

id, email, full_name

address_line1, address_line2, address_city, address_state, address_zip, country

language_preference

Table: letter_drafts

id, user_email, status (Draft/Completed/Pending Admin)

transcription (Body text)

recipient_json (JSON blob of To address)

sender_json (JSON blob of From address)

tier (Standard/Civic/Santa/Heirloom)

price, signature_data (Base64)

Table: audit_events

id, timestamp

user_email

stripe_session_id (The "Golden Thread" linking money to mail)

event_type (e.g., PAYMENT_VERIFIED, MAIL_API_FAILURE)

details (JSON blob of error traces or metadata)

Table: saved_contacts

Address book for returning users.

4. Required Secrets (.streamlit/secrets.toml)
DATABASE_URL (Supabase Postgres Connection Pool)

SUPABASE_URL / SUPABASE_KEY

STRIPE_SECRET_KEY

OPENAI_API_KEY

POSTGRID_API_KEY

RESEND_API_KEY (email.password)

ADMIN_EMAIL (for identifying Tarak)

5. Critical Workflows
The "Zombie Transaction" Fix: We track stripe_session_id in main.py upon return. We pass this ID to audit_engine.log_event. If mailing fails in ui_main.py, the error is logged against that Payment ID so refunds can be issued.

SEO Injection: seo_injector.py must run during the Docker build process, or Google will not index the site correctly.
