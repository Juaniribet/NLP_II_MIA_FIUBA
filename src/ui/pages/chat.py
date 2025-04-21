import streamlit as st
from src.ui.components.chat_interface import ChatInterface
from src.utils.get_llm_response_handler import LLMResponseHandler
from src.utils.config import UI_CONFIG
from src.auth.auth_handler import is_authenticated
from typing import Generator

class ChatPage:
    def __init__(self):
        self.chat_interface = ChatInterface()
        self.llm_handler = LLMResponseHandler()
        self.available_models = UI_CONFIG["available_models"]
        self._initialize_session_state()

    def _initialize_session_state(self):
        """Initialize session state variables."""
        if "model" not in st.session_state:
            st.session_state.model = self.available_models[0]
        if "temperature" not in st.session_state:
            st.session_state.temperature = 0.7
        if "vector_store_name" not in st.session_state:
            st.session_state.vector_store_name = "default"
        if "messages" not in st.session_state:
            st.session_state.messages = [{
                "role": "assistant",
                "content": f"Hello {st.session_state.user['user_id'].capitalize()}! I'm your AI assistant to answer questions about the documents in the Knowledgebase: {st.session_state.vector_store_name}"
            }]

    def _display_model_controls(self):
        """Display model selection and temperature controls in the sidebar."""
        st.sidebar.title("Model Settings")
        
        # Model selection
        st.session_state.model = st.sidebar.selectbox(
            "Select Model",
            options=self.available_models,
            index=self.available_models.index(st.session_state.model) if st.session_state.model in self.available_models else 0
        )
        
        # Temperature control
        st.session_state.temperature = st.sidebar.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=st.session_state.temperature,
            step=0.1,
            help="Higher values make the output more random, lower values make it more deterministic."
        )

    def _get_context_from_vector_store(self, query: str) -> str:
        """Get relevant context from the vector store."""
        if "vector_store" not in st.session_state:
            return ""
        
        try:
            # Get the most relevant documents
            docs = st.session_state.vector_store.similarity_search(query, k=3)
            # Combine the content of the documents with source information
            context_parts = []
            for i, doc in enumerate(docs, 1):
                source = doc.metadata.get('source', f'Document {i}')
                page = doc.metadata.get('page', 'N/A')
                context_parts.append(f"[{i}] {doc.page_content}\nSource: {source} (Page {page})\n")
            context = "\n".join(context_parts)
            return context
        except Exception as e:
            print(f"Error getting context from vector store: {e}")
            return ""

    def _generate_response(self, prompt: str, context: str) -> Generator[str, None, str]:
        """Generate a response using the selected model with RAG."""
        try:
            # Get the current chat history
            chat_history = st.session_state.messages.copy()
            
            # Add the current prompt to the chat history
            chat_history.append({"role": "user", "content": prompt})
            
            # Get the selected model
            model = st.session_state.model
            
            # Get RAG response using the LLM handler
            response_stream = self.llm_handler.get_rag_response(
                chat_history=chat_history,
                model=model,
                temperature=st.session_state.temperature,
                context=context,
                stream=True
            )
            
            # Stream the response
            full_response = ""
            for chunk in self.llm_handler.stream_response(response_stream):
                full_response += chunk
                yield chunk
            
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

        # Check if vector store exists
        if "vector_store" not in st.session_state or st.session_state.vector_store is None:
            st.info("Please upload some documents or load an existing vector store to start chatting.")
            return

        # Display model controls in sidebar
        self._display_model_controls()

        # Add new chat button in the sidebar
        if st.sidebar.button("New Chat", key="new_chat_button"):
            st.session_state.messages = [{
                "role": "assistant",
                "content": f"Hello {st.session_state.user['user_id'].capitalize()}! I'm your AI assistant to answer questions about the documents in the Knowledgebase: {st.session_state.vector_store_name}"
            }]
            st.rerun()

        # Display chat messages using the ChatInterface
        self.chat_interface.display_messages(st.session_state.messages)

        # Chat input
        if prompt := st.chat_input("What would you like to know about your documents?"):
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Get context from vector store
            context = self._get_context_from_vector_store(prompt)
            
            # Generate and stream response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    message_placeholder = st.empty()
                    full_response = ""
                    
                    # Stream the response
                    for chunk in self._generate_response(prompt, context):
                        full_response += chunk
                        message_placeholder.markdown(full_response + "▌")
                    
                    message_placeholder.markdown(full_response)
            
            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": full_response}) 