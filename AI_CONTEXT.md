VerbaPost 📮 (v2.8 Production)
URL: www.verbapost.com Status: Production Candidate Description: A voice-to-physical-mail platform. Users dictate letters via audio; AI transcribes and formats them; PostGrid prints and mails them via USPS First Class.

🏗️ Architecture & Tech Stack
	•	Frontend: Streamlit (Python)
	•	Database & Auth: Supabase (PostgreSQL + Auth)
	•	AI Engine: OpenAI Whisper (Transcription) + GPT-4o (Text Refinement)
	•	Payments: Stripe Checkout (with Tax calculation)
	•	Fulfillment: PostGrid (Print & Mail API + CASS Verification)
	•	Notifications: Resend (Transactional Email)
	•	Infrastructure: Docker / Streamlit Cloud

🛡️ Critical Safety Mechanisms (New in v2.8)
1. Address Hygiene & Verification
To prevent failed deliveries and returned mail:
	•	Pre-Signup Verification: ui_login.py calls mailer.verify_address_data before account creation.
	•	Standardization: Invalid addresses are rejected; typo-ridden addresses are auto-corrected to official USPS CASS standards (e.g., "123 main street" -> "123 MAIN ST").
	•	Sending Strictness: The mailer uses strict-but-accept-unknown mode to allow new construction addresses while blocking obvious fakes.
2. "Auto-Healing" Authentication
To prevent "User already registered" lockouts during database sync issues:
	•	Logic: If a signup fails because the email exists in Auth but is missing from the DB, auth_engine.py catches the error.
	•	Repair: It automatically logs the user in (verifying ownership) and force-creates the missing user_profiles row instantly.
3. "Zombie-Proof" Transactions
To prevent lost orders if a user closes their browser immediately after payment:
	•	Persistence: The draft_id is now written to the URL (?draft_id=xyz). If the user refreshes the page, the session state is restored.
	•	Audit: A Supabase Edge Function listens for Stripe webhooks to log PAYMENT_VERIFIED events independently of the browser.
4. Idempotency (Duplicate Prevention)
To prevent double-charging or double-mailing:
	•	Mechanism: mailer.py generates a SHA-256 hash of the letter content + address.
	•	Implementation: This hash is sent as the Idempotency-Key header to PostGrid. Repeated clicks of "Send" result in the same API response without creating a second letter.

🚀 Features
Core User Features
	•	Dictation: Browser-based audio recording and transcription.
	•	AI Magic Editor: Rewrites text for Grammar, Professionalism, or Conciseness.
	•	WYSIWYG Preview: Users can generate a PDF proof before mailing.
	•	Address Book: Saves contacts for repeat sending (Auto-standardized).
	•	Language Support: Profiles now store a language_preference for localized UI potential.
Admin Console (ui_admin.py)
	•	Order Management: View all drafts and statuses.
	•	Fix & Resubmit: Correct address typos (including Apt/Suite #) and re-trigger PostGrid API.
	•	Manual Fulfillment:
	◦	Santa Mode: Generate "North Pole" PDFs.
	◦	Heirloom Mode: Generate "Handwritten" font PDFs.
	•	Promo Code Manager: Create codes with strict usage limits (Database-enforced) via the new promo_codes table.
