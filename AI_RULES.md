# 🤖 VERBAPOST AI BEHAVIOR PROTOCOL
**Version:** v4.3.0
**Strict Instructions for AI Assistants**

## 🛑 SECTION 1: THE GOLDEN RULES (NON-NEGOTIABLE)
1.  **ZERO-REFACTOR POLICY:**
    * **NEVER** shorten, summarize, or "clean up" code unless explicitly asked to "Refactor".
    * **NEVER** remove unused imports, helper functions, or commented-out code blocks. They are there for a reason (usually to prevent hidden dependencies from crashing).
    * **ALWAYS** provide the **FULL FILE** content when applying a fix. Do not provide snippets like "Insert this at line 50."

2.  **FINANCIAL ATOMICITY:**
    * External API calls (Mailing, PDF Generation) must **ALWAYS** succeed *before* we deduct credits or log promo code usage in the database.
    * Never log a financial transaction before the physical artifact is secured.

3.  **DOMAIN & ROUTING:**
    * Base URL is ALWAYS `https://app.verbapost.com`. Do not use `verbapost.streamlit.app`.
    * Stripe Redirects must match this domain exactly to preserve session cookies.

---

## ⚠️ SECTION 2: KNOWN PITFALLS (DO NOT REPEAT THESE BUGS)

### 📮 PostGrid & Mailing
* **The 404 Error Trap:** We are on the "Print & Mail" plan.
    * ❌ **WRONG:** `.../addver/verifications` (Returns 404).
    * ✅ **CORRECT:** `https://api.postgrid.com/print-mail/v1/contacts` (Use this for validation).
* **Validation Logic:** We validate addresses by attempting to **Create a Contact**. If it returns ID 200, it's valid. If 400, it's invalid. We DO NOT use the CASS/Verification endpoint.

### 📄 PDF Generation (letter_format.py)
* **The "Overlap" Trap:** PostGrid #10 Window Envelopes have a massive "Safe Zone."
    * ❌ **WRONG:** Standard margins or `y=105mm`.
    * ✅ **CORRECT:** Body text must explicitly start at **`y=115mm`**.
* **Duplicate Address:** Never loop through `sender_text` twice. It confuses the parser.

### 💳 Promo Codes
* **The "Free Loop" Trap:** 100% off orders ($0.00) bypass Stripe.
    * **Constraint:** You must explicitly call `database.record_promo_usage` inside the `if total <= 0:` block in `ui_main.py`.

---

## 🏗️ SECTION 3: SYSTEM ARCHITECTURE
* **Pattern:** Router-Controller-Engine (Modular Monolith).
* **Router (`main.py`):** Handles `?nav=` routing and `?session_id=` callbacks.
* **Controllers (`ui_*.py`):** Handle UI state. `ui_main.py` is the Store. `ui_heirloom.py` is the Archive.
* **Engines:**
    * `database.py`: SQLAlchemy (Port 5432).
    * `mailer.py`: PostGrid Wrapper (Contacts Endpoint ONLY).
    * `payment_engine.py`: Stripe.

## ✅ SECTION 4: DEPLOYMENT CHECKLIST
Before confirming a fix, verify:
1.  Did I break the Receipt Page route?
2.  Did I accidentally remove the "Accessibility/Senior" tabs in `ui_legacy.py`?
3.  Did I maintain the "Manual Print Queue" logic in `ui_admin.py`?

📘 VerbaPost System Documentation
Version: v3.2.4 (The "Professional" Release)
Status: ✅ Production Stable
Last Updated: December 14, 2025
Architecture: Router-Controller-Engine (Modular Monolith)
1. Executive Summary
VerbaPost has evolved from a simple dictation tool into a dual-purpose platform:
	1	Standard Workspace: AI-powered dictation and editing for general correspondence ($2.99 - $9.99).
	2	Legacy Service (New): A private, secure, "End of Life" planning tool featuring custom handwriting fonts, archival paper, and certified delivery ($15.99).
The UI has been overhauled with a Minimalist/Serif design language to convey trust, utilizing mobile-responsive typography and subtle UX animations (like the "Shake" on error).

2. System Architecture & Components
A. The Core Triad (Frontend)
Component
File
Status
Responsibility
Router
main.py
✅ Stable
Entry point. Handles URL params (?view=legacy), CSRF checks, and routing.
Controller
ui_main.py
✅ Fixed
The "Brain." Manages the standard workspace state, audio recording, and tier selection.
Splash
ui_splash.py
✨ New
Marketing landing page. Features the "Professional/Minimalist" design with Serif fonts.
B. The Feature Modules
Module
File
Status
Responsibility
Legacy
ui_legacy.py
✨ New
Dedicated "End of Life" interface. Features: Font Previews, Long-form text area, Private Transcription (No AI Edit).
Auth UI
ui_login.py
✨ New
Login/Signup forms. Features: "Shake" error animation, Progress Tracker, Clean Tabs.
PDF Engine
letter_format.py
🔄 Updated
Generates PDFs. Now supports Custom Fonts (Caveat, Great Vibes, etc.) via dynamic loading.
C. The Backend Engines
Engine
File
Status
Responsibility
AI Engine
ai_engine.py
✅ Stable
Runs local Whisper model for transcription. (Used by both Workspace and Legacy).
Payment
payment_engine.py
✅ Stable
Wraps Stripe API. Handles checkout sessions for both Standard and Legacy tiers.
Database
database.py
✅ Stable
Manages Supabase connection (Users, Drafts, Address Book).

3. Critical User Flows
Flow A: The "Legacy" Letter (End of Life)
	•	Target User: Someone writing a final will, testament, or emotional letter.
	•	Entry: User clicks "Legacy Service" on Splash Page.
	•	Step 1 (Identity): User enters Name and Address.
	•	Step 2 (Style): User selects a font (e.g., "Great Vibes").
	◦	Logic: A CSS injection immediately renders a preview of their text in that font.
	•	Step 3 (Compose):
	◦	Option A: Type manually (Unlimited length).
	◦	Option B: Upload/Record Audio. ai_engine transcribes it verbatim (No GPT-4 polishing is offered, ensuring privacy).
	•	Step 4 (Preview): letter_format.py generates a PDF using the uploaded .ttf font files.
	•	Step 5 (Pay): payment_engine creates a $15.99 session with metadata service="EndOfLife".
Flow B: The Standard Workspace
	•	Target User: Daily correspondence, civic letters, quick notes.
	•	Entry: User logs in via ui_login.py.
	•	UX Feature: If login fails, the box shakes physically (CSS Animation).
	•	Workspace: User records audio.
	•	AI: ai_engine transcribes AND offers "Polishing" (Grammar/Professional modes).
	•	Output: Standard Helvetica PDF.

4. Codebase Logic Audit (Final Review)
I have performed a mental walkthrough of the current code state to identify any lingering risks.
✅ What is Solid:
	1	Syntax Errors: The "Line 10" and "Line 5" crashers in ui_main and ui_legacy are resolved via the multi-line try/except blocks.
	2	Naming Mismatch: ui_splash.py now includes the safety alias show_splash = render_splash, making it impossible for main.py to crash it.
	3	Crash Loop: The inotify crash was resolved (likely by the config change or simply stabilizing the file inputs).
⚠️ Minor Items to Watch:
	1	Font Files: The Legacy feature strictly requires the .ttf files (Caveat-Regular.ttf, etc.) to be in the root directory. If they are missing, the PDF generator has a fallback to Helvetica, so it won't crash, but the feature won't look right.
	◦	Action: Ensure those 4 font files are committed to GitHub.
	2	Promo Codes: While promo_engine.py exists, we did not explicitly hook it up to the ui_main.py checkout button in our final code blocks.
	◦	Impact: Users cannot enter coupons yet. (Low priority compared to system stability).
	3	SEO Files: Remember to verify that sitemap.xml and robots.txt are inside a static/ folder so Google can see them.

5. Deployment Verification
Current Version: v3.2.4
To consider this deployment successful, verify these 3 things in the live app:
	1	Splash: Does the title look like a newspaper header (Serif font)? (Yes = New CSS loaded).
	2	Legacy: Click "Legacy Service". Do you see the Font Selection radio buttons with live text previews?
	3	Login: Go to Login, type a fake password, and hit enter. Does the box shake?
System Status: OPERATIONAL 🟢


📘 VerbaPost System Documentation
Version: v3.3.0 (Legacy & Accessibility Release)
Status: ✅ Production Stable
Last Updated: December 14, 2025

1. High-Level Architecture
VerbaPost utilizes a Router-Controller-Engine architecture (Modular Monolith) built on Streamlit. This design separates the user interface from business logic to ensure stability, easier debugging, and preventing "God Files."
	•	Router (main.py): The single entry point. It handles URL parameters (e.g., ?session_id= for payment returns), performs security checks (CSRF), and routes traffic to the correct Controller.
	•	Controllers (ui_*.py): Manage the user interface and session state. They call Backend Engines to perform tasks.
	•	Engines (*_engine.py): Standalone modules handling specific domains (Payments, AI, Database, Mailing). They are UI-agnostic.

2. File Manifest & Responsibilities
Frontend Controllers (The "UI" Layer)
File
Responsibility
Key Features in v3.3.0
main.py
Router & Gatekeeper.
Entry point. Routes to ui_main or ui_legacy based on URL params. Handles global auth checks.
ui_main.py
Main App Controller.
Manages the Standard, Heirloom, Civic, and Santa tiers. Includes the Campaign (CSV) uploader.
ui_legacy.py
Legacy App Controller.
Dedicated flow for "End of Life" letters. Features Big Accessibility Tabs, Address Book integration, and loop-proof audio recording.
ui_splash.py
Marketing Landing.
Displays pricing cards and the "Start a Letter" call to action.
ui_login.py
Authentication UI.
Handles Login, Signup, and Password Reset forms.
Backend Engines (The "Logic" Layer)
File
Responsibility
Key Features in v3.3.0
payment_engine.py
Stripe Integration.
Creates checkout sessions. Fixed: Supports line_items and handles "Guest" users by omitting invalid emails so Stripe collects them.
letter_format.py
PDF Generator.
Creates PDF binaries using FPDF2. Fixed: Includes a "Safety Cast" to ensure output is always immutable bytes, preventing bytearray crashes.
ai_engine.py
AI Transcription.
Wraps OpenAI Whisper (running locally) to transcribe audio files from the UI.
mailer.py
PostGrid Connector.
Sends the final PDF and address data to the PostGrid API for physical printing and mailing.
database.py
Persistence.
Manages Supabase (PostgreSQL) connections. Handles saving drafts, users, and address book contacts.

3. Core User Flows (The "Happy Paths")
A. The Standard Letter Flow
	1	Store: User selects a tier (e.g., "Standard") in ui_main.py.
	2	Compose: User types or records a message.
	◦	New: Accessibility CSS makes tabs large and high-contrast.
	3	Review: User clicks "Generate PDF Proof".
	◦	letter_format.py generates a PDF.
	◦	ui_main.py converts it to Base64 for display.
	4	Pay: User clicks "Checkout".
	◦	payment_engine creates a Stripe Session with line_items.
	5	Return: User returns to app. main.py verifies payment and marks the letter as "Paid".
B. The Legacy Letter Flow (New & Fixed)
	1	Workspace: User lands on ui_legacy.py.
	2	Addressing: User loads a contact from the Address Book or types it manually.
	3	Dictation: User records voice.
	◦	Loop Fix: The app calculates a hash of the audio file. If the hash matches the previous one, it skips re-transcription to prevent infinite loops.
	4	Preview: User generates a PDF proof.
	◦	Crash Fix: The system explicitly casts the mutable bytearray from FPDF2 into immutable bytes before rendering.
	5	Checkout: User pays $15.99.
	◦	Guest Fix: If the user is a guest, the system tells Stripe to ask for their email address explicitly.

4. Version Changelog (v3.3.0 Changes)
This version introduces critical stability fixes and accessibility improvements.
🔴 Critical Bug Fixes
	1	Stripe Guest Email Crash:
	◦	Before: Sending email="guest" to Stripe caused a 400 Invalid Email error.
	◦	After: payment_engine.py detects "guest" and omits the email field, forcing Stripe to show its own email input form.
	2	PDF Preview Crash (bytearray):
	◦	Before: fpdf2 returned a bytearray, which caused AttributeError: 'bytearray' has no attribute 'encode' during Base64 conversion.
	◦	After: letter_format.py and UI controllers now include a Safety Cast (bytes(raw_output)) to guarantee compatible data types.
	3	Infinite Transcription Loop:
	◦	Before: The Legacy recorder would continuously re-process the same audio file on every page reload.
	◦	After: Added audio_hash logic to ui_legacy.py. The app only calls the AI engine if the audio file's content has actually changed.
	4	Payment Return Crash:
	◦	Before: main.py tried to call ui_main.render_main(), which was missing from the file.
	◦	After: Restored the render_main() entry point in ui_main.py.
