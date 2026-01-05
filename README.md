VerbaPost
Real Mail, Real Legacy. VerbaPost is a modular Streamlit application that bridges the digital and physical worlds. It allows users to compose letters via a web interface or voice dictation and have them physically printed and mailed via the USPS. It features two primary modes: a standard letter utility and "The Family Archive" (Heirloom), a voice-biography service for preserving family stories.

🏗️ System Architecture
VerbaPost utilizes a Router-Controller-Engine pattern (Modular Monolith) to ensure separation of concerns and stability.

Router (main.py): The central traffic controller. It handles URL routing, global authentication checks, payment fulfillment triggers, and security headers.

Controllers (ui_*.py): The interface layer. These modules manage user state, form inputs, and frontend logic (e.g., ui_main.py for the store, ui_heirloom.py for voice stories).

Engines (*_engine.py): The logic layer. Standalone, UI-agnostic modules that handle external API integrations (Stripe, OpenAI, PostGrid, Twilio, Geocodio).

✨ Key Features
1. The Letter Store (Utility Mode)
Digital-to-Physical: Users can type letters that are automatically converted to PDF and mailed via USPS.

Smart Addressing: Integrates address verification to ensure deliverability.

Civic Action: Users can enter their address to automatically find and write to their specific US Senators and Representatives.

Multi-Tier Support: Supports various letter tiers (Standard, Vintage, Civic) with dynamic pricing.

2. The Family Archive (Heirloom Mode)
Voice-to-Mail: Designed for seniors. Users record stories via telephone calls which are automatically transcribed.

AI Transcription: Uses OpenAI Whisper to convert speech to text and GPT models to polish the output for print.

Credit System: A subscription-based model where credits are exchanged for physical mailings.

3. "End of Life" Legacy Service
Certified Mail: A specialized workflow for legal or sentimental "End of Life" documents, ensuring delivery tracking.

Accessibility First: Features high-contrast UI elements and large typography for accessibility.
