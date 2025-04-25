import streamlit as st
from src.ui.components.chat_interface import ChatInterface
from src.utils.agent import AgentAI
from src.utils.config import UI_CONFIG
from src.auth.auth_handler import is_authenticated
from typing import Generator
import time

class ChatPage:
    def __init__(self):
        self.chat_interface = ChatInterface()
        self.agent = AgentAI()
        self.available_models = UI_CONFIG["available_models"]
        self._initialize_session_state()

    def _initialize_session_state(self):
        """Initialize session state variables."""
        if "model" not in st.session_state:
            st.session_state.model = self.available_models[0]
        if "messages" not in st.session_state:
            st.session_state.messages = [{
                "role": "assistant",
                "content": f"Hello {st.session_state.user['user_id'].capitalize()}! I'm your AI assistant"
            }]
        if "agent_messages" not in st.session_state:
            st.session_state["agent_messages"] = []
        if "token_count" not in st.session_state:
            st.session_state["token_count"] = []


    def _generate_response(self, prompt: str) -> Generator[str, None, str]:
        """Generate a response using the agent."""
        try:
            # Get the current chat history
            chat_history = st.session_state.messages.copy()
            
            # Add the current prompt to the chat history
            chat_history.append({"role": "user", "content": prompt})
            
            with st.spinner("Agent is thinking..."):
                # Get response using the agent
                response = self.agent.run(prompt, st.session_state.model)
                if not st.session_state["agent_messages"]:
                    st.session_state["agent_messages"] = [self.agent.agent_messages]
                else:
                    st.session_state["agent_messages"].extend([self.agent.agent_messages])
                if not st.session_state["token_count"]:
                    st.session_state["token_count"] = [self.agent.token_count]
                else:
                    st.session_state["token_count"].extend([self.agent.token_count])

            
            if response is None:
                yield "I apologize, but I encountered an error while generating a response. Please try again."
                return
            
            # Stream the response
            full_response = ""
            for word in response.split():
                full_response += word + " "
                yield word + " "
                time.sleep(0.05)
            
            return full_response
        except Exception as e:
            print(f"Error generating response: {e}")
            yield "I apologize, but I encountered an error while generating a response. Please try again."

    def render(self):
        """Render the chat page."""
        st.title("Chat with your documents")
        
        if not is_authenticated():
            st.warning("Please log in to chat with your documents.")
            return

        # Add new chat button in the sidebar
        if st.sidebar.button("New Chat", key="new_chat_button"):
            st.session_state.messages = [{
                "role": "assistant",
                "content": f"Hello {st.session_state.user['user_id'].capitalize()}! I'm your AI assistant"}]
            st.session_state["agent_messages"] = []
            st.session_state["token_count"] = []
            st.rerun()

        # diplay selec model in the sidebar
        self.chat_interface.display_model_controls(self.available_models)    

        # Display chat messages using the ChatInterface
        self.chat_interface.display_messages(st.session_state.messages)

        # Chat input
        if prompt := st.chat_input("What would you like to know about your documents?"):
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)
            
            # Generate and stream response
            with st.chat_message("assistant"):
                
                # Stream the response
                full_response = st.write_stream(self._generate_response(st.session_state.messages))
            
            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": full_response}) 
        
        if st.session_state.token_count:
            st.sidebar.write("Token count:")
            total_user_prompt_tokens = sum(item["user_interaction"]["prompt_tokens"]for item in st.session_state["token_count"])
            total_user_completion_tokens = sum(item["user_interaction"]["completion_tokens"]for item in st.session_state["token_count"])
            total_user_total_tokens = sum(item["user_interaction"]["total_tokens"]for item in st.session_state["token_count"])
            total_agent_prompt_tokens = sum(item["agent_interaction"]["prompt_tokens"]for item in st.session_state["token_count"])
            total_agent_completion_tokens = sum(item["agent_interaction"]["completion_tokens"]for item in st.session_state["token_count"])
            total_agent_total_tokens = sum(item["agent_interaction"]["total_tokens"]for item in st.session_state["token_count"])

            st.sidebar.write(f"user prompt tokens: {total_user_prompt_tokens}")
            st.sidebar.write(f"user completion tokens: {total_user_completion_tokens}")
            st.sidebar.write(f"user total tokens: {total_user_total_tokens}")
            st.sidebar.write(f"Thinking prompt tokens: {total_agent_prompt_tokens}")
            st.sidebar.write(f"Thinking completion tokens: {total_agent_completion_tokens}")
            st.sidebar.write(f"Thinking total tokens: {total_agent_total_tokens}")

            if st.session_state.model.startswith("o"):
                total_agent_reasoning_tokens = sum(item["agent_interaction"]["reasoning_tokens"]for item in st.session_state["token_count"])
                st.sidebar.write(f"Reasoning tokens: {total_agent_reasoning_tokens}")

                

        if st.session_state.agent_messages:
            options=[i+1 for i in range(len(st.session_state.agent_messages))]
            index=len(options)-1
            question_selected =st.sidebar.selectbox(
                "Agent thinking steps",
                options=options,
                index=index
            )

            if question_selected:
                for message in st.session_state["agent_messages"][question_selected-1][2 * question_selected:]:
                    st.sidebar.write(message)

    