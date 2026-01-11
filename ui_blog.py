import streamlit as st
import time

def render_blog_page():
    # --- HEADER ---
    st.title("📰 VerbaPost Insights")
    st.markdown("Thoughts on legacy, memory, and the future of family history.")
    
    # --- NAVIGATION ---
    # Default to "For Advisors" if mode is partner, otherwise default to "All"
    default_idx = 1 if st.session_state.get("system_mode") == "partner" else 0
    tab_all, tab_b2b, tab_stories = st.tabs(["All Posts", "For Advisors (B2B)", "Family Stories"])

    # --- CONTENT DATABASE ---
    posts = [
        {
            "id": "heir-attrition",
            "title": "The 90% Problem: Solving Heir Attrition with Emotional Wealth",
            "category": "B2B",
            "date": "Dec 28, 2025",
            "preview": "Why do 90% of heirs fire their parents' advisor? Because the relationship was transactional, not emotional.",
            "content": """
            ### The Silent Crisis in Wealth Management
            
            It is the statistic that keeps Wealth Managers awake at night: **over 90% of heirs prompt changes in advisors after receiving their inheritance.**
            
            We call this **Heir Attrition**.
            
                        
            The Great Wealth Transfer is seeing trillions of dollars move from Baby Boomers to Millennials and Gen Z. Yet, most advisors have no relationship with the next generation. When the matriarch or patriarch passes, the assets leave with them.
            
            ### The Missing Link: Emotional Legacy
            
            Financial planning prepares the money for the heirs. **Legacy planning prepares the heirs for the money.**
            
            VerbaPost offers a bridge. By facilitating "Legacy Letters" or "Heirloom Voice Biographies" for your senior clients, you achieve three critical retention goals:
            
            1.  **Deepened Trust:** You move from being a "money guy" to a trusted family partner.
            2.  **Next-Gen Introduction:** The delivery of these letters often involves family meetings, giving you a natural, non-sales reason to meet the heirs.
            3.  **Differentiation:** In a world of commoditized robo-advisors, offering a physical, emotional legacy service sets your firm apart.
            
            **Don't let the assets walk out the door.** Start a VerbaPost Heirloom project for your top-tier clients today.
            """
        },
        {
            "id": "power-of-voice",
            "title": "Why Voice is the Medium of Memory",
            "category": "Stories",
            "date": "Dec 15, 2025",
            "preview": "Handwriting is beautiful, but the human voice carries the soul. How VerbaPost captures the nuance of storytelling.",
            "content": """
            ### The Sound of History
            
            When we lose a loved one, the first thing we often forget is the sound of their voice. 
            
            VerbaPost's **Heirloom Service** was built to solve this. Unlike video, which can make seniors self-conscious, or typing, which can be physically difficult, voice is natural.
            
            * **Comfort:** They speak from their own phone, in their own chair.
            * **Nuance:** We capture the laughter, the pauses, and the cadence.
            * **Permanence:** We transcribe these stories into physical, archival-quality letters, but we also preserve the audio forever.
            """
        }
    ]

    # --- RENDERER HELPER ---
    def render_posts(filter_cat=None):
        for post in posts:
            if filter_cat and post['category'] != filter_cat:
                continue
                
            with st.expander(f"{'📌' if post['category']=='B2B' else '📖'} {post['title']}"):
                st.caption(f"{post['date']} • {post['category']}")
                st.markdown(post['content'])
                
                if post['category'] == "B2B":
                    st.divider()
                    st.markdown("#### 🤝 Partner with VerbaPost")
                    st.write("Retain your clients' heirs with our white-label solution.")
                    if st.button("Partner Inquiry", key=f"btn_{post['id']}"):
                        # Redirect to Partner Portal
                        st.session_state.app_mode = "partner"
                        st.session_state.redirect_to = "partner"
                        st.rerun()

    # --- TABS ---
    with tab_all:
        render_posts()
    with tab_b2b:
        st.info("Strategies for Wealth Managers & Estate Planners.")
        render_posts("B2B")
    with tab_stories:
        render_posts("Stories")
        
    # --- FOOTER ---
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("⬅️ Back Home"):
        st.session_state.app_mode = "splash"
        st.rerun()