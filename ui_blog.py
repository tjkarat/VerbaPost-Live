import streamlit as st
import os

def render_blog_page():
    """
    Renders the VerbaPost Blog by reading Markdown files from the 'blog_posts' directory.
    Follows Zero-Refactor standards.
    """
    # --- CSS ---
    st.markdown("""
    <style>
    .blog-container { max-width: 800px; margin: 0 auto; padding: 2rem 1rem; }
    .blog-title { font-family: 'Merriweather', serif; font-size: 2.5rem; color: #111; margin-bottom: 0.5rem; }
    .blog-meta { font-family: 'Helvetica Neue', sans-serif; font-size: 0.9rem; color: #666; margin-bottom: 2rem; border-bottom: 1px solid #eee; padding-bottom: 1rem;}
    .blog-list-item { padding: 20px; border: 1px solid #eee; border-radius: 8px; margin-bottom: 15px; transition: 0.2s; cursor: pointer; }
    .blog-list-item:hover { border-color: #d93025; background-color: #fcfcfc; }
    </style>
    """, unsafe_allow_html=True)

    # --- NAVIGATION ---
    if st.button("← Back to Home", use_container_width=True):
        st.session_state.app_mode = "splash"
        st.rerun()

    # --- CONTENT LOADER ---
    posts_dir = "blog_posts"
    if not os.path.exists(posts_dir):
        st.info("No blog posts found. Please create a 'blog_posts' directory.")
        return ""

    # Get files, sort by name (reverse to show newest if named 01, 02...)
    files = sorted([f for f in os.listdir(posts_dir) if f.endswith(".md")], reverse=True)

    # --- ROUTER WITHIN BLOG ---
    # If a specific post is selected, show it
    if "active_post" in st.session_state and st.session_state.active_post:
        selected_file = st.session_state.active_post
        try:
            with open(os.path.join(posts_dir, selected_file), "r") as f:
                content = f.read()
            
            st.markdown('<div class="blog-container">', unsafe_allow_html=True)
            if st.button("← Back to All Posts"):
                del st.session_state.active_post
                st.rerun()
            st.markdown(content)
            st.markdown('</div>', unsafe_allow_html=True)
        except:
            st.error("Post not found.")
    
    # Otherwise, show the list
    else:
        st.markdown(f"## 📰 VerbaPost Journal")
        st.markdown("Thoughts on legacy, correspondence, and voice.")
        
        for filename in files:
            # Simple parser: Assumes first line is title #
            display_name = filename.replace(".md", "").replace("_", " ").title()
            with open(os.path.join(posts_dir, filename), "r") as f:
                first_line = f.readline().strip().replace("#", "")
                if first_line: display_name = first_line
            
            if st.button(f"📄 {display_name}", key=filename, use_container_width=True):
                st.session_state.active_post = filename
                st.rerun()

    return "" # Artifact Prevention
