import streamlit as st
from get_responses import (
    get_response,
    get_rag_response,
    create_session_name
    )
from record_chats_history_sql import (
    load_user_chats,
    generate_random_session_id,
    add_messages,
    get_messages_by_session_id,
    delete_session,
    edit_session_name
)
from datetime import datetime
import time
import re

#Configure the streamlit page
st.set_page_config(
    page_title="chatbot UI",
    initial_sidebar_state="expanded"
)

def login_ui():
    """
    Renders the user authentication interface
    """
    st.title("User Authentication")
    user_id = st.text_input("User name")
    if user_id:
        st.write(f"welcome, {user_id}")
        st.session_state["authenticated"] = True
        st.session_state["user_id"] = user_id
        st.rerun()

def chat_interaction(model, temperature, user_input: str, messages: list):
    """
    Handles the interaction between the user and the chatbot

    Args:
        model (str): The model to use for generating responses
        temperature (float): sampling temperature for response generation.
        user_input (str): The user's input message.
        messages (list): The list of previous messages in the chat.

    Returns:
        list: Updated list of messages including the assistant's response
    """
    messages.append({
        "role": "user",
        "content": user_input
    })
    # Fetch the last 20 messages for context
    chat_history = st.session_state["messages"][-20:]
    response = get_rag_response(chat_history, model, temperature)
    # Uncomment the following line to use RAG responses
    # response = get_rag_response(chat_history, model, temperature)
    messages.append({
    "role": "assistant",
    "content": response
    })
    
    return messages

