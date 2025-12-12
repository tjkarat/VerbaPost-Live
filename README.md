# VerbaPost v3.1.12 (Stable) 📮

**Status:** ✅ Production Stable  
**Last Updated:** December 11, 2025  
**Architecture:** Router-Controller-Engine (Modular Monolith)

## 🌐 Overview
VerbaPost bridges the digital-physical gap by using AI to turn voice dictation into professional physical mail. It handles transcription (OpenAI Whisper), generation (PDF), payment (Stripe), and fulfillment (PostGrid).

## 🏗️ Core Architecture
[cite_start]The app uses a "Triad" structure to separate concerns:

1.  **The Router (`main.py`)**: The security gatekeeper. It handles URL parameters, CSRF checks on payment returns, and initializes the session state.
2.  **The Controller (`ui_main.py`)**: The brain. Manages the linear user journey (Store -> Workspace -> Review), handles UI state, and calls backend engines.
3.  **The Engines (Backend)**: Domain-specific modules that process data independently of the UI.

### [cite_start]Key Components 
| File | Responsibility |
| :--- | :--- |
| `ai_engine.py` | Runs OpenAI Whisper locally (CPU) for zero-cost transcription. Calls OpenAI API for text refinement. |
| `mailer.py` | Connects to PostGrid. Handles address verification (CASS) and PDF transmission. |
| `payment_engine.py` | Wraps Stripe API. Creates sessions and verifies payment success securely. |
| `pricing_engine.py` | Server-side price calculator to prevent client-side tampering. |
| `database.py` | SQLAlchemy ORM for Supabase (PostgreSQL). Manages Users, Drafts, and Contacts. |
| `letter_format.py` | Generates PDF binaries. Handles "Safe Zone" layout to prevent PostGrid overlap errors. |
| `auth_engine.py` | Manages Supabase Authentication (Sign In/Up, Password Reset). |
| `promo_engine.py` | Validates coupon codes and tracks usage limits in the database. |
| `ui_admin.py` | Back-office console for retrying failed orders, editing addresses, and creating promos. |

---

## [cite_start]🔄 Critical Workflows 

### 1. The Payment Flow (Secure)
1.  **Selection:** User picks a tier (e.g., "Santa").
2.  **Calculation:** `pricing_engine.calculate_total()` computes price server-side.
3.  **Draft:** Ghost Draft check runs to ensure a DB record exists before payment.
4.  **Stripe:** Session created -> User pays off-site -> Returns to `main.py`.
5.  **Verification:** `main.py` verifies the session via `payment_engine` and unlocks the workspace.

### 2. The Transcription Flow
1.  **Record:** User speaks into the microphone.
2.  **Process:** `ai_engine` saves audio to a temp file (`/tmp`) and runs local Whisper.
3.  **Refine:** User can click "Professional" or "Friendly" to have GPT-4o rewrite the text.

### 3. Fulfillment (The "Send" Button)
1.  **Preview:** `letter_format.py` generates a PDF proof using custom fonts (Caveat/Helvetica).
2.  **Normalization:** `mailer.py` sends the address to PostGrid for verification.
3.  **Transmission:** The final PDF is uploaded via multipart/form-data.
4.  **Completion:** Database marks order as "Completed".

---