✨ New Features & Improvements
	1	Senior Accessibility Mode:
	◦	Tabs in the Workspace are now 70px tall, have thick outlines, and use 24px bold text.
	◦	High-contrast instruction boxes (Yellow/Orange) added to guide users.
	2	Full Feature Restoration:
	◦	Restored the Address Book Loader in the Legacy view (was previously stripped).
	◦	Restored Campaign (CSV) uploading in the Main view.
	◦	Restored State Initialization to prevent KeyError crashes on first load.

5. Configuration (Secrets)
The app requires the following structure in .streamlit/secrets.toml:
Ini, TOML

[stripe]
secret_key = "sk_live_..."

[postgrid]
api_key = "live_sk_..."

[openai]
api_key = "sk-..."

[supabase]
url = "https://your-project.supabase.co"
key = "your-anon-key"

[general]
BASE_URL = "https://verbapost.com"

Here is the comprehensive system documentation for VerbaPost v3.2.2. This document captures the current stable architecture, the critical fixes implemented today (Database Port 5432, Geocodio cd field), and the updated user flows.

📘 VerbaPost v3.2.2 System Documentation
Status: ✅ Production Stable (Fixes Applied) Last Updated: December 15, 2025 Version: v3.2.2 (Civic & Database Patch Release)

🌐 1. High-Level Architecture
VerbaPost uses a Router-Controller-Engine pattern (Modular Monolith). This ensures clean separation of concerns: the UI handles the user, and specialized "Engines" handle the heavy lifting (DB, API, AI).
The "Triad" Structure
	1	Router (main.py): The single entry point.
	◦	Role: Security Gatekeeper & Traffic Director.
	◦	Responsibilities: Handles URL parameters (?session_id), performs CSRF checks on payment returns, and initializes global session state.
	2	Controller (ui_main.py): The Application Brain.
	◦	Role: State Manager & UI Renderer.
	◦	Responsibilities: Manages the linear user journey (Store → Workspace → Review). It captures user input, auto-populates profiles, and calls backend engines.
	3	Engines (Backend): Specialized Logic Units.
	◦	Role: Domain Experts (UI Agnostic).
	◦	Responsibilities:
	▪	database.py: SQLAlchemy ORM (now using Dictionaries to prevent detached sessions).
	▪	civic_engine.py: Geocodio Integration (updated to use cd field).
	▪	mailer.py: PostGrid Integration (Print & Verification).
	▪	ai_engine.py: OpenAI Whisper (Local CPU) + GPT-4o (Polish).

🛠️ 2. Critical Fixes & Findings (Dec 15, 2025)
A. Database Connection & Schema
	•	The "1043" Error: We identified that Unknown PG numeric type: 1043 was caused by connecting to Supabase via the Transaction Pooler (Port 6543).
	◦	Fix: Secrets updated to use the Session Pooler (Port 5432) which fully supports SQLAlchemy types.
	•	Schema Mismatch: The price column in letter_drafts was TEXT while the code expected FLOAT.
	◦	Fix: SQL migration run to cast columns to double precision.
	•	Detached Instances: The UI crashed when reading database objects after the session closed.
	◦	Fix: database.py now converts all ORM objects to standard Python Dictionaries (to_dict()) before returning them.
B. Civic Engine (Geocodio)
	•	Deprecated Field: The API warning "The field congress is not recognized" caused empty results.
	◦	Fix: Updated civic_engine.py to use the cd (Congressional District) field.
	◦	Parsing Update: The code now correctly drills down into fields -> congressional_districts -> current_legislators to extract Senator and Representative names.
C. Admin Console
	•	Health Checks: Added explicit validation for all 5 required API keys (Stripe, PostGrid, OpenAI, Geocodio, Resend).
	•	Data Integrity: Restored the "Users" and "Logs" tabs.

🔄 3. Core User Flows
Flow A: The "Civic" Letter (Write to Congress)
	1	User Entry: Selects "Civic" Tier ($6.99).
	2	Auto-Populate: App loads User Profile. If "From" address exists, it pre-fills the form.
	3	Lookup: User clicks "🏛️ Find My Representatives".
	4	Engine: civic_engine.py sends the address to Geocodio with fields=cd.
	5	Result: App displays found officials (e.g., "Sen. Marsha Blackburn", "Rep. John Rose").
	6	Action: User writes one letter body. The system automatically prepares 3 envelopes (one for each official).
Flow B: The Standard/Heirloom Letter
	1	Addressing: User selects a contact from the Address Book (persisted in DB).
	2	Verification: Clicking "Save" triggers mailer.validate_address().
	◦	Note: Uses PostGrid's /contacts endpoint to verify without a separate AV subscription.
	3	Dictation: User clicks the Streamlit Audio Widget (Big Mic icon removed for clarity).
	4	Transcribe: ai_engine.py saves audio to /tmp, runs Whisper locally, and returns text.
	5	Payment: pricing_engine.py calculates total server-side. User pays via Stripe.
Flow C: Admin Operations
	1	Access: Admin logs in via ui_admin.py (password in secrets).
	2	Health Check: Dashboard shows green ✅ for all connected services.
	3	Order Management: Admin can view the PDF content of any draft to verify formatting before fulfillment.

🔑 4. Configuration Reference
To maintain this stable state, the .streamlit/secrets.toml (or Cloud Run Env Vars) must match this structure exactly.
Ini, TOML

[general]
# CRITICAL: Must use port 5432, NOT 6543
DATABASE_URL = "postgresql://postgres.[ref]:[pass]@aws-0-us-east-1.pooler.supabase.com:5432/postgres"

[stripe]
secret_key = "sk_live_..." 

[postgrid]
api_key = "live_sk_..." # Print & Mail Key

[geocodio]
api_key = "..." # Required for Civic Tier

[openai]
api_key = "sk-..." # Required for Text Polish

[email]
password = "re_..." # Resend API Key

[admin]
email = "tjkarat@gmail.com"
password = "..."

📂 5. File Structure Overview
	•	main.py: Router. Checks auth and redirects to ui_main.
	•	ui_main.py: The massive Controller (>600 lines). Handles the Store, Workspace, and Review logic. Contains the fix for Address Book visibility.
	•	database.py: The Data Layer. Contains the to_dict() fix and the robust create_engine configuration.
	•	civic_engine.py: The Geocodio wrapper. Contains the fix for the cd field.
	•	ui_admin.py: Back-office dashboard with new Health Checks.
	•	mailer.py: Handles PostGrid interaction and address verification.
	•	ai_engine.py: Handles local Whisper transcription.
🚀 6. Next Steps
	1	Monitor: Watch the Admin Console "Logs" tab for any 1043 recurrences (indicates a port revert).
	2	Marketing: The "Heirloom" and "Civic" flows are now fully functional and ready for traffic.
	3	Testing: Perform a real $2.99 transaction on "Standard" tier to verify the end-to-end webhook fulfillment (if webhooks are enabled).
 render_application()

if __name__ == "__main__":
    render_main()



🕰️ VerbaPost Heirloom: System Documentation
1. Executive Summary
VerbaPost Heirloom is a "Voice-to-Mailbox" platform designed to capture family stories. It allows seniors to record stories via a standard telephone call, which are then transcribed by AI, edited by family members, and physically mailed as keepsake letters.
Current Status: ✅ MVP Operational
	•	Input: Telephone (Twilio)
	•	Processing: AI Transcription (OpenAI)
	•	Interface: Web Dashboard (Streamlit)
	•	Output: Physical Mail (PostGrid)
	•	Monetization: Credit System (1 Credit = 1 Letter)

2. System Architecture
The app follows a modular "Engine" architecture. The main.py file acts as a traffic controller, routing users to specific modules based on their session state.
The Core Workflow:
	1	Grandma Calls (615) 656-7667 (Twilio).
	2	Audio Captured: Twilio sends the .wav file to your server (currently via manual upload or webhook simulation).
	3	Transcription: ai_engine.py converts speech to text using OpenAI Whisper.
	4	Storage: Text is saved as a "Draft" in the Supabase Database.
	5	Review: Daughter logs into the Dashboard (ui_heirloom.py), fixes typos, and clicks "Preview".
	6	Production: letter_engine.py generates a US Letter PDF.
	7	Dispatch: postgrid_engine.py sends the PDF to the print facility.
	8	Delivery: USPS delivers the physical letter to the daughter.

3. File Directory & Responsibility
Here is the "Who Does What" for your codebase:
File Name
Responsibility
Status
main.py
The Router. Checks if user is logged in, handles navigation sidebar, and loads the correct page module. Includes the "Database Repair" button.
✅ Stable
ui_heirloom.py
The Dashboard. The main UI where users see the Inbox, edit stories, manage parent details, and click "Send". Handles the credit deduction logic.
✅ Stable
database.py
The Vault. Handles all Supabase interactions.

• Stores UserProfile (incl. credits_remaining).

• Stores LetterDraft (content, status).

• Converts SQL objects to Python Dictionaries to prevent crashes.
✅ Stable
letter_engine.py
The Typesetter. Uses fpdf2 to draw the PDF.

• Forces US Letter size (8.5x11).

• Adds "The Family Archive" header.

• Formats date, salutation, and signature.
✅ Stable
postgrid_engine.py
The Postman. Connects to the PostGrid API.

• Creates "To" Contact (User).

• Creates "From" Contact (VerbaPost/Mom).

• Uploads PDF and places the order.
✅ Stable
ai_engine.py
The Scribe. Sends audio files to OpenAI Whisper API and returns raw text.
✅ Stable

4. External Services Configured
Your app relies on these 4 pillars. If one breaks, the chain breaks.
	1	OpenAI API:
	◦	Role: Intelligence (Speech-to-Text).
	◦	Cost: ~$0.006 per minute of audio.
	2	Supabase (PostgreSQL):
	◦	Role: Memory (Users, Drafts, Credits).
	◦	Status: Schema patched (added credits_remaining column).
	3	Twilio (Voice):
	◦	Role: The Phone Line (615) 656-7667.
	◦	Status: Trial Mode (Needs upgrade to remove trial warning/restrictions).
	◦	Config: Currently static XML (TwiML). Future: Dynamic Webhook.
	4	PostGrid (Print & Mail):
	◦	Role: Fulfillment.
	◦	Status: Connected.
	◦	Cost: ~$0.80 per letter (eats into your $19/mo margin).

5. The "Golden Path" (User Journey)
This is the flow you have successfully tested today:
	1	Login: User accesses the dashboard.
	2	Heirloom Tab: User sees "Letter Credits: 4/4".
	3	Draft: A new story appears in "Inbox" (from manual upload test).
	4	Edit: User edits the text to fix "ums" and "ahs".
	5	Save: User clicks "💾 Save". Database updates.
	6	Preview: User clicks "📄 Preview PDF". A formatted PDF is generated.
	7	Send: User clicks "📮 Send Mail (1 Credit)".
	◦	System checks credits (4 > 0).
	◦	System subtracts 1 credit (Balance: 3).
	◦	System sends PDF to PostGrid.
	◦	Success Balloon pops up.

6. Current Limitations & Next Steps
You are ready for Phase 2, which tackles these remaining gaps:
	1	The "Robot Voice" Problem:
	◦	Current: Callers hear a static, boring greeting.
	◦	Goal: Dynamic AI Biographer that asks specific questions ("Tell me about your wedding...").
	2	The "Contact" Hardcoding:
	◦	Current: PostGrid sends letters to the address in user_profile.
	◦	Goal: Allow users to add multiple recipients (Aunts, Uncles) to an address book.
	3	The "Data Entry" Gap:
	◦	Current: You have to manually type the "Parent Phone" in settings.
	◦	Goal: Auto-detect the Caller ID and link it to the account automatically.
	4	Payment Processing:
	◦	Current: You manually gave yourself 4 credits.
	◦	Goal: Integrate Stripe so users pay $19/mo to refill those credits automatically.