def chat_app():
    """
    Main chat application interface.
    """
    st.title("Chatbot for PoC")

    def log_off_func():
        """
        Logs off the current user by clearing relevant session state variables.
        """
        st.session_state["authenticated"] = False
        del st.session_state["session_id"]
        del st.session_state["session_name"]
        del st.session_state["messages"]
        del st.session_state["chat_input"]
        del st.session_state["selection"]

    # sidebar styling
    st.sidebar.markdown(
        """
        <style>
            div[data-testid="column"]:nth-of-type(1) {
                border:1px solid red;
        }
        div[data-testid="column"]:nth-of-type(2) {
        border:1px solid blue;
        text-align: end;
        }
    </style>
    """,
    unsafe_allow_html=True
    )
    # Sidebar columns for user avatar and log off button
    scol4, scol5 = st.sidebar.columns([1, 5])
    with scol4:
        user_initial = st.session_state["user_id"][0].upper() # Extract the firs
        st.markdown(
            f"""
            <style>
                div[data-testid="column"] {{
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
                }}
            </style>
            <div data-testid="column">
                {user_initial}
            </div>
            """,
            unsafe_allow_html=True
        )
    with scol5:
        st.button("Log off", on_click=log_off_func)

    st.sidebar.write("----")

    def new_chat_func():
        """
        Initializes a new chat session by resetting relevant session state variables.
        """
        st.session_state["session_id"] = None
        st.session_state["session_name"] = None
        st.session_state["messages"] = None
        st.session_state["chat_input"] = False
        st.session_state["selection"] = None

    # Initialize session state variables if they don't exist
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = None
    if "session_name" not in st.session_state:
        st.session_state["session_name"] = None
    if "messages" not in st.session_state:
        st.session_state["messages"] = None
    if st.session_state.messages is None:
        st.session_state["messages"] = [{
            "role": "assistant",
            "content": f"""Welcome {st.session_state["user_id"]}! I'm here to help"""
        }]
    if "chat_input" not in st.session_state:
        st.session_state["chat_input"] = False
    if "selection" not in st.session_state:
        st.session_state["selection"] = None

    # Button to start a new chat
    st.sidebar.button("New Chat", type="primary", on_click=new_chat_func)

    # Model selection
    models=[
        "gpt-4o-2024-11-20",
        "gpt-4o-mini-2024-07-18"]

    model= st.sidebar.selectbox(
        "Select Model",
        models,
        index=1
        )


    # Temperature selection slider
    if not bool(re.match(r'^o\d', model)):
    #if model in ["gpt-4o-2024-08-06", "gpt-4o-mini", "gemini-1.5-flash", "gemini-2.0-flash-lite", "gemini-2.0-flash"]:
        temperature = st.sidebar.select_slider(
            "Select the Temperature",
            options=[x / 10 for x in range(11)],
            value=0.5
        )
    else:
        temperature = None

    st.sidebar.write("----")
    # Load selected chat session

    if st.session_state["selection"]:
        index = st.session_state["user_chats_dict"]["session_name"].index(st.session_state["selection"])
        st.session_state["session_id"] = st.session_state["user_chats_dict"]["session_id"][index]
        st.session_state["session_name"] = st.session_state["selection"]
        st.session_state["messages"] = get_messages_by_session_id(st.session_state["session_id"])

    # Sidebar columns for chat history actions
    scol1, scol2, scol3 = st.sidebar.columns([2, 2, 2])

    def delete_reset_select():
        """
        Deletes the selected chat session and resets the selection.
        """
        delete_session(st.session_state["session_id"])
        new_chat_func()

    with scol1:
        with st.popover("Delete Chat"):
            if st.session_state["selection"]:
                st.write(f"""Are you sure you want to delete the chat: "{st.session_state["selection"]}"?""")
                st.button("Delete Chat", on_click=delete_reset_select)
            else:
                st.write("Please select a chat")

    def change_session_name_func():
        """
        Changes the name of the current chat session.
        """
        edit_session_name(st.session_state["session_id"], new_session_name)
        st.session_state["user_chats_dict"] = load_user_chats(st.session_state["user_id"]),
        st.session_state["selection"] = st.session_state["change_session_name"]
        st.session_state["change_session_name"] = None

    with scol2:
        with st.popover("Edit Name"):
            if st. session_state["selection"]:
                new_session_name = st.text_input(
                    label="Write the new name",
                    key="change_session_name"
                )
                st.button("Change Name", on_click=change_session_name_func)
            else:
                st.write("Please select a chat")

    with scol3:
        with st.popover("Edit Last Message"):
            if st.session_state.chat_input:
                st.text_area(
                    label="Edit Last Message",
                    value=st.session_state["user_input"],
                    key="lst_msg",
                    label_visibility="hidden"
                )
                change_last_msg= st.button("Save & Submit")
            elif len(st.session_state["messages"]) > 1:
                st.text_area(
                    label="Edit Last Message",
                    value=st.session_state["messages"][-2]["content"],
                    key="lst_msg",
                    label_visibility="hidden"
                    )
                change_last_msg = st.button("Save & Submit")

            try:
                if change_last_msg:
                # Remove the last two messages (user and assistant) and update with edited message
                    st.session_state["messages"] = st.session_state["messages"][:-2]
                    st.session_state["messages"] = chat_interaction(
                        model,
                        temperature,
                        st.session_state["lst_msg"],
                        st.session_state["messages"]
                    )
                    st.session_state.chat_input = True
            except:
                pass

    # Define avatars
    # user_avatar=":)"
    # assistant_avatar = "./logos/eyq_avatar.png"
    # Display chat messages
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    
    def stream_data(response):
        for word in response.split(" "):
            yield word + " "
            time.sleep(0.05)

    def chat_input_func():
        """
        sets the chat input flag to True when a user submits a message.
        """
        st.session_state["chat_input"] = True

    if user_input := st.chat_input(on_submit=chat_input_func, key="user_input"):
        # Generate a new session ID if not already set
        if st.session_state["session_id"] is None:
            st.session_state["session_id"] = generate_random_session_id()

        # Display user 2 message in the chat
        st.chat_message("user").write(user_input)
        # Update messages with assistant's response
        st.session_state["messages"] = chat_interaction(
            model,
            temperature,
            user_input,
            st.session_state["messages"]
        )
        # Display assistant's response
        with st.chat_message("assistant"):
            st.write_stream(stream_data(st.session_state["messages"][-1]["content"]))
        # Generate session name if not already set
        if st.session_state["session_name"] is None:
            session_content = st.session_state["messages"][1]["content"]
            s_name = session_content.split()
            st.session_state["session_name"] = ' '.join(s_name[:4]) if len(s_name) > 4 else ' '. join(s_name)

    # Capture current time
    time_now = datetime.now()
    # Determine the time of the first interaction
    if len(st.session_state["messages"]) < 4:
        first_interaction = datetime.now()
    else:
        first_interaction = None

    if st.session_state.chat_input:
        if st.session_state["session_name"] is not None:
            add_messages(
                st.session_state["user_id"],
                st.session_state["session_id"],
                st.session_state["session_name"],
                st.session_state["messages"],
                first_interaction,
                time_now
            )

    # Load user chats dictionary
    st.session_state["user_chats_dict"] = load_user_chats(st.session_state["user_id"])

    # Retrieve session names for chat history
    session_names = st.session_state["user_chats_dict"].get("session_name", [])
    
    # Radio buttons for selecting chat history
    st.sidebar.radio(
        "Chat History",
        session_names,
        index=None,
        key='selection'
    )

def main():
    """
    Main function to run the application based on authentication state.
    """
    if st.session_state.authenticated:
        chat_app()
    else:
        login_ui()

if __name__ == "__main__":
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    main()
