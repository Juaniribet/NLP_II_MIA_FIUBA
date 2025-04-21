import streamlit as st
from typing import Optional
from datetime import datetime

class LoginPage:
    def __init__(self):
        self._initialize_session_state()

    def _initialize_session_state(self):
        """Initialize session state variables for login."""
        if "authenticated" not in st.session_state:
            st.session_state.authenticated = False
        if "user" not in st.session_state:
            st.session_state.user = None
        if "messages" not in st.session_state:
            st.session_state.messages = []

    def render(self) -> Optional[str]:
        """
        Render the login page.
        Returns the authenticated user_id if login successful, None otherwise.
        """
        st.title("Welcome to AI Chat Assistant")
        
        # Center the login form
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("login_form", clear_on_submit=True):
                username = st.text_input("Username", key="username_input")
                submit = st.form_submit_button("Login", use_container_width=True)
                
                if submit and username:
                    st.session_state.authenticated = True
                    st.session_state.user = {
                        "user_id": username,
                        "created_at": datetime.now().isoformat()
                    }
                    # Initialize messages with welcome message
                    st.session_state.messages = [{
                        "role": "assistant",
                        "content": f"Hello {username}! I'm your AI assistant. How can I help you today?"
                    }]
                    st.success(f"Welcome, {username}!")
                    st.rerun()
                elif submit:
                    st.error("Please enter a username")
        
        return st.session_state.user["user_id"] if st.session_state.authenticated else None

    def logout(self):
        """Log out the current user."""
        st.session_state.authenticated = False
        st.session_state.user = None
        st.session_state.messages = []  # Initialize as empty list instead of None
        st.session_state.model = None
        st.session_state.temperature = None
        if "vector_store" in st.session_state:
            del st.session_state.vector_store
        st.rerun() 