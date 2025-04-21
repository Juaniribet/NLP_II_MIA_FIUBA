import streamlit as st
from datetime import datetime
from typing import Optional, Dict

def login_user(username: str) -> Dict:
    """
    Log in a user with basic session-based authentication.
    
    Args:
        username: The username to log in with
        
    Returns:
        Dict: The logged in user's data
    """
    user_data = {
        "user_id": username,
        "created_at": datetime.now().isoformat()
    }
    
    # Store user data in session state
    st.session_state["user"] = user_data
    st.session_state["authenticated"] = True
    
    return user_data

def get_current_user() -> Optional[Dict]:
    """
    Get the currently logged in user.
    
    Returns:
        Optional[Dict]: The current user's data or None if not authenticated
    """
    if "user" not in st.session_state or not st.session_state["authenticated"]:
        return None
    
    return st.session_state["user"]

def logout_user():
    """Log out the current user by clearing session state."""
    if "user" in st.session_state:
        del st.session_state["user"]
    st.session_state["authenticated"] = False

def is_authenticated() -> bool:
    """
    Check if a user is currently authenticated.
    
    Returns:
        bool: True if user is authenticated, False otherwise
    """
    return st.session_state.get("authenticated", False) 