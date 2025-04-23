import streamlit as st
from typing import List, Dict, Optional
from src.utils.config import UI_CONFIG, DEFAULT_MODEL
from src.ui.pages.login import LoginPage
import time

class ChatInterface:
    def __init__(self):
        self._initialize_session_state()
        self.login_page = LoginPage()

    def _initialize_session_state(self):
        """Initialize all required session state variables."""
        if "messages" not in st.session_state:
            username = st.session_state.get("user_id", "User")
            st.session_state.messages = [{
                "role": "assistant",
                "content": f"Hello {username}! I'm your AI assistant. How can I help you today?"
            }]
        if "model" not in st.session_state:
            st.session_state.model = DEFAULT_MODEL
        if "temperature" not in st.session_state:
            st.session_state.temperature = 0.7
        if "should_stream" not in st.session_state:
            st.session_state.should_stream = True

    def display_messages(self, messages: List[Dict]):
        """Display chat messages with proper formatting."""
        # Display all messages except the last one normally
        for i, message in enumerate(messages[:-1]):
            with st.chat_message(message["role"]):
                st.write(message["content"])
        
        # Stream only the last message if it's from the assistant
        if messages:
            last_message = messages[-1]
            with st.chat_message(last_message["role"]):
                if last_message["role"] == "assistant" and st.session_state.should_stream:
                    self.stream_response(last_message["content"])
                    st.session_state.should_stream = False  # Reset streaming flag
                else:
                    st.write(last_message["content"])

    def stream_response(self, response: str):
        """Stream the response with a typing effect."""
        message_placeholder = st.empty()
        full_response = ""
        
        for word in response.split():
            full_response += word + " "
            message_placeholder.write(full_response + "▌")
            time.sleep(0.05)
        
        message_placeholder.write(full_response)

    def get_user_input(self) -> Optional[str]:
        """Get user input with proper handling."""
        if prompt := st.chat_input("What would you like to know?"):
            st.session_state.should_stream = True  # Enable streaming for next assistant response
            return prompt
        return None

    def display_user_avatar(self, user_id: str):
        """Display user avatar and logout button in the sidebar."""
        col1, col2 = st.sidebar.columns([1, 3])
        
        with col1:
            user_initial = user_id[0].upper()
            st.markdown(
                f"""
                <style>
                    .avatar {{
                        width: 48px;
                        height: 48px;
                        border: 3px solid black;
                        background-color: #1A1A24;
                        border-radius: 50%;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 25px;
                        text-align: center;
                        color: #DCDCE0;
                        margin-bottom: 0;
                    }}
                </style>
                <div class="avatar">
                    {user_initial}
                </div>
                """,
                unsafe_allow_html=True
            )
            st.markdown(f"<p style='margin-bottom: 5px; padding-left: 10px;'><b>{user_id.capitalize()}</b></p>", unsafe_allow_html=True)
        with col2:
            # Add logout button
            st.sidebar.markdown(" ")
            if st.button("Logout"):
                self.login_page.logout()
                st.rerun()

    def display_model_controls(self, available_models: List[str]):
        """Display model selection and temperature controls."""
        st.sidebar.selectbox(
            "Select Model",
            available_models,
            key="model"
        )
        
        # st.sidebar.slider(
        #     "Temperature",
        #     min_value=0.0,
        #     max_value=1.0,
        #     value=st.session_state.temperature,
        #     step=0.1,
        #     key="temperature"
        # )

    def display_error(self, error_message: str):
        """Display error messages to the user."""
        st.error(error_message)

    def display_success(self, success_message: str):
        """Display success messages to the user."""
        st.success(success_message) 