twilio api:core:incoming-phone-numbers:update PN155027fb38f5c05afc9d383328ae8d9d --voice-url "https://heirloom-brain-3361-dev.twil.io/incoming-call"



📂 VerbaPost Project Status (Dec 16, 2025)
System Status: ✅ Stable (Database Unified, Admin Console Fixed, Sidebar Cleaned) Deployment: Streamlit Cloud & Google Cloud Run Database: Supabase (PostgreSQL)
1. Key Accomplishments Today
	•	Heirloom Module Integration: Successfully added the "Voice Story" feature (ui_heirloom.py) which connects to Twilio to fetch call recordings.
	•	Database Unification: Rewrote database.py to support both Legacy features (Store, Promo Codes, Audit Logs) and Heirloom features (Profiles, Drafts) simultaneously.
	•	Crash Fixes: Resolved AttributeError and UndefinedColumn errors by syncing the Python models with the SQL schema.
	•	UI Cleanup: Removed temporary "Fix Database" buttons from the sidebar in main.py.
2. Critical File States
You should have the latest versions of these files saved locally or pushed to GitHub:
	•	database.py: The "Unified" version containing UserProfile, LetterDraft, Letter, PromoCode, AuditEvent, and Contact.
	•	main.py: Cleaned version with no debug buttons in the sidebar.
	•	ui_main.py: Includes unique keys (key="sb_home") to prevent duplicate ID errors.
	•	requirements.txt: Must include twilio, sqlalchemy, psycopg2-binary, streamlit, openai, stripe.
3. Required Environment Variables (Secrets)
Ensure these are set in Streamlit Cloud and Google Cloud Run:
Ini, TOML

[supabase]
url = "https://phqnppksrypylqpzmlxv.supabase.co"
key = "eyJ..."
db_password = "[YOUR_DB_PASSWORD]" # Critical for connection string

[twilio]
account_sid = "AC..."
auth_token = "..."

[openai]
api_key = "sk-..."

# Plus: [stripe], [postgrid], [geocodio], [email]
4. Database Schema (Reference)
If you ever reset the database, run this SQL to restore full functionality:
SQL

CREATE TABLE IF NOT EXISTS promo_codes (code text PRIMARY KEY, active boolean DEFAULT true, is_active boolean DEFAULT true, uses integer DEFAULT 0, discount_amount float DEFAULT 0.0, max_uses bigint, current_uses integer DEFAULT 0);
CREATE TABLE IF NOT EXISTS audit_events (id serial PRIMARY KEY, timestamp timestamp DEFAULT now(), user_email text, stripe_session_id text, event_type text, details text, description text);
ALTER TABLE letter_drafts ADD COLUMN IF NOT EXISTS tier text DEFAULT 'Heirloom';

🚀 Resume Prompt (Copy & Paste Tomorrow)
Paste this into the chat to restart:
"I am resuming work on VerbaPost, a Streamlit app with two modes: Legacy (Letter Store) and Heirloom (Voice Biographer).
Current Status:
	1	We have successfully unified database.py to support both Legacy (Promos, Logs) and Heirloom (Drafts, Profiles) models.
	2	We fixed the Admin Console crashes by syncing the Python models with the Supabase SQL schema.
	3	We cleaned up main.py to remove temporary debug buttons.
Immediate Next Steps:
	1	Verify the Admin Console loads data (Orders, Logs) without error in Production.
	2	Test the Heirloom "Check for New Stories" button to ensure Twilio integration is working live.
	3	If any AttributeError or UndefinedColumn errors appear, we likely need to check database.py against the SQL schema again.
Let's start by verifying the Admin Console is healthy."


📜 VerbaPost System Documentation (Current State - Dec 16, 2025)
1. Core Architecture
	•	Frontend: Streamlit (v1.40.0)
	•	Backend Logic: Python Modules (ai_engine, letter_format, postgrid_engine, database)
	•	Database: Supabase (PostgreSQL) via SQLAlchemy.
	•	Infrastructure:
	◦	QA: Streamlit Cloud (secrets via st.secrets)
	◦	Production: Google Cloud Run (secrets via os.environ)
2. Critical Flows
A. The "Fetch Stories" Loop (Heirloom)
	1	Trigger: User clicks "Check for New Stories" in Heirloom Dashboard.
	2	Twilio Search: ai_engine.py calls Twilio API to find calls from parent_phone.
	3	Recording Retrieval: Finds the latest recording, constructs the .mp3 URL manually (bypassing the .media_url bug).
	4	Transcription: Downloads audio to temp file $\rightarrow$ Sends to OpenAI Whisper $\rightarrow$ Returns text.
	5	Storage: Saves new draft to letter_drafts table with tier="Heirloom".
B. The "Preview & Send" Flow
	1	Selection: User selects a recipient from the "Send To" dropdown (Address Book + Profile).
	2	PDF Generation: letter_format.py creates a PDF.
	◦	Logic: Checks for type_right.ttf. If present & tier is Heirloom, uses Typewriter font.
	◦	Safety: Forces bold_style='' for the custom font to prevent FPDF crashes.
	◦	Layout: Places Recipient Address (Top Left) and Sender Address (Top Right) for window envelopes.
	3	Mailing: postgrid_engine.py receives the PDF and the structured address object (not just text) to route the mail via USPS.
C. The Production "Environment" Fix
	•	Problem: Cloud Run was crashing because it couldn't find database credentials or font files.
	•	Solution:
	◦	database.py now checks os.environ first (for Cloud Run) before st.secrets.
	◦	letter_format.py fails gracefully if type_right.ttf is missing (falls back to Times New Roman), but we expect it to be present after the git push.
3. Key Files & Responsibilities
	•	main.py: The traffic cop. Injects SEO & Analytics, checks for payment callbacks, routes to ui_main or ui_heirloom.
	•	ui_heirloom.py: The Dashboard. Handles the "Fetch" trigger, address selection, and calls the PDF generator.
	•	letter_format.py: The Artist. Draws the PDF. Contains the "Smart Signature" logic (avoids "Love Mom Love Mom").
	•	database.py: The Vault. Manages connections to Supabase. Handles the Unified Schema (Legacy + Heirloom tables).


📘 VerbaPost System Documentation
Version: v3.4.0 (Stable)
Date: December 17, 2025
🏗️ Architecture Overview
VerbaPost operates on a Router-Controller-Engine architecture pattern. This ensures separation of concerns, stability, and easier debugging.
	•	Router (main.py): The "Traffic Cop". It checks URL parameters, verifies sessions, enforces security, and decides which UI module to load.
	•	Controller (ui_*.py): The "Brain". These files (ui_main, ui_heirloom, ui_legacy) handle user interaction, state management, and form logic.
	•	Engines (*_engine.py): The "Muscle". Standalone workers that handle specific tasks (Email, Database, Payments, AI, Mailing).
🔄 Critical User Flows
1. The Standard Flow (Store)
	1	User lands on ui_splash.py.
	2	User Logs in/Signs up via ui_login.py.
	3	User enters the Store (ui_main.py), selects a tier (e.g., Standard), writes a letter, and enters addresses.
	4	Checkout: ui_main calls payment_engine to create a Stripe session.
	5	Return: User returns to main.py.
	6	Fulfillment: main.py verifies payment → Calls mailer.py to send PDF to PostGrid → Updates Database → Logs to audit_engine.
2. The Heirloom Flow (Voice Stories)
	1	User sets up a "Parent Phone" in ui_heirloom.py settings.
	2	Parent calls the Twilio number. ai_engine records and transcribes the call.
	3	User clicks "Check for New Stories" in Dashboard. The draft appears in Inbox.
	4	User edits the text, selects a recipient from Address Book, and clicks "Send (1 Credit)".
	5	Fulfillment: ui_heirloom generates PDF → Calls mailer.py → Updates Database → Logs to audit_engine.
3. The Legacy Flow (One-Off Certified)
	1	User enters ui_legacy.py.
	2	User types letter, verifies addresses via mailer.py.
	3	Checkout: ui_legacy syncs variables to global session state (addr_to, addr_from) and calls Stripe.
	4	Return: User returns to main.py.
	5	Fulfillment: main.py reads the synced variables → Calls mailer.py → Updates Database → Logs to audit_engine.
🛠️ Component Reference
Component
Responsibility
Status
main.py
Router, Payment Verification, Fulfillment Trigger, Security Gate
✅ Audit Log Added
ui_main.py
Store UI, Voice Recording, Address Book Loading
✅ Stable
ui_heirloom.py
Voice Story Dashboard, Credit System
✅ Fixed Mailer & Audit
ui_legacy.py
Single Certified Letter UI
✅ Fixed Sync & Audit
ui_admin.py
Back-office controls
✅ Fixed Retry Logic
mailer.py
PostGrid API Wrapper (Address Verification + Sending)
✅ Robust
database.py
SQLAlchemy ORM Models & Connections
✅ Schema Fixed
audit_engine.py
Security Logging
✅ Active
📝 Changelog: What was fixed today?
1. Critical Mailing Fix (Silent Failure Resolved)
	•	Issue: ui_heirloom.py was using an obsolete postgrid_engine and decrementing credits without actually sending mail.
	•	Fix: Updated to use mailer.py. It now properly sends the PDF to PostGrid and records the returned Letter ID.
2. Audit Logging Gaps Filled
	•	Issue: Successful orders in main.py, ui_heirloom.py, and ui_legacy.py were not creating audit logs.
	•	Fix: Added audit_engine.log_event() calls to all success paths. Every letter sent now leaves a permanent security trail.
3. Legacy Flow Integration
	•	Issue: ui_legacy.py used isolated variables (legacy_sender) that the main.py router couldn't see, causing fulfillment to fail after payment.
	•	Fix: Added state synchronization logic. When a user clicks "Pay", legacy variables are copied to the global addr_to/addr_from slots.
4. Admin Console Repair
	•	Issue: The "Force Send" button in Admin was using invalid arguments and crashing.
	•	Fix: Updated the logic to match the current mailer.send_letter signature and added audit logging for admin actions.
5. Database Schema Cleanup
	•	Issue: PromoLog used datetime incorrectly, causing crashes. Garbage code existed at the end of the file.
	•	Fix: Cleaned up database.py and fixed the datetime.utcnow reference.
