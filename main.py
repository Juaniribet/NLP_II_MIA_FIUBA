import streamlit as st
from src.ui.pages.chat import ChatPage
from src.ui.pages.login import LoginPage
from src.ui.pages.upload import UploadPage
from src.utils.config import UI_CONFIG
from src.ui.components.chat_interface import ChatInterface

st.set_page_config(
    page_title=UI_CONFIG["page_title"],
    initial_sidebar_state=UI_CONFIG["initial_sidebar_state"]
)

# Initialize session state
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []
if "vector_store_params" not in st.session_state:
    st.session_state.vector_store_params = {
        "embedding_model": "text-embedding-3-small",
        "chunk_size": 1000,
        "chunk_overlap": 50,
        "separators": ["\n\n", "\n", " ", ""]
    }

def main():
    """Main application entry point."""
    # Initialize pages
    login_page = LoginPage()
    chat_page = ChatPage()
    upload_page = UploadPage()
    
    # Show appropriate page based on authentication status
    if not st.session_state.get("authenticated", False):
        login_page.render()
    else:
        # Display UI components
        ChatInterface().display_user_avatar(st.session_state.user["user_id"])

        # Add navigation in sidebar
        page = st.sidebar.radio("Go to", ["Upload", "Chat"], horizontal=True, label_visibility="hidden")
        
        # Display selected page
        if page == "Upload":
            upload_page.render()
        else:
            chat_page.render()         
            
if __name__ == "__main__":
    main() 