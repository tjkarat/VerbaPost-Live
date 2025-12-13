import streamlit as st

def show_onboarding_tutorial():
    """
    Show this the first time a user lands on the workspace page.
    """
    # Check if user has seen tutorial
    if st.session_state.get("tutorial_completed"):
        return

    if not st.session_state.get("show_tutorial"):
        # Offer tutorial on first visit to workspace
        with st.container(border=True):
            st.markdown("""
            <div style="text-align: center; padding: 20px;">
                <h2 style="color: #2a5298;">👋 Welcome to VerbaPost!</h2>
                <p style="font-size: 1.1rem; color: #666;">
                    First time here? Take a 30-second tour to learn how it works.
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns([1, 2, 1])
            with c2:
                if st.button("🎓 Start Tutorial", type="primary", use_container_width=True):
                    st.session_state.show_tutorial = True
                    st.session_state.tutorial_step = 0
                    st.rerun()
                if st.button("Skip for now", type="secondary", use_container_width=True):
                    st.session_state.tutorial_completed = True
                    st.rerun()
        return

    # Tutorial steps
    steps = [
        {
            "title": "Step 1: Record Your Message",
            "icon": "🎙️",
            "description": "Click the microphone and speak your letter. Our AI will transcribe it for you.",
            "tips": ["Speak clearly at a normal pace", "Say 'comma' or 'period' for punctuation", "Keep background noise low"]
        },
        {
            "title": "Step 2: Review & Edit",
            "icon": "✏️",
            "description": "Check the transcription and make any edits. Use AI buttons to polish the tone.",
            "tips": ["Click 'Professional' to formalize language", "Click 'Grammar' to fix mistakes", "Edit directly in the text box"]
        },
        {
            "title": "Step 3: Send It!",
            "icon": "📬",
            "description": "We'll print, stamp, and mail your letter via USPS. Arrives in 3-5 days.",
            "tips": ["Verify recipient address is correct", "Save contacts to your address book", "Track your order in the dashboard"]
        }
    ]
    
    current_step = st.session_state.get("tutorial_step", 0)
    step_data = steps[current_step]
    
    # Modal Overlay CSS
    st.markdown("""
    <style>
        .tutorial-card {
            background: #ffffff;
            border: 2px solid #2a5298;
            border-radius: 15px;
            padding: 30px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 20px;
            animation: fadeIn 0.5s;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(-20px); } to { opacity: 1; transform: translateY(0); } }
        .t-icon { font-size: 3rem; margin-bottom: 10px; }
        .t-title { color: #2a5298; font-weight: bold; font-size: 1.5rem; margin-bottom: 10px; }
        .t-desc { font-size: 1.1rem; color: #444; margin-bottom: 20px; }
        .t-tips { text-align: left; background: #f8f9fa; padding: 15px; border-radius: 10px; font-size: 0.9rem; color: #555; }
    </style>
    """, unsafe_allow_html=True)
    
    # Render Card
    st.markdown(f"""
    <div class="tutorial-card">
        <div class="t-icon">{step_data['icon']}</div>
        <div class="t-title">{step_data['title']}</div>
        <div class="t-desc">{step_data['description']}</div>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("💡 Quick Tips", expanded=True):
        for tip in step_data['tips']:
            st.write(f"• {tip}")
            
    # Navigation Buttons
    c1, c2 = st.columns(2)
    with c1:
        if current_step > 0:
            if st.button("← Back"):
                st.session_state.tutorial_step -= 1
                st.rerun()
    with c2:
        if current_step < len(steps) - 1:
            if st.button("Next →", type="primary"):
                st.session_state.tutorial_step += 1
                st.rerun()
        else:
            if st.button("🚀 Finish", type="primary"):
                st.session_state.tutorial_completed = True
                st.session_state.show_tutorial = False
                st.rerun()

def show_contextual_help(page):
    """
    Small help bubbles that appear on specific pages.
    """
    help_tips = {
        "workspace": {
            "title": "💡 Recording Tips",
            "tips": ["Find a quiet room", "Speak at normal pace", "Pause briefly between sentences"]
        },
        "review": {
            "title": "✅ Before You Send",
            "tips": ["Verify recipient address", "Check for typos in text", "Preview the PDF"]
        },
        "store": {
            "title": "📦 Choosing a Package",
            "tips": ["Standard: Best for regular mail", "Heirloom: Premium paper & style", "Civic: Automatic rep lookup"]
        }
    }
    
    if page in help_tips:
        data = help_tips[page]
        with st.expander(f"{data['title']}", expanded=False):
            for tip in data['tips']:
                st.markdown(f"• {tip}")
            st.markdown("---")
            if st.button("Restart Tutorial", key=f"restart_{page}"):
                 st.session_state.tutorial_completed = False
                 st.session_state.show_tutorial = True
                 st.session_state.app_mode = "workspace"
                 st.rerun()  # <--- CRITICAL FIX: Ensures UI refreshes immediately