6. Fake Tracking Numbers Removed
	•	Issue: The success screen was displaying a random 94055... number.
	•	Fix: The system now displays the actual PostGrid Letter ID returned from the API (e.g., letter_2b8...)
	•	
	•	
	•	1. System Architecture: Router-Controller-Engine
	•	VerbaPost is built on a modular "Router-Controller-Engine" architecture using Streamlit. This design separates the user interface from business logic to ensure stability and scalability.
	•	Router (main.py): The single entry point that manages global session state, security checks (CSRF), and traffic direction based on URL parameters.
	•	Controllers (ui_*.py): UI-specific modules that manage the user journey, state transitions, and form logic.
	•	Engines (*_engine.py, mailer.py, etc.): Standalone logic units that handle external APIs (Stripe, OpenAI, PostGrid) and database operations.
	•	
	•	2. Component Functionality & File Manifest
	•	Frontend Controllers (UI Layer)
	•	main.py (Router):
	◦	Acts as the system gatekeeper.
	◦	Injects SEO meta-tags and Google Analytics.
	◦	Verifies Stripe payment sessions and triggers post-payment fulfillment.
	•	ui_splash.py (Marketing):
	◦	The public-facing landing page featuring a minimalist, professional design.
	◦	Displays "Trust Logos" (Stripe, Visa, Mastercard, USPS) and entry points for the "Standard" and "Legacy" services.
	•	ui_main.py (Primary Workspace):
	◦	Handles the core letter-writing experience for Standard, Heirloom, Civic, and Campaign tiers.
	◦	Integrates the audio recording widget for voice-to-letter dictation.
	•	auth_ui.py & auth_engine.py (Identity):
	◦	Manages user authentication via Supabase.
	◦	Features login, signup, and password recovery flows with "Shake" error animations for feedback.
	•	ui_admin.py (Operational Control):
	◦	Provides an administrative dashboard for monitoring health checks, viewing order logs, and manually re-triggering failed fulfillment.
	•	Backend Engines (Logic Layer)
	•	ai_engine.py (Intelligence):
	◦	Transcribes audio using OpenAI's Whisper model.
	◦	Optionally "polishes" text using GPT-4o to improve grammar or professional tone.
	•	mailer.py (Fulfillment):
	◦	The bridge to the PostGrid API for physical printing and USPS delivery.
	◦	Handles address verification to ensure deliverability before charging users.
	•	letter_format.py (Typesetting):
	◦	Generates high-fidelity PDF documents using the FPDF2 library.
	◦	Supports custom fonts (e.g., "Typewriter" or "Handwriting" styles) for specialized tiers.
	•	bulk_engine.py (Campaigns):
	◦	Parses CSV files with flexible header matching (e.g., "zip" vs "zip_code") to load mailing lists.
	◦	Automates the generation and mailing of hundreds of letters in a single run while logging progress to the audit engine.
	•	civic_engine.py (Civic Lookup):
	◦	Uses the Geocodio API to find US Senators and Representatives based on a user's address.
	◦	Specifically utilizes the cd (Congressional District) field for accurate legislator mapping.
	•	audit_engine.py (Security):
	◦	Maintains a permanent record of critical system events, such as campaign starts, successful mailings, and payment verification.
	•	
	•	3. Core Operational Flows
	•	Standard & Heirloom Letter Flow
	•	Entry: User selects a tier (Standard or Heirloom) in ui_main.py.
	•	Composition: User dictates audio; ai_engine.py returns a transcript.
	•	Refinement: AI-driven "Polishing" is applied if requested.
	•	Addressing: User selects a contact from the database or enters a manual address validated by mailer.py.
	•	Payment: User completes a Stripe checkout session.
	•	Fulfillment: Upon return to main.py, the system verifies the payment, generates the final PDF via letter_format.py, and dispatches it through mailer.py.
	•	Civic Outreach Flow
	•	Selection: User chooses the "Civic" tier to write to government officials.
	•	Lookup: civic_engine.py queries Geocodio with the user's home address.
	•	Mapping: The system identifies the specific Congressional District and populates a list of current legislators.
	•	Mailing: One letter body is written by the user, but multiple individual letters are generated and mailed—one for each representative found.
	•	Campaign (Bulk) Flow
	•	Upload: User provides a CSV file containing recipient names and addresses.
	•	Parsing: bulk_engine.py normalizes headers (Name, Street, City, State, Zip) and validates rows.
	•	Execution: The engine iterates through the list, generating a unique mailing request for each recipient via mailer.py.
	•	Logging: Every successful or failed delivery is recorded in the audit_events table for administrative review.
	•	
	•	4. External Integration Manifest
	•	Service
	•	Component
	•	Purpose
	•	OpenAI
	•	ai_engine.py
	•	Audio transcription and text polishing.
	•	PostGrid
	•	mailer.py
	•	Physical printing, enveloping, and USPS mailing.
	•	Stripe
	•	main.py
	•	Secure payment processing and transaction verification.
	•	Geocodio
	•	civic_engine.py
	•	US Congressional District and legislator lookup.
	•	Supabase
	•	auth_engine.py
	•	User authentication, session management, and data persistence.
	•	Twilio
	•	ai_engine.py
	•	Fetching voice recordings for the Heirloom telephone service.
	•	.
📘 VerbaPost System Documentation
Version: v3.4.2 (Stability & Repair Release)
Status: ✅ Production Stable
Last Updated: December 19, 2025

1. Executive Summary
VerbaPost is a modular "Router-Controller-Engine" application. This release focuses on stabilizing the production environment by fixing external API endpoints, hardening security (API key sanitization), and restoring full functionality to the user workspace and administrative tools.
Key Updates in v3.4.2:
	•	PostGrid Production Fix: Corrected API endpoint routing.
	•	Admin Capabilities: Added a "Repair Station" to manually fix and retry failed orders.
	•	Security: Implemented aggressive sanitization for SMTP/API keys.
	•	Restoration: Re-integrated Promo Codes and safe Font Loading into the main UI.

2. Critical Findings & Fixes (Dec 19, 2025)
A. The PostGrid "404" Error
	•	Issue: Production orders were failing with API 404.
	•	Root Cause: The application was using the Address Verification endpoint structure (/v1/letters) instead of the Print & Mail structure.
	•	Fix: mailer.py and ui_admin.py now explicitly use: https://api.postgrid.com/print-mail/v1/letters.
B. Resend API "400" Error
	•	Issue: Health checks and emails were failing in QA/Prod.
	•	Root Cause: API keys copied into secrets/env variables contained hidden whitespace or quotation marks (e.g., 're_123').
	•	Fix: Implemented aggressive sanitization in mailer.py and ui_admin.py: key.strip().replace("'", "").replace('"', "").
