# VerbaPost v3.4.0 (Phase 2 Complete) 📮

**Status:** ✅ Production Stable  
**Last Updated:** December 12, 2025  
**Architecture:** Router-Controller-Engine (Modular Monolith)

## 🌐 Overview
VerbaPost bridges the digital-physical gap by using AI to turn voice dictation into professional physical mail. It handles transcription (OpenAI Whisper), generation (PDF), payment (Stripe), and fulfillment (PostGrid).

**New in v3.4.0:**
* **Smart UI:** Accordion-style address forms to reduce clutter.
* **Help Module:** Dedicated FAQ section and sidebar navigation.
* **Rich Feedback:** Informative loading screens for payments and transcription.
* **Civic Intelligence:** Auto-detection of specific Representative names for preview generation.

---

## 🏗️ Core Architecture
The app uses a "Triad" structure to separate concerns:

1.  **The Router (`main.py`)**: The security gatekeeper. It handles URL parameters, CSRF checks on payment returns, and initializes the session state.
2.  **The Controller (`ui_main.py`)**: The brain. Manages the linear user journey (Store -> Workspace -> Review), handles UI state, and calls backend engines.
3.  **The Engines (Backend)**: Domain-specific modules that process data independently of the UI.

### Key Components 
| File | Responsibility |
| :--- | :--- |
| `ui_main.py` | **(Core)** Main UI controller. Manages forms, state, and user flow. |
| `ui_help.py` | **(New)** Handles FAQ and Help documentation display. |
| `ai_engine.py` | Runs OpenAI Whisper locally (CPU) for zero-cost transcription. Calls OpenAI API for text refinement. |
| `mailer.py` | Connects to PostGrid. Handles address verification (CASS) and PDF transmission. |
| `payment_engine.py` | Wraps Stripe API. Creates sessions and verifies payment success securely. |
| `pricing_engine.py` | Server-side price calculator to prevent client-side tampering. |
| `database.py` | SQLAlchemy ORM for Supabase (PostgreSQL). Manages Users, Drafts, and Contacts. |
| `letter_format.py` | Generates PDF binaries. Handles "Safe Zone" layout to prevent PostGrid overlap errors. |
| `civic_engine.py` | Interfaces with Geocodio to map zip codes to specific US Representatives. |

---

## 🔄 Critical User Flows

### 1. The Store & Payment Flow
*Goal: Securely capture intent and payment before resource-intensive tasks.*
1.  **Selection:** User selects a tier (e.g., "Civic" or "Standard").
2.  **Calculation:** `pricing_engine` calculates total server-side.
3.  **Ghost Draft:** A draft record is created in `database.py` to link the future payment.
4.  **Loading State:** App displays "Creating your Stripe checkout..." with HTML visual feedback.
5.  **Redirect:** User pays on Stripe.com.
6.  **Return:** User is redirected back to `main.py?session_id=xyz`.
7.  **Recovery:** `main.py` verifies the session, recovers the user email from Stripe (if session was lost), and unlocks the **Workspace**.

### 2. The Smart Workspace Flow (Input)
*Goal: Collect address and content with minimal friction.*
1.  **Smart Addressing:**
    * **Standard:** User sees an "Accordion" form (From/To) that expands only when needed.
    * **Civic:** User enters ONLY their zip code. `civic_engine` auto-fetches their Reps.
2.  **Audio Instruction:** User sees a clear "1-2-3" guide on how to record.
3.  **Transcription:**
    * User records audio.
    * App shows "Converting speech to text..." (30-60s CPU warning).
    * `ai_engine` processes audio via local Whisper model.

### 3. Review & Fulfillment Flow
*Goal: Final verification and physical dispatch.*
1.  **Refinement:** User clicks "Professional" or "Grammar" to auto-polish text via GPT-4o.
2.  **Smart Preview:**
    * **Standard:** Generates PDF with entered address.
    * **Civic:** Dynamically pulls the *first* Representative's specific address for the preview so the user sees a real name (e.g., "Rep. Tarak Robbana") instead of a placeholder.
3.  **Dispatch:**
    * User clicks "Send".
    * App displays checklist: "Generating PDF... Uploading... Scheduling Pickup...".
    * PDF is sent to PostGrid API.
    * Database marks order as `Completed`.

---

## 🛠️ Setup & Installation
1.  **Environment:** Ensure `secrets.toml` contains keys for Stripe, OpenAI, PostGrid, Supabase, and Geocodio.
2.  **Dependencies:** `pip install -r requirements.txt` (requires `ffmpeg` installed on system for audio).
3.  **Run:** `streamlit run main.py`

## 🧪 Testing Notes
* **Civic Mode:** Requires valid US Zip Code to fetch Reps.
* **Audio:** Local transcription requires CPU. For Cloud Run deployment, increase memory to 2GB minimum.