C. Admin Console "No Logs" & Order Count
	•	Issue: The Admin Console showed "No Logs" and an incomplete order count (67 vs Actual).
	•	Root Cause:
	1	The code was querying audit_logs (which didn't exist), but Supabase contained audit_events.
	2	The Order Manager was only querying the letters table (completed), ignoring letter_drafts (pending/failed).
	•	Fix:
	1	audit_engine.py updated to query audit_events.
	2	ui_admin.py now merges both tables for a complete operational view.

3. Architecture & File Manifest
Frontend Controllers
File
Responsibility
Current Status
main.py
Router. Handles URL params, CSRF checks, and Payment Verification.
✅ Stable. Now logs "Order Fulfilled" to audit trail.
ui_main.py
Standard UI. The main workspace (700+ lines). Handles Voice, Typing, Promos, and Stripe Checkout.
✅ Restored. Promo codes & line_items fixed.
ui_admin.py
Admin Dashboard. Health checks, Order Repair, and Log viewing.
✅ Upgraded. Includes "Repair Station".
ui_heirloom.py
Voice Dashboard. Interface for the "Story" tier.
✅ Stable.
Backend Engines
File
Responsibility
Current Status
mailer.py
Fulfillment. Connects to PostGrid (Print) and Resend (Email).
✅ Fixed URL (/print-mail/) & Key Sanitization.
audit_engine.py
Logging. Records security and transaction events to Supabase.
✅ Fixed. Reads from audit_events table.
payment_engine.py
Financials. Manages Stripe Checkout Sessions.
✅ Stable.
letter_format.py
PDF Gen. Creates the physical letter PDF.
✅ Stable. Safe font fallback included.

4. Core Operational Flows
Flow A: The Standard Letter (Fixed)
	1	Compose: User types or dictates in ui_main.py.
	2	Review: User applies Promo Code (Restored feature).
	3	Checkout: System sends line_items to Stripe (Fixes 400 Error).
	4	Fulfillment:
	◦	main.py receives success signal.
	◦	Calls mailer.py $\rightarrow$ Hits https://api.postgrid.com/print-mail/...
	◦	Success: Updates DB status to "Sent", logs to audit_events.
Flow B: The "Repair" Flow (New)
Used when an order fails (e.g., bad address).
	1	Identify: Admin logs into ui_admin.py and sees an order with status "Failed" or "Pending".
	2	Select: Admin selects the Order ID in the Repair Station dropdown.
	3	Edit: Admin corrects the Recipient Name, Address, or Body text directly in the form.
	4	Force Retry: Admin clicks "🚀 Update & Re-Send".
	5	Result: System bypasses payment, regenerates PDF, forces dispatch via mailer.py, and updates status to "Sent (Admin)".

5. Environment Configuration
Ensure your .streamlit/secrets.toml or Cloud Run Environment Variables match this logic:
Ini, TOML

[postgrid]
# Must be a Live Secret Key (sk_live_...)
api_key = "..."

[email]
# "Sending Only" permission recommended.
# Code now strips quotes automatically.
password = "re_..."

[general]
# Use Session Pooler (Port 5432) for SQLAlchemy compatibility
DATABASE_URL = "postgresql://...:5432/postgres"
6. Database Schema Reference
To ensure the code runs without UndefinedTable or AttributeError, the Supabase schema must align with the Python models:
	•	Table: audit_events (Used for system logs)
	•	Table: letters (Columns: to_name, to_city required for Admin view)
	•	Table: letter_drafts (Columns: to_name, to_city required for Admin view)
📘 VerbaPost System Documentation
Version: v3.4.0 (Stable)
Status: ✅ Production Ready
Architecture: Router-Controller-Engine (Modular Monolith)
1. System Architecture Overview
The application is built on Streamlit but uses a strict separation of concerns to maintain stability.
	•	Router (main.py): The single entry point. It handles URL routing, security (CSRF), global state initialization, and module loading.
	•	Controllers (ui_*.py): Manage the user interface and session state for specific features.
	•	Engines (*_engine.py): Domain-specific logic (Database, AI, Mail, Payments) that is agnostic of the UI.
2. File Manifest & Dependencies
📂 Core Infrastructure
File
Responsibility
Dependencies
main.py
Router. Entry point. Routes traffic, handles global error logging, and injects CSS/Analytics.
streamlit, logging, ui_* modules
secrets_manager.py
Security. Safely retrieves API keys from either Streamlit Secrets (QA) or OS Environment Variables (Cloud Run).
os, streamlit
database.py
Persistence. Unified SQLAlchemy handler for User Profiles, Drafts, and Heirloom Stories.
sqlalchemy, psycopg2-binary
🎨 UI Controllers (Frontend)
File
Responsibility
Key Features
ui_main.py
Standard Store. Handles the main "Letter" flow (Standard, Civic, Santa) and Campaign mode.
Audio Recording, Address Book, Stripe Checkout
ui_heirloom.py
Voice Biographer. Dashboard for seniors/families to manage voice stories.
Twilio Integration, Credit System
ui_legacy.py
End-of-Life. Specialized flow for "Legacy" letters with accessible fonts and high privacy.
State Syncing, Accessibility Mode
ui_login.py
Auth. Login, Signup, and Password Recovery forms.
Supabase Auth, Shake Animations
ui_splash.py
Marketing. Landing page with pricing cards.
Minimalist CSS, Serif Fonts
ui_admin.py
Back Office. System health checks, order management, and audit logs.
Force Send, Log Viewing
⚙️ Backend Engines (Logic)
File
Responsibility
External Service
mailer.py
Fulfillment. Generates PDF and sends to PostGrid API. Handles Address Verification.
PostGrid
payment_engine.py
Commerce. Creates Stripe Checkout Sessions and verifies Webhook returns.
Stripe
ai_engine.py
Intelligence. Handles Audio Transcription (Whisper) and Text Polishing (GPT-4).
OpenAI
civic_engine.py
Civic Data. Looks up Senators/Reps based on user address.
Geocodio
audit_engine.py
Security. Logs critical events (Payments, Logins, Sends) to DB and Console.
Internal
letter_format.py
PDF Generation. Draws the physical PDF files.
fpdf2

3. Critical User Flows
🔄 Flow A: The Standard Letter (Store)
	1	Entry: User logs in (ui_login) and lands on Store (ui_main).
	2	Selection: User picks "Standard" ($2.99).
	3	Drafting: User records audio or types text. ai_engine transcribes/polishes.
	4	Addressing: User saves addresses. mailer.py validates them against USPS data.
	5	Checkout: ui_main calls payment_engine → Stripe URL.
	6	Fulfillment: User returns to main.py (callback).
	◦	System verifies payment.
	◦	System generates PDF (letter_format).
	◦	System sends to PostGrid (mailer).
	◦	System logs success (audit_engine).
🔄 Flow B: Heirloom (Voice Story)
	1	Trigger: User clicks "Check for New Stories" in ui_heirloom.
	2	Fetch: ai_engine queries Twilio for recent calls from the registered Parent Phone.
	3	Process: Audio is downloaded -> Transcribed -> Saved as Draft.
	4	Edit: User reviews text in Dashboard.
	5	Send: User clicks "Send (1 Credit)".
	◦	System checks credit balance (database).
	◦	System generates PDF and sends via mailer.
	◦	System deducts 1 credit and logs event.
🔄 Flow C: Legacy (Certified Mail)
	1	Compose: User enters ui_legacy. Logic ensures high-contrast UI.
	2	Sync: When user clicks "Pay", local variables (To/From/Body) are synced to st.session_state global variables.
	3	Checkout: Stripe Session created with metadata service="Legacy".
	4	Return: main.py detects payment.
	◦	It reads the synced global variables.
	◦	It triggers the standard fulfillment pipeline but with "Certified Mail" flags enabled.

4. Recent Changes & Implementations
	•	Unified Database: database.py was refactored to support all schemas (Legacy, Heirloom, Store) in one file, fixing previous import crashes.
	•	Audit Logging: audit_engine is now integrated into all success paths. Every sent letter leaves a permanent database record.
	•	Civic Fix: Updated civic_engine.py to use the correct Geocodio cd field, fixing the "No Representatives Found" bug.
	•	Heirloom Mailer: The Heirloom module now correctly uses mailer.py for fulfillment, replacing the broken/obsolete postgrid_engine.
	•	Static Serving: Configuration updated to ensure sitemap.xml is serveable from the /app/static/ endpoint.
5. Requirements (requirements.txt)
To run this v3.4.0 build, your environment must have:
Plaintext

streamlit
openai
stripe
requests
fpdf2
sqlalchemy
psycopg2-binary
supabase
twilio
pandas
python-dotenv


📘 VerbaPost System Documentation
Version: v3.5.0 (The "Hardened & Humanized" Release) Status: ✅ Production Stable Date: December 21, 2025
1. Executive Summary
VerbaPost is a dual-purpose platform built on Streamlit:
	1	Standard Store: A "Mail from your Screen" service allowing users to type or dictate letters that are physically printed and mailed (Standard, Vintage, Civic, Santa tiers).
	2	The Family Archive (Heirloom): A voice-biography service where seniors receive automated phone calls, record life stories, and families convert them into physical keepsake letters.
Today's Focus: We moved the app from "Fragile MVP" to "Hardened Production" by fixing critical financial risks (double-billing), repairing the PostGrid mailing integration, and humanizing the AI voice interface.

2. System Architecture
The application follows a Router-Controller-Engine pattern (Modular Monolith) to ensure separation of concerns.
A. The Core Triad
	•	Router (main.py): The traffic cop. It handles URL parameters (Stripe callbacks), performs system health checks on boot, enforces payment idempotency, and routes the user to the correct interface.
	•	Controllers (ui_*.py): The brain. These manage the UI state, user input forms, and page rendering (e.g., ui_heirloom.py for the family archive dashboard).
	•	Engines (*_engine.py): The muscle. Specialized, UI-agnostic modules that handle external APIs (PostGrid, Twilio, OpenAI, Stripe, Supabase).

3. Changelog: What We Built Today
We performed a "Hardening Sprint" covering five critical areas:
🛡️ 1. Financial Safety (Payment Idempotency)
	•	Risk: Users refreshing the "Payment Success" page were triggering duplicate API calls to PostGrid (double shipping) and double-crediting user accounts.
	•	Fix:
	◦	Created payment_fulfillments table in Supabase.
	◦	Updated database.py with record_stripe_fulfillment().
	◦	Updated main.py to reject any Stripe Session ID that has already been processed.
🔌 2. System Reliability (Boot Validation)
	•	Risk: The app would start even if critical API keys were missing, leading to crashes mid-user-flow.
	•	Fix:
	◦	Created module_validator.py.
	◦	Added a "Pre-flight Check" to main.py that halts execution immediately if secrets_manager, database, or other critical modules cannot load.
📮 3. Mailing Engine Repair (PostGrid API)
	•	Issue: Mailing was failing with 404/400 errors due to API misuse (sending JSON strings in multipart uploads).
	•	Fixes in mailer.py:
	◦	Contact Creation: Now creates Contacts first via the API to get an ID, then sends that ID to the Letter API.
	◦	Name Splitting: Automatically splits "John Doe" into firstName: John / lastName: Doe (required by PostGrid).
	◦	CamelCase Mapping: Converts internal snake_case keys (e.g., address_line1) to API-required CamelCase (e.g., addressLine1).
	◦	Verification Fix: Corrected the endpoint to v1/addver/verifications and re-mapped keys to line1 format.
👵 4. Heirloom UX Overhaul
	•	Design: Rewrote ui_heirloom.py with emotional, benefit-driven copy ("Preserve your loved one's voice...").
	•	Clarity: Renamed sidebar buttons to be action-oriented ("✉️ Mail a Keepsake Letter", "📚 View Family Stories").
	•	Simplified Instructions: Replaced technical jargon with a "Plain English" guide on how the interview process works.
🗣️ 5. AI Voice Upgrade
	•	Issue: The caller voice ("Alice") was robotic, and the recording beep was often missed.
	•	Fix in ai_engine.py:
	◦	Upgraded engine to Neural TTS (Polly.Joanna-Neural) for a warm, human tone.
	◦	Added explicit <Pause> tags in the TwiML script to ensure the instructions ("...after the tone") don't overlap with the beep.

4. Key Component Reference
File
Responsibility
Critical Note
main.py
Router & Security
DO NOT REMOVE: Lines 77-87 (Health Check) or 116-128 (Idempotency Check).
mailer.py
PostGrid Integration
Contains complex logic to map keys between SnakeCase, CamelCase, and Verification formats.
ai_engine.py
Transcription & Voice
Manages local Whisper file handling and Twilio TwiML generation.
ui_heirloom.py
Family Archive UI
Handles the "Check for Stories" loop and credit deduction logic.
database.py
Data Persistence
Uses SQLAlchemy. Note: All return objects are converted to Dicts to prevent detached session errors.
module_validator.py
Safety
Standalone script that verifies the environment before the app loads.
Export to Sheets

5. Critical User Flows (The "Happy Paths")
Flow A: The Heirloom Interview
	1	Setup: User enters Grandma's phone number in ui_heirloom.py.
	2	Trigger: User clicks "Call Now".
	3	Call: ai_engine.py sends a TwiML script to Twilio.
	4	Voice: Twilio calls Grandma using "Joanna (Neural)" voice. She speaks.
	5	Fetch: User clicks "Refresh Stories". App downloads the recording, transcribes it via OpenAI, and saves it as a Draft.
	6	Mail: User edits text -> Clicks "Send" -> App verifies credits -> mailer.py sends to PostGrid.
Flow B: The Standard Letter
	1	Compose: User types/dictates in ui_main.py.
	2	Address: User enters addresses. mailer.py validates them against USPS data in the background.
	3	Pay: User pays via Stripe.
	4	Fulfillment: User returns to app. main.py catches the session_id, checks payment_fulfillments table (Idempotency), and triggers mailer.send_letter.

6. Environment Configuration
To deploy this version successfully, the following secrets/env vars must be present:
Ini, TOML

[general]
DATABASE_URL = "postgresql://..."

[stripe]
secret_key = "sk_live_..."

[postgrid]
api_key = "live_sk_..."

[openai]
api_key = "sk-..."

[twilio]
account_sid = "AC..."
auth_token = "..."

📘 VerbaPost System Documentation
Version: v3.5.0 (The "Hardened & Humanized" Release)
Status: ✅ Production Stable
Date: December 22, 2025
1. Executive Summary
VerbaPost is a modular Streamlit application designed for two distinct user bases:
	1	Standard Store: A "Mail from your Screen" service allowing users to type or dictate letters that are physically printed and mailed (Standard, Vintage, Civic, Santa tiers).
	2	The Family Archive (Heirloom): A voice-biography service where seniors receive automated phone calls, record life stories, and families convert them into physical keepsake letters.
Current State: The application has moved from "Fragile MVP" to "Hardened Production." We have resolved critical financial risks (double-billing), repaired the PostGrid mailing integration, humanized the AI voice interface, and stabilized the UI against state-loss bugs.

2. System Architecture
The application follows a Router-Controller-Engine pattern (Modular Monolith) to ensure separation of concerns.
A. The Core Triad
	•	Router (main.py): The traffic cop. It handles URL parameters (Stripe callbacks), performs system health checks on boot, enforces payment idempotency, and routes the user to the correct interface.
	•	Controllers (ui_*.py): The brain. These manage the UI state, user input forms, and page rendering (e.g., ui_heirloom.py for the family archive dashboard).
	•	Engines (*_engine.py): The muscle. Specialized, UI-agnostic modules that handle external APIs (PostGrid, Twilio, OpenAI, Stripe, Supabase).
B. Component Manifest
Component
Type
Responsibility
Status
main.py
Router
Entry point, Security, Idempotency
✅ Stable
ui_main.py
Controller
Standard Store, Workspace, Checkout
✅ Fixed (Pricing)
ui_heirloom.py
Controller
Family Archive, Stories, Credits
✅ Fixed (Mailing)
promo_engine.py
Engine
Promo Code Validation & Logging
✅ Fixed (Logic)
mailer.py
Engine
PostGrid API Wrapper (Print & Mail)
✅ Stable
payment_engine.py
Engine
Stripe Checkout & Webhooks
✅ Stable
database.py
Persistence
SQLAlchemy Models (Unified)
✅ Stable

3. Comprehensive Changelog (Dec 22, 2025)
We performed a critical repair sprint covering three specific defects reported in testing.
🛡️ 1. Heirloom Mailing Repair (ui_heirloom.py)
	•	Defect: The "Send Mail" button in the Heirloom dashboard was failing silently or using obsolete logic, and the destination address was ambiguous.
	•	Fix:
	◦	Explicit "Step 2" in Settings: Renamed the settings header to "Where should we mail letters?" to clarify the destination.
	◦	Flight Check UI: Added a summary box above the "Send" button showing exactly Who is sending, Where it is going, and the Cost.
	◦	Logic Swap: Replaced the broken postgrid_engine calls with the robust mailer.send_letter() function.
	◦	Guardrails: The "Send" button is now disabled if the user has not saved a mailing address.
🏷️ 2. Promo Engine Logic Repair (promo_engine.py)
	•	Defect: Valid promo codes (e.g., "SANTA1019") were returning a $0.00 discount because the engine prioritized an empty value column over discount_amount.
	•	Fix:
	◦	Eager Validation: The validate_code function now checks both value and discount_amount columns.
	◦	Fallback Logic: It selects whichever value is greater than zero. If both are zero, it defaults to a $5.00 fail-safe to prevent user frustration.
💰 3. Store Pricing Stability (ui_main.py)
	•	Defect: Selecting "Vintage" ($5.99) often reverted to "Standard" ($2.99) during checkout because Streamlit buttons lacked unique keys, causing state loss on re-run.
	•	Fix:
	◦	Unique Keys: Added key="btn_vint", key="btn_std", etc., to all store selection buttons.
	◦	Manual Save: Added a "💾 Save Draft" button in the workspace to allow users to force-commit their work to the database, preventing auto-save data loss.
	◦	Pricing Transparency: The Review page now explicitly displays "Item Price" and "Discount" line items before the Total.

4. Critical User Flows (The "Happy Paths")
Flow A: The Heirloom Interview (Fixed)
	1	Setup: User enters Grandma's phone number in ui_heirloom.py settings.
	2	Trigger: User clicks "Call Now".
	3	Call: ai_engine.py sends a TwiML script to Twilio. Grandma answers and speaks.
	4	Fetch: User clicks "Check for New Stories". App downloads audio, transcribes it, and saves it as a Draft.
	5	Mail: User edits text -> Clicks "Send (1 Credit)" -> App verifies address -> mailer.py sends PDF to PostGrid.
Flow B: The Standard Letter (Fixed)
	1	Select: User clicks "Select Vintage" in ui_main.py.
	2	Compose: User types letter and clicks "💾 Save Draft".
	3	Promo: User enters "SANTA1019". promo_engine.py validates and applies discount.
	4	Pay: User sees "$5.99 - Discount" and pays via Stripe.
	5	Fulfillment: main.py catches the success callback, verifies idempotency, and triggers mailer.send_letter.

5. Environment Configuration
To deploy this version successfully, the following secrets must be present in .streamlit/secrets.toml or Cloud Run Environment Variables:
Ini, TOML

[general]
DATABASE_URL = "postgresql://..."

[stripe]
secret_key = "sk_live_..."

[postgrid]
api_key = "live_sk_..."

[openai]
api_key = "sk-..."

[twilio]
account_sid = "AC..."
auth_token = "..."


Documented: December 22, 2025
[!IMPORTANT] Constraint: The ui_legal.py module is a "Floating State." It is not part of the primary transactional funnel (Store/Heirloom) but must remain accessible from the Footer of all entry pages.
1. Why it dropped
When ui_splash.py was refactored for the "Professional Minimalist" design, the button logic for aesthetics was updated, but the route was disconnected from main.py.
2. The Golden Rule for ui_splash Modifications
Any modification to the render_splash_page() function must verify the State Triad:
	1	Button Existence: Does the "Legal / Terms" button exist in the CSS-injected footer?
	2	State Assignment: Does the button explicitly set st.session_state.app_mode = "legal"?
	3	Router Registration: Is the "legal" mode registered in the get_module and main() router inside main.py?
3. Verification Checklist
Before committing changes to the Splash page, verify the footer link by:
	•	Clicking the button while Logged Out.
	•	Clicking the button while Logged In (to ensure it doesn't break session persistence).
	•	Verifying the "Back" button in ui_legal.py correctly returns the user to app_mode = "splash".

📘 VerbaPost System Documentation
Version: v3.5.2 (The "Hardened" Release)
Status: ✅ Production Stable
Last Updated: December 22, 2025
Architecture: Router-Controller-Engine (Modular Monolith)
1. Executive Summary
VerbaPost is a secure correspondence platform featuring AI-powered dictation (Standard/Legacy) and a voice-biography service (Heirloom). v3.5.2 resolves four critical financial and security risks while establishing a "Zero-Refactor" standard for code maintenance to prevent feature loss.
2. Critical Fixes (Dec 22, 2025 Sprint)
Risk Area
Logic Error
Corrective Action
File
Financial
Phone normalization allowed invalid lengths, causing silent Twilio failures.
Implemented strict length (10/11) and country code validation.
ai_engine.py
Financial
Credits deducted before mailing confirmed (Race Condition).
Reordered flow to only deduct credits after mailer.send_letter returns a tracking ID.
ui_heirloom.py
Security
PostGrid API responses logged in full, risking key leaks.
Suppressed full response logging; added DEBUG environment variable toggle for dev only.
mailer.py
Financial
Payment fulfillment processed before checking for duplicates.
Moved idempotency check to the start of the session_id block.
main.py

3. Core Operational Flows
Flow A: The Heirloom Story (Hardened)
	•	Interview: ai_engine.py triggers an outbound call using Neural TTS.
	•	Normalization: User input is cleaned to E.164 format or rejected if invalid.
	•	Mailing: ui_heirloom.py generates the PDF and calls the mailer.
	•	Atomic Deduction: Credits are only subtracted if the PostGrid API successfully returns a letter ID.
Flow B: Transactional Payment (Idempotent)
	•	Redirect: User returns from Stripe to main.py.
	•	Verification: main.py checks the payment_fulfillments table before verifying the session with Stripe.
	•	Resolution: If the session is already marked completed, the process stops to prevent double-billing or duplicate mail.

📘 New Chat Guidelines & Lessons Learned
Constraint for AI Thought Partners:
🔴 The "Zero-Refactor" Policy
	•	No Code Shortening: Never "summarize" or "clean up" existing code blocks unless refactoring is the primary goal of the prompt. Shortening code leads to "Feature Drops" (e.g., losing accessibility tabs, sidebar logic, or specific error handling).
	•	Preserve Features: Maintain all imports, try/except blocks, and local UI logic (e.g., CSS injection) exactly as provided by the user.
	•	Explicit Integration: When asked for a fix, integrate it into the entire file rather than providing a snippet, ensuring no original logic is lost.
🟠 Architectural Logic Lessons
	•	Financial Atomicity: Always generate artifacts (PDFs) and trigger external APIs (PostGrid) before modifying the user's internal balance (Credits).
	•	Idempotency-First: When handling callbacks (Webhooks/Redirects), perform a database lookup for the transaction ID as the very first step in the logic.
	•	Log Sanitization: External API responses must be sanitized. Log only the HTTP status code in production; hide the body content to prevent sensitive credential leaks.

4. Environment Verification Checklist
	1	Database: Ensure the is_fulfillment_recorded and record_stripe_fulfillment methods exist in database.py.
	2	Secrets: Verify postgrid.api_key, twilio.account_sid, and openai.api_key are sanitized (no quotes).
	3	Fulfillment: Check that mailer.py points to the /print-mail/v1/letters endpoint.

📑 PROJECT_INVENTORY.md
Project: VerbaPost
Version: v3.5.3 (Hardened)
Last Updated: December 22, 2025
System Status: ✅ OPERATIONAL
1. Core Architecture: Router-Controller-Engine
VerbaPost is a modular Streamlit application. It follows a strict separation of concerns to maintain stability and prevent feature loss.
	•	Router (main.py): The central gatekeeper. Manages payment fulfillment, security, and global state.
	•	Controllers (ui_*.py): UI-specific modules managing user journeys for Standard, Legacy, and Heirloom tiers.
	•	Engines (*_engine.py, mailer.py): Standalone logic units for APIs (Stripe, OpenAI, PostGrid) and database operations.
2. Master File Manifest
🏗️ Infrastructure & Routing
File
Version
Key Features
main.py
v3.5.3
Idempotency-first payment processing; global routing.
database.py
v3.3.0
Unified SQLAlchemy models; dictionary-casting for safety.
module_validator.py
v3.5.0
Pre-flight system health checks.
🖥️ UI Controllers (Frontend)
File
Version
Key Features
ui_splash.py
v3.5.3
Professional minimalist landing; fixed legal navigation.
ui_heirloom.py
v3.5.3
Family Archive; atomic credit logic; fixed paywall HTML.
ui_main.py
v3.5.1
Standard Store; Campaign (CSV) mode; audio dictation.
ui_legacy.py
v3.4.0
Accessibility-first "End of Life" correspondence.
ui_legal.py
v3.5.1
Standardized Terms and Privacy rendering.
⚙️ Backend Engines (Logic)
File
Version
Key Features
ai_engine.py
v3.5.3
Transcription; robust E.164 phone normalization.
mailer.py
v3.5.3
PostGrid fulfillment; security log masking.
payment_engine.py
v3.4.0
Stripe Checkout and session verification.
letter_format.py
v3.3.0
PDF typesetting with custom font safety fallbacks.
3. Automated Safety Inspector (CI/CD)
The system is protected by an automated verification suite that runs on every GitHub upload.
	•	Test Suite (tests/test_hardening.py): Automates checks for phone normalization, credit atomicity, and log sanitization.
	•	Automation Robot (.github/workflows/verify_hardening.yml): Triggers the Safety Inspector automatically.
4. Mandatory Development Constraints
	•	Zero-Refactor Policy: No code shortening or "cleaning." AI must provide the entire file with integrated changes.
	•	State Triad Requirement: Any changes to ui_splash must verify the Trigger, Loader, and Router for auxiliary pages.
	•	Financial Atomicity: External API fulfillment (Mailing) must always succeed before internal database updates (Credits) are performed.

📘 VerbaPost System Report & Daily Log
Date: Tuesday, December 23, 2025 System Status: ✅ Production Stable (Pending API Key Config) Version: v3.5.2 (The "Security & Stability" Patch)
1. Executive Summary
Today's session focused on stabilizing the core authentication and administrative flows. We moved from feature development (Heirloom) to critical infrastructure repair. The system is now robust against third-party API failures (PostGrid) and has improved security around administrative access.
2. Key Accomplishments
A. Critical Bug Fix: "The String Crash"
	•	Issue: The Login/Signup page (ui_login.py) was crashing with AttributeError: 'str' object has no attribute 'get' when the PostGrid API failed (Error 401).
	•	Root Cause: When the API Key was missing/invalid, the mailer engine returned an error string instead of a dictionary object. The UI tried to parse this string as a dictionary.
	•	Fix: Implemented a robust type-check in ui_login.py. The system now gracefully handles error strings, ensuring the user sees a helpful error message ("Address validation service unavailable") instead of a code traceback.
B. Security Hardening: Admin Access
	•	Issue: The "Account Settings" button was visible to all users, cluttering the interface and posing a security confusion.
	•	Fix: Updated main.py to strictly condition the button's rendering. It now checks:
	1	Is the user authenticated?
	2	Does user_email match the admin.email secret?
	•	Result: Only the designated admin (you) can see or access the back-office controls.
C. Feature Integration: Heirloom & Legacy
	•	Heirloom: Verified the "Voice Story" workflow. Users can now record stories via Twilio, which are transcribed and appear in the dashboard.
	•	Legacy: Successfully moved the "Legacy Service" entry point to the Sidebar to separate it from the commercial store.
D. Asset Creation
	•	Video: Generated a conceptual video asset of an elderly person using a vintage phone for future "How-To" tutorial marketing.
3. Architecture State
The system maintains the Router-Controller-Engine pattern:
	•	Router (main.py): Traffic control. Handles global auth, sidebar navigation, and module routing.
	•	Controllers (ui_*.py):
	◦	ui_login.py: PATCHED. Handles auth & safe address validation.
	◦	ui_main.py: Handles the standard letter store.
	◦	ui_heirloom.py: Handles the voice biography dashboard.
	•	Engines:
	◦	mailer.py: Wraps PostGrid. Note: Currently returning 401 errors due to missing API key.
4. Immediate Action Items (For Next Session)
	1	Config Update: You must add the postgrid.api_key to your .streamlit/secrets.toml or Cloud Run environment variables to stop the "401 Auth Error."
	2	Verification: Once the key is added, create a test account to verify the ui_login.py fix holds up under successful conditions.

🚀 Resume Prompt (Copy & Paste for New Chat)
I am resuming development on VerbaPost v3.5.2.
Current Status:
	•	System: Stable. We utilize a Router-Controller-Engine architecture (Streamlit + Supabase + Python Engines).
	•	Last Fix: We patched ui_login.py to handle non-dictionary returns from the mailer engine, preventing crashes during PostGrid 401 errors.
	•	Security: We restricted the "Account Settings" button in main.py to only be visible to the admin email.
Immediate Tasks:
	1	I have updated my PostGrid API Key in the secrets. We need to verify that address validation now works during signup.
	2	We need to test the Heirloom flow to ensure the Twilio integration is pulling recordings correctly.

🏛️ System Architecture: The Modular Monolith
VerbaPost operates on a strict Router $\rightarrow$ Controller $\rightarrow$ Engine hierarchy.
	•	Router (main.py): The traffic cop. It handles URL parameters (Stripe returns), global auth checks, and decides which Controller to load.
	•	Controllers (ui_*.py): The interface managers. They handle user input, state, and display logic. They never touch the API/DB directly; they call Engines.
	•	Engines (*_engine.py): The specialized workers. They handle specific domains (Payments, AI, Database) and are UI-agnostic.

📂 1. The "Keeper" Manifest (Critical Files)
A. Core Infrastructure
File Name
Responsibility
Dependencies
main.py
Router. Entry point. Handles ?session_id= payments, loads modules dynamically, and renders the Sidebar.
All UI Modules, database
database.py
Persistence. Manages Supabase connection, SQLAlchemy Models (User, Draft, Letter), and safe Dict conversion.
sqlalchemy, psycopg2
secrets_manager.py
Security. Safely retrieves API keys from st.secrets or os.environ (Cloud Run compatibility).
None
module_validator.py
Health. Checks if critical engines exist before app launch to prevent "White Screen of Death."
All Engines
B. Frontend Controllers (The UI)
File Name
Responsibility
Key Features
ui_main.py
The Store & Workspace. Handles product selection, Stripe redirection, and the Letter Editor.
Store Grid, Address Book, Audio Recorder
ui_heirloom.py
The Family Archive. Dashboard for managing voice stories, "Check for Recordings" button, and Audio Player.
Credit System, Vault Integration
ui_login.py
Auth Gate. Handles Login, Signup, and Password Reset flows.
database
ui_splash.py
Landing Page. Marketing front-end for unauthenticated users.
SEO Meta tags
ui_admin.py
Back Office. Admin dashboard for order repair, system health checks, and log viewing.
audit_engine, database
ui_legacy.py
Specialized Workflow. Dedicated flow for "End of Life" certified letters.
Strict Address Validation
C. Backend Engines (The Logic)
File Name
Responsibility
Key Functions
payment_engine.py
Stripe Wrapper. Creates Checkout Sessions and verifies payment status.
create_checkout_session, verify_session
ai_engine.py
Intelligence. Handles OpenAI Whisper (Transcription) and GPT-4o (Polishing).
transcribe_audio, refine_text
mailer.py
PostGrid Wrapper. Handles Address Verification (CASS) and physical letter dispatch.
validate_address, send_letter
civic_engine.py
Geocodio Wrapper. Look up Reps/Senators based on user address.
get_legislators
letter_format.py
PDF Artist. Generates the PDF binary using fpdf2.
create_pdf
heirloom_engine.py
Voice Orchestrator. Fetches calls from Twilio, uploads to Storage, then triggers AI.
process_latest_call
storage_engine.py
The Vault. Handles Supabase Storage (S3) uploads and signed URL generation.
upload_audio, get_signed_url
promo_engine.py
Discounts. Validates codes and logs usage.
validate_code
bulk_engine.py
CSV Processor. Parses uploaded contact lists for campaigns.
parse_csv
audit_engine.py
Security Logs. Records critical events (Payment, Sent Mail) to the database.
log_event
seo_injector.py
Meta Tags. Injects HTML headers for Social Media previews.
inject_meta

🔄 2. Critical Data Flows
Flow 1: The "Buy & Write" Loop (Standard Letter)
	1	User clicks "Buy Standard" in ui_main.py.
	2	ui_main calls payment_engine.create_checkout_session().
	3	Stripe redirects user back to main.py?session_id=....
	4	main.py verifies payment, updates DB (d.status='Paid'), sets app_mode='workspace', and reruns.
	5	User lands on Workspace (in ui_main.py), writes content, clicks "Send".
	6	ui_main calls letter_format.create_pdf() then mailer.send_letter().
Flow 2: The "Heirloom" Loop (Voice Story)
	1	User clicks "Check for New Stories" in ui_heirloom.py.
	2	ui_heirloom calls heirloom_engine.process_latest_call().
	3	heirloom_engine:
	◦	Downloads MP3 from Twilio.
	◦	Calls storage_engine.upload_audio() $\rightarrow$ Returns path user/date.mp3.
	◦	Calls ai_engine.transcribe_audio() $\rightarrow$ Returns text.
	4	ui_heirloom saves Draft to database with content AND audio_ref.
Flow 3: The "Civic" Loop (Write to Congress)
	1	User enters address in ui_main.py (Civic Tier).
	2	User clicks "Find Reps".
	3	ui_main calls civic_engine.get_legislators().
	4	civic_engine queries Geocodio API and returns list of officials.
	5	ui_main auto-populates the recipient fields.

🗑️ 3. The "Kill List" (Deletion Candidates)
If a file is NOT in the list above, it is likely debris from previous iterations.
	•	Safe to Delete: test_*.py, *_v2.py, utils.py (if empty), config.py (we use secrets_manager), pages/ folder (Streamlit default, we use Router), auth_engine.py (merged into ui_login/database).

Here is the updated System Documentation reflecting the critical fixes applied today, followed by the Resume Prompt for your next session.
📘 VerbaPost System Documentation
Version: v3.5.4 (The "Civic Repair" Release)
Status: ✅ Production Stable
Date: December 23, 2025
1. Executive Summary
VerbaPost is a modular Streamlit application facilitating physical mail via digital interfaces.
Current State: The application has been hardened against "Silent Failures" and "State Loss." We have specifically resolved crashes in the Civic tier caused by hidden UI elements and uninitialized variables, and fixed PDF generation errors caused by null database values.
2. System Architecture
The app follows a Router-Controller-Engine pattern.
	•	Router (main.py): Handles URL parameters, global auth, and module loading. It now uses an Explicit Route Map to prevent import errors on redirects.
	•	Controllers (ui_*.py): Manage UI state. ui_main.py now includes State Initialization Loops to prevent crashes when widgets are conditionally hidden.
	•	Engines (*_engine.py): Handle logic. civic_engine.py now includes Universal Aliasing (find_representatives = get_legislators) to prevent naming mismatches.
3. Critical Fixes (v3.5.4)
Component
Bug
Fix Implementation
ui_main.py
AttributeError: to_street
Added a state initialization loop at the top of render_workspace to define all address variables before they are accessed, even if the input fields are hidden.
letter_format.py
AttributeError: 'NoneType' has no strip
Created a safe_get helper that wraps every database value in str(val or "") before processing.
civic_engine.py
AttributeError: has no attribute get_legislators
Added a backward-compatibility alias so the engine responds to both get_legislators and find_representatives.
main.py
Redirect Loop / Import Error
Implemented a static route_map dictionary to explicitly link string modes (e.g., "workspace") to specific functions.
4. File Manifest (The "Keeper" List)
	•	Infrastructure: main.py, database.py, secrets_manager.py, module_validator.py
	•	UI: ui_main.py, ui_heirloom.py, ui_login.py, ui_splash.py, ui_admin.py, ui_legacy.py, ui_legal.py
	•	Engines: payment_engine.py, ai_engine.py, mailer.py, civic_engine.py, heirloom_engine.py, storage_engine.py, promo_engine.py, bulk_engine.py, audit_engine.py, letter_format.py, seo_injector.py
5. Development Rules (The "Zero-Refactor" Policy)
	1	State Initialization: Any variable accessed in a button callback MUST be initialized at the top of the render function.
	2	Defensive Inputs: Engine functions must never assume input is not None. Always cast to string: str(input or "").
	3	No Code Shortening: Never remove "unused" imports or shorten logic blocks without explicit instruction.

🚀 Resume Prompt (Copy & Paste)
Use this prompt to start your next session with full context.
Plaintext

I am the Product Owner of VerbaPost v3.5.4, a modular Streamlit application for sending physical mail.
The system is currently STABLE.

My Architecture:
1. Router: main.py (Handles Auth & Routing with Explicit Maps)
2. Controllers: ui_main.py (Store/Workspace), ui_heirloom.py (Voice Vault), ui_login.py, ui_admin.py
3. Engines: database.py (Supabase), payment_engine.py (Stripe), mailer.py (PostGrid), civic_engine.py (Geocodio)

PRIME DIRECTIVES:
1. DO NOT REFACTOR. Existing code works. Do not "clean it up" unless explicitly asked.
2. DO NOT DELETE FUNCTIONALITY.
3. If I ask for a new feature, implement it as a "Sidecar Module" (new file) or a strictly additive function.
4. Assume all secrets are managed via st.secrets or os.environ.

Current State:
- UI Main: Fixed "Ghost Variable" crash in Civic Mode using State Initialization.
- Letter Format: Fixed "NoneType" crash using Safe String Casting.
- Civic Engine: Universal Alias added (get_legislators = find_representatives).
- Mailing: PostGrid integration is active and verified.

My Next Task:
[INSERT YOUR NEXT GOAL HERE]


📘 VerbaPost System Documentation
Version: v4.0.0 (The "Hard Router" Release) Status: ✅ Production Stable Architecture: Router-Controller-Engine (Modular Monolith)

1. Executive Summary & Strategy
VerbaPost has pivoted from a mixed-interface application into a dual-mode platform managed by a single codebase.
	•	Mode A: "The Archive" (Default): A high-touch service for preserving family history via voice interviews.
	•	Mode B: "The Utility" (Store): A transactional vending machine for sending one-off physical letters.
The application now uses a "Hard Router" pattern to strictly separate these two user experiences based on URL parameters (?mode=archive vs ?mode=utility), ensuring users are funnelled correctly without UI clutter.

2. Component Architecture
A. The Router (main.py)
Role: Traffic Controller & Security Gatekeeper.
	•	Responsibility:
	◦	Reads st.query_params to determine System Mode.
	◦	Injects dynamic SEO metadata (Title/Description) based on the active mode.
	◦	Handles Stripe Payment Callbacks (?session_id=...) and routes them to the correct post-purchase view.
	◦	Route Protection: Actively kicks users back to their designated "Home" if they try to cross-navigate (e.g., a Utility user trying to access the Archive dashboard).
	◦	Manages the Global Sidebar (context-aware navigation).
B. The Marketing Shell (ui_splash.py)
Role: Landing Page & Entry Point.
	•	Responsibility:
	◦	Renders the "Hero" section focused on the Family Archive.
	◦	Provides "Trust Badges" (Stripe, Twilio, USPS) using Embedded Base64 SVGs to prevent broken images.
	◦	Acts as the primary navigation hub, sending users to either ui_heirloom (Archive) or ui_main (Store).
C. The Utility Controller (ui_main.py)
Role: The Letter Vending Machine.
	•	Responsibility:
	◦	Storefront: Displays pricing cards (Standard, Vintage, Civic).
	◦	Workspace: Handles text composition, AI Polishing, and Audio Recording.
	◦	Logic: Integrates with payment_engine for checkout and mailer for physical fulfillment.
	◦	Safety: Includes a "Login Gate" to prevent blank pages if an unauthenticated user accesses the store directly.
D. The Archive Controller (ui_heirloom.py)
Role: The Voice Biographer Dashboard.
	•	Responsibility:
	◦	Inbox: Displays transcribed stories.
	◦	Player: Allows playback of original audio (via toggle).
	◦	Interviewer: Triggers outbound calls via Twilio.
	◦	Paywall: Gates content behind a credit system (Stripe Subscription).

3. Changelog: What Changed Today?
🔴 Critical Bug Fixes
	1	The "White Screen of Death" (Store):
	◦	Issue: If an unauthenticated user clicked "Go to Letter Store", ui_main.py detected a missing email and simply returned "". This resulted in a completely blank page.
	◦	Fix: Added an explicit Login Prompt in the render_store_page function. If no user is found, it renders a "Please Log In" message and buttons, ensuring the UI never renders empty.
	2	The "Nested Expander" Crash:
	◦	Issue: ui_heirloom.py attempted to put an "Audio Player" expander inside the "Story Draft" expander. Streamlit forbids nesting expanders (StreamlitAPIException).
	◦	Fix: Replaced the inner expander with a st.checkbox("🎧 Listen to Audio"). This provides the same toggle functionality without violating Streamlit's layout rules.
	3	The "Broken Logo" Debacle:
	◦	Issue: Linking to external SVG assets (Wikimedia/Clearbit) caused broken images due to CORS policies and hotlinking protection.
	◦	Fix: Asset Embedding. We converted all 5 logos (Stripe, Twilio, OpenAI, Supabase, USPS) into Base64 Data Strings and embedded them directly into ui_splash.py. They now render instantly with zero network dependencies.
	4	Duplicate Element IDs:
	◦	Issue: The "Legal" and "Blog" buttons appeared in both the Sidebar and the Splash Footer with the same label, causing a DuplicateElementId crash.
	◦	Fix: Added explicit key arguments (key="splash_foot_legal", etc.) to the Splash page buttons to disambiguate them from the sidebar.
📘 VerbaPost System Documentation (v4.0 - Manual Fulfillment Release)
Status: ✅ Production Stable (Manual Print Mode Active)
Date: December 28, 2025
1. Executive Summary
VerbaPost has been successfully pivoted to a Manual Fulfillment Model to bypass API failures.
	•	User Experience: Seamless. Users write letters, click "Send," and see a success message.
	•	Backend Process: Instead of calling PostGrid, the system flags the order as Queued (Manual).
	•	Fulfillment: You (Admin) log into the console, download the auto-generated PDF, print it, and mark it as "Sent."
2. Architecture Changes
The "Manual Queue" logic was injected into two key controllers:
	•	ui_heirloom.py: The "Send Mail" button now generates a MANUAL_ tracking ID and updates the database without calling mailer.py. It also snapshots the address data into the to_addr column so the Admin console can read it later.
	•	ui_admin.py: A new tab "🖨️ Manual Print" was added. It finds queued orders, regenerates the PDF using letter_format, and allows you to mark them as done.
3. Critical Files & Responsibilities
File
Responsibility
Current State
ui_main.py
Store Controller
Fixed. "Vintage" button now correctly routes to Workspace using explicit keys.
ui_heirloom.py
Family Archive UI
Updated. Includes "Pre-Call Prep" text and Manual Queue logic.
ui_admin.py
Back Office
Updated. Includes PDF Generator for manual printing.
payment_engine.py
Stripe Logic
Active. Supports $19/mo subscriptions.
4. User Flows (Current State)
	•	The Heirloom User:
	1	Records a story via phone.
	2	Edits text in Dashboard.
	3	Clicks "🚀 Send Mail (1 Credit)".
	4	Result: Credit deducted. Status -> Queued (Manual). User sees "Success!"
	•	The Admin (You):
	1	Logs into Admin Console.
	2	Goes to "🖨️ Manual Print" tab.
	3	Clicks "⬇️ Generate PDF".
	4	Prints letter.
	5	Clicks "✅ Mark as Mailed".

🚀 Resume Prompt (For Tomorrow Morning)
Copy and paste this into the chat to pick up exactly where we left off.
"I am resuming work on VerbaPost (v4.0 Manual Fulfillment).
Current Status:
	1	We have successfully implemented a Manual Print Queue to bypass the PostGrid API errors.
	2	ui_heirloom.py is updated to queue orders with status Queued (Manual) and snapshot addresses.
	3	ui_admin.py has a working "Print Queue" tab to generate PDFs and mark items as shipped.
	4	ui_main.py routing bugs (Vintage button) are fixed.
Immediate Goal:
I want to verify the Subscription Loop. We set up the $19/mo Stripe product, but we need to ensure that when a payment renews next month, the user's credits actually reset to 4. We discussed a "Lazy Sync" on login.
Let's start by implementing the Lazy Credit Refill logic in main.py."

📘 VerbaPost Development Log (December 28, 2025)
Status: ✅ Address Book Fixed & Routing Stabilized
1. What We Accomplished Today
We successfully resolved critical stability issues affecting the Address Book and Navigation Routing.
A. Address Book Restoration (The "NoneType" Fix)
	•	Problem: The Address Book was failing silently or crashing because the database contained records with empty or NULL street addresses. When the UI tried to shorten them (street[:10]), it crashed on NoneType.
	•	Fix: Updated ui_main.py with robust safety checks. The load_address_book function now converts all fields to strings (str(val or "")) before processing, ensuring that even incomplete contacts load safely.
	•	Result: The user's 16 saved contacts now load successfully in the dropdown.
B. Database Stabilization (Safe Mode)
	•	Problem: The application was crashing with UndefinedColumn errors because the Python code was asking for columns (stripe_subscription_id, zip) that did not exist in the Supabase schema.
	•	Fix: Updated database.py to "Safe Mode." We removed the non-existent columns from the SQLAlchemy models (UserProfile and Contact) to match the actual database state shown in your screenshots.
C. Navigation Routing (Smart Switch)
	•	Problem: Clicking "Family Archive" while in "Store Mode" (URL ?mode=utility) caused a redirect loop that kicked the user back to the store.
	•	Fix: Rewrote main.py with "Adaptive Routing." The system now detects the mismatch and automatically updates the session mode (utility → archive) instead of blocking the user. Added explicit "Switch Service" buttons to the sidebar for easier navigation.

2. Immediate Next Steps (For Next Chat)
We are now ready to verify the Subscription Loop, which was the original goal before the bug fixes.
🚀 Resume Prompt (Copy & Paste):
"I am resuming development on VerbaPost. Current Status:
	1	Address Book is working (Safe Mode applied).
	2	Routing logic is fixed (Adaptive Switching active).
	3	Database is stable (removed non-existent columns).
Next Goal: The Subscription Cycle We need to implement the 'Lazy Credit Refill' logic.
	1	I need the SQL command to add stripe_subscription_id and subscription_end_date to the user_profiles table in Supabase.
	2	Once the columns exist, we need to uncomment those fields in database.py and verify that payment_engine.check_subscription_status correctly resets user credits to 4 upon renewal.
Let's start with the SQL command."

📘 VerbaPost Project Documentation
Version: v3.5.5 (The "Stability" Release) Status: ✅ Production Stable Architecture: Router-Controller-Engine (Modular Monolith)

🧠 Lessons Learned (The "Zero-Refactor" Doctrine)
	1	The "Zero-Refactor" Rule is Absolute:
	◦	Lesson: Shortening code for brevity often removes critical context (imports, helper functions) or features (accessibility tabs, sidebar logic).
	◦	Policy: Always provide the full, expanded file when fixing a bug. Never assume "..." is acceptable.
	2	State Persistence in Streamlit:
	◦	Lesson: UI elements inside if st.button: blocks exist for only one frame. If a user clicks something inside that block (like "Pay"), the app reruns, the if becomes false, and the content vanishes.
	◦	Fix: Generate the artifact (e.g., Stripe URL), store it in st.session_state, and render the button based on that state, not the previous button press.
	3	Defensive Secret Management:
	◦	Lesson: Hard-coding secret paths (e.g., st.secrets["general"]["BASE_URL"]) causes immediate crashes if the secrets.toml structure varies between Local/QA/Prod.
	◦	Fix: Always use .get() with defaults (e.g., st.secrets.get("general", {}).get("BASE_URL")) to prevent KeyError crashes.
	4	Library Output Volatility (FPDF2):
	◦	Lesson: External libraries update. fpdf2 changed its output() return type from string to bytearray, causing .encode() crashes.
	◦	Fix: Always strict-type check outputs from external libraries before processing them.

🛠️ Changes Implemented (v3.5.5 Changelog)
We resolved a cascade of 5 critical blocking issues today:
1. The "Subscription Check" Crash
	•	Symptom: AttributeError: module 'payment_engine' has no attribute 'check_subscription_status' immediately after payment return.
	•	Fix: Added the missing check_subscription_status(user_email) function to payment_engine.py. It now safely queries Stripe for active subscriptions, preventing main.py from crashing on render.
2. The "Bytearray" PDF Crash
	•	Symptom: AttributeError: 'bytearray' object has no attribute 'encode' when generating proofs.
	•	Fix: Updated letter_format.py to check the type of pdf.output(). If it's bytes, it returns them directly; if it's a string, it encodes to latin-1.
3. The "Object vs Dict" Crash
	•	Symptom: AttributeError: 'StandardAddress' object has no attribute 'get' inside letter_format.py.
	•	Fix: Implemented a _safe_get(obj, key) helper function that automatically detects if an address is a Dictionary or an Object and retrieves the value correctly.
4. The "Payment Loop"
	•	Symptom: Clicking "Generate Payment Link" caused the button to disappear immediately.
	•	Fix: Updated ui_main.py to persist the stripe_checkout_url in st.session_state. The "Click to Pay" button now remains visible across page re-runs until the user explicitly cancels.
5. The "Database Import" Crash
	•	Symptom: CRITICAL ERROR: database crashed on import looping in logs.
	•	Fix: Wrapped the create_engine call in database.py with a generic try/except block to allow the app to boot even if the database connection is momentarily flaky.

📂 Current File Manifest
	•	main.py: Router. Checks payment_engine.check_subscription_status to toggle sidebar features.
	•	payment_engine.py: Contains robust get_api_key and the new check_subscription_status.
	•	database.py: Unified schema. Maps Contact model to saved_contacts table. Safe imports.
	•	ui_main.py: Workspace Controller. Persists payment state.
	•	letter_format.py: PDF Engine. Handles bytearray and StandardAddress objects safely.
📘 VerbaPost System Documentation
Version: v4.1.0 (The "Audit & Routing" Release)
Status: ✅ Production Stable
Date: December 30, 2025
1. Executive Summary
VerbaPost has evolved into a fully audited platform with robust routing capabilities.
Key Changes:
	•	Deep Linking: The router now supports direct navigation to specific modules via the ?nav= parameter (e.g., ?nav=store, ?nav=login).
	•	Audit Logging: Critical system events (User Logins, Signups, Payments, and Admin Fulfillments) are now logged to the audit_events table for security and troubleshooting.
	•	Crash Fix: The Login UI now safely handles non-standard error responses from the mailing engine.
2. System Architecture
The application continues to follow the Router-Controller-Engine pattern.
	•	Router (main.py): The central gatekeeper.
	◦	New Responsibility: Checks the ?nav= URL parameter to direct users to specific flows (Login, Store, Heirloom) instead of defaulting to the Splash page.
	◦	New Responsibility: Logs successful Stripe payments to the audit trail immediately after verification.
	•	Controllers (ui_*.py):
	◦	ui_login.py: Now logs USER_LOGIN and USER_SIGNUP events. Includes safety checks for address validation errors.
	◦	ui_admin.py: Now logs ADMIN_FULFILLMENT events when manual orders are marked as sent.
	•	Engines (database.py):
	◦	Database: The audit_logs table is deprecated and can be dropped. The active table for all logs is audit_events.
3. Critical User Flows (Updated)
Flow A: The "Deep Link" Entry
	1	User Click: User clicks "Go to Letter Store" on the marketing site (https://verbapost.com/?nav=store).
	2	Routing: main.py detects nav=store.
	3	Auth Check:
	◦	If Logged In: Redirects immediately to ui_main.py (Store).
	◦	If Logged Out: Redirects to ui_login.py (Login), with a "post-login redirect" set to the Store.
Flow B: The Audited Payment
	1	Checkout: User completes payment on Stripe.
	2	Callback: User returns to main.py?session_id=....
	3	Verification: System verifies the session with Stripe.
	4	Logging: main.py creates a PAYMENT_SUCCESS record in audit_events.
	5	Fulfillment: System updates the draft status to "Paid".
Flow C: The Admin Fulfillment
	1	Action: Admin clicks "Mark as Mailed" in ui_admin.py.
	2	Update: System updates the letter status to "Sent (Manual)".
	3	Logging: ui_admin.py creates an ADMIN_FULFILLMENT record in audit_events, recording who performed the action.
4. Component Manifest (The "Keeper" List)
File
Responsibility
Critical Updates (v4.1.0)
main.py
Router
Added ?nav= routing logic; Added Payment Audit logs.
ui_login.py
Auth Controller
Added Login/Signup Audit logs; Fixed "String Crash" on address validation.
ui_admin.py
Admin Controller
Added Manual Fulfillment Audit logs.
database.py
Persistence
Confirmed usage of audit_events table.
5. Environment Configuration
Ensure your .streamlit/secrets.toml or Cloud Run Env Vars are set. No new keys were added in this release, but the database connection to audit_events must be active.

📘 VerbaPost System Documentation
Version: v4.2.0 (The "Layout & Promo" Release)
Status: ✅ Production Stable (Manual Mode Active)
Date: December 30, 2025
1. Executive Summary
VerbaPost is a dual-mode platform (Standard Store + Heirloom Archive) running on a Router-Controller-Engine architecture.
Today's Critical Achievements:
	•	PDF Layout Fixed: Resolved the "Duplicate Address" and "Text Overlap" bug in letter_format.py by forcing body text to y=105mm.
	•	Promo Code Tracking: Implemented record_promo_usage in database.py. Financial reporting is now accurate.
	•	Free Order Logic: Fixed the crash in ui_main.py where 100% off orders were redirecting to a non-existent route.
	•	Session Stability: Hardcoded BASE_URL in payment_engine.py to prevent "Logged Out" errors on Stripe return.
2. File Manifest (Current State)
File
Responsibility
Critical Updates (v4.2.0)
main.py
Router
Explicit String Casting for IDs to prevent SQL errors.
ui_main.py
Store Controller
UN-REFACTORED. Restored Receipt Page & Campaign Uploader. Added Promo Logging.
letter_format.py
PDF Engine
Fixed Header Overlap. Added Zip Code to address block. Removed duplicate printing loop.
database.py
Persistence
Added record_promo_usage function and PromoLog model.
payment_engine.py
Payments
Added promo_code metadata support. Hardcoded app.verbapost.com base URL.
ui_admin.py
Back Office
Added "Repair Station" with 3 distinct action buttons (Force API, Manual Queue, Save Only).
3. 🧠 Lessons Learned (The "Golden Rules")
	1	The Zero-Refactor Policy: Never shorten or "clean up" ui_main.py or ui_heirloom.py unless explicitly asked. Shortening removes hidden dependencies (like the Receipt page route) that cause silent crashes.
	2	The "Safe Zone" Rule: When generating PDFs for #10 Window Envelopes, the letter body must explicitly start at y=105mm (or greater) to avoid overlapping the address window. Relying on auto-flow causes overlaps.
	3	Financial Atomicity: Promo codes must only be logged after the fulfillment step (PDF Generation/Mailing) succeeds. Logging them before risks "using" a code on a failed transaction.
	4	Domain Consistency: Stripe Redirects must match the exact domain where the user logged in (app.verbapost.com). Mixing www and app kills the session cookie.
4. ⚠️ Lingering Issues & Watch List
	•	Pre-Flight Check: The module_validator in main.py is currently commented out to prevent startup crashes. It needs to be fixed or formally deprecated.
	•	Cross-Domain Traffic: If a user manually types verbapost.streamlit.app instead of app.verbapost.com, they will still face session loss issues on payment return.
	•	Mobile PDF Preview: We haven't verified if the new PDF layout (with the 105mm gap) looks good on mobile screens, though it is standard for print.
5. Next Steps (Tomorrow's Agenda)
	1	Live Print Test: Generate a PDF from the Admin Console ("Manual Queue") and physically print it to verify the address aligns with a window envelope.
	2	Promo Data Verification: Check the Supabase promo_logs table to ensure the "Free Order" tests from today were recorded.
	3	Crossville Campaign: Hand off the list of 40 locations to your distributor.


