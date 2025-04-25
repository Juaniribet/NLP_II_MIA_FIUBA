import streamlit as st
import os
import re
import unicodedata
from typing import Optional, List, Dict
from src.auth.auth_handler import is_authenticated
from src.utils.vector_store_creator import VectorStoreCreator
from src.utils.vector_store_metadata import VectorStoreMetadata

class UploadPage:
    def __init__(self):
        self.allowed_extensions = ['.txt', '.pdf', '.doc', '.docx']
        self.upload_path = "uploads"
        self._ensure_upload_directory()
        self.vector_store_creator = VectorStoreCreator()
        self.vector_store_metadata = VectorStoreMetadata()
        self.available_embedding_models = [
            "text-embedding-3-small",
            "text-embedding-3-large",
            "text-embedding-ada-002"
        ]

    def _ensure_upload_directory(self):
        """Ensure the upload directory exists."""
        if not os.path.exists(self.upload_path):
            os.makedirs(self.upload_path)

    def _is_valid_file(self, file) -> bool:
        """Check if the file has an allowed extension."""
        if file is None:
            return False
        file_ext = os.path.splitext(file.name)[1].lower()
        return file_ext in self.allowed_extensions
    
    def _sanitize_name(self, name: str) -> str:
        """
        Sanitizes a filename to make it safe for use on most filesystems.
        
        - Converts accented characters to their ASCII equivalents.
        - Removes invalid characters.
        - Replaces spaces and special characters with underscores.
        - Collapses multiple underscores into one.
        - Trims leading/trailing underscores and periods.
        
        Args:
            name (str): The original filename.

        Returns:
            str: A sanitized version of the filename.
        """
        if not isinstance(name, str):
            raise TypeError("Filename must be a string.")

        try:
            name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
        except Exception:
            pass  # If normalization fails, keep the original

        name = name.strip()
        name = name.replace(" ", "_")
        name = re.sub(r'[^a-zA-Z0-9_.-]+', '_', name)
        name = re.sub(r'_+', '_', name)
        name = name.strip('._')

        return name
    
    def _save_uploaded_file(self, uploaded_file) -> Optional[str]:
        """Save the uploaded file and return its path."""
        if uploaded_file is None:
            return None
            
        file_path = os.path.join(self.upload_path, uploaded_file.name)
        try:
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            return file_path
        except Exception as e:
            st.error(f"Error saving file: {str(e)}")
            return None

    def _display_vector_store_params(self):
        """Display vector store parameters in the sidebar."""
        st.sidebar.title("Vector Store Parameters")
        
        # Embedding model selection
        st.session_state.vector_store_params["embedding_model"] = st.sidebar.selectbox(
            "Embedding Model",
            self.available_embedding_models,
            index=self.available_embedding_models.index(
                st.session_state.vector_store_params["embedding_model"]
            )
        )
        
        # Chunk size and overlap
        col1, col2 = st.sidebar.columns(2)
        with col1:
            st.session_state.vector_store_params["chunk_size"] = st.number_input(
                "Chunk Size (chars)",
                min_value=100,
                max_value=2000,
                value=st.session_state.vector_store_params["chunk_size"],
                step=100,
                help="Number of characters in each text chunk. Larger chunks capture more context but may be less precise."
            )
        with col2:
            st.session_state.vector_store_params["chunk_overlap"] = st.number_input(
                "Overlap (chars)",
                min_value=0,
                max_value=500,
                value=st.session_state.vector_store_params["chunk_overlap"],
                step=50,
                help="Number of characters that overlap between consecutive chunks. Helps maintain context between chunks."
            )
        
        # Vector store name (required)
        st.session_state.vector_store_params["store_name"] =self._sanitize_name(
            st.sidebar.text_input(
            "Vector Store Name *",
            value=st.session_state["vector_store_name"],
            help="Name for the vector store. This will be used to save and load the store.",
            placeholder=st.session_state["vector_store_name"]
        )
        )

        # Vector store description (required)
        st.session_state.vector_store_params["store_description"] = st.sidebar.text_input(
            "Vector Store Description *",
            value=st.session_state["vector_store_description"]['description'],
            help="Description for the vector store. This will be used to save and load the store.",
            placeholder=st.session_state["vector_store_description"]
        )


    def _create_vector_store(self, file_paths: List[str]) -> bool:
        """Create a vector store from the uploaded files."""
        try:
            # Validate required fields
            if not st.session_state.vector_store_params.get("store_name"):
                st.error("Vector store name is required. Please enter a name for your vector store.")
                return False
            if not st.session_state.vector_store_params.get("store_description"):
                st.error("Vector store description is required. Please enter a description for your vector store.")
                return False

            with st.spinner("Creating vector store..."):
                # Update vector store creator parameters
                self.vector_store_creator.split_documents(
                    chunk_size=st.session_state.vector_store_params["chunk_size"],
                    chunk_overlap=st.session_state.vector_store_params["chunk_overlap"]
                )
                
                vector_store = self.vector_store_creator.process_files(
                    file_paths,
                    name=st.session_state.vector_store_params["store_name"]
                )
                if vector_store:
                    # Save vector store metadata
                    if not self.vector_store_metadata.add_vector_store(
                        st.session_state.vector_store_params["store_name"],
                        st.session_state.vector_store_params["store_description"],
                        st.session_state.vector_store_params["embedding_model"]
                    ):
                        st.error("Failed to save vector store metadata.")
                        return False

                    st.session_state.vector_store = vector_store
                    st.session_state["vector_store"] = vector_store  # Ensure both formats are set
                    st.session_state.vector_store_name = st.session_state.vector_store_params["store_name"]
                    st.success("Vector store created successfully!")
                    return True
                else:
                    st.error("Failed to create vector store from the uploaded files.")
                    return False
        except Exception as e:
            st.error(f"Error creating vector store: {str(e)}")
            return False

    def _get_documents_from_vector_store(self) -> List[Dict]:
        """Get unique documents from the current vector store."""
        if "vector_store" not in st.session_state or st.session_state.vector_store is None:
            return []
        
        try:
            # Get all documents from the vector store
            docs = st.session_state.vector_store.docstore._dict.values()
            
            # Create a dictionary to store unique documents by source
            unique_docs = {}
            for doc in docs:
                source = doc.metadata.get('source', 'Unknown')
                if source not in unique_docs:
                    unique_docs[source] = {
                        'source': source,
                        'pages': set()
                    }
                unique_docs[source]['pages'].add(doc.metadata.get('page', 0))
            
            # Convert to list and sort by source name
            return sorted(
                [{'source': doc['source'], 'pages': sorted(doc['pages'])} 
                 for doc in unique_docs.values()],
                key=lambda x: x['source']
            )
        except Exception as e:
            print(f"Error getting documents from vector store: {e}")
            return []


    def _display_vector_store_management(self):
        """Display vector store management options."""
        st.sidebar.title("Vector Store Management")
        
        # Create new vector store button
        if st.sidebar.button("Create New Vector Store", key="new_vector_store"):
            # Clear current vector store and uploaded files
            if "vector_store" in st.session_state:
                del st.session_state.vector_store
            st.session_state.uploaded_files = []
            st.session_state.vector_store_params["store_name"] = ""
            st.session_state.vector_store_params["store_description"] = ""
            st.success("Ready to create a new vector store!")
            st.rerun()
        
        # List available vector stores with descriptions
        available_stores = self.vector_store_metadata.list_vector_stores()
        if available_stores:
            st.sidebar.write("Available Vector Stores:")
            for store_name, description in available_stores.items():
                with st.sidebar.expander(f"📄 {store_name}"):
                    st.write(f"Description: {description}")
                    if st.button("Delete", key=f"delete_{store_name}"):
                        # Delete both the vector store and its metadata
                        if self.vector_store_creator.delete_vector_store(store_name):
                            self.vector_store_metadata.delete_vector_store(store_name)
                            # If the deleted store was the current one, clear it from session state
                            if st.session_state.get("vector_store_name") == store_name:
                                if "vector_store" in st.session_state:
                                    del st.session_state.vector_store
                                st.session_state.vector_store_name = ""
                            st.rerun()
        
        # Load vector store
        if available_stores:
            selected_store = st.sidebar.selectbox(
                "Load Vector Store",
                options=list(available_stores.keys()),
                index=0
            )
            if st.sidebar.button("Load Selected Store"):
                vector_store = self.vector_store_creator.load_vector_store(selected_store)
                if vector_store:
                    st.session_state.vector_store = vector_store
                    st.session_state["vector_store"] = vector_store
                    st.session_state["vector_store_description"] = self.vector_store_metadata.get_vector_store_description(selected_store)
                    st.session_state.vector_store_name = selected_store
                    # Update chat messages with new vector store name
                    st.success(f"Loaded vector store: {selected_store}")
                    st.rerun()  # Force a rerun to update the document display
                else:
                    st.error("Failed to load vector store")

    def render(self):
        """Render the upload page."""
        st.title("File Upload")
        
        if not is_authenticated():
            st.warning("Please log in to upload files.")
            return

        # Display documents from current vector store
        if "vector_store" in st.session_state and st.session_state.vector_store is not None:
            st.session_state["vector_store_description"] = self.vector_store_metadata.get_vector_store_description(st.session_state.vector_store_name)
            st.subheader("Documents in Current Vector Store")
            documents = self._get_documents_from_vector_store()
            if documents:
                for doc in documents:
                    with st.expander(f"📄 {doc['source']}"):
                        st.write(f"Pages: {', '.join(map(str, doc['pages']))}")
            
            else:
                st.info("No documents found in the current vector store.")
        else:
            st.session_state["vector_store_name"] = ""
            st.session_state["vector_store_description"] = ""

        # Display current uploaded files
        if st.session_state.uploaded_files:
            st.write("Currently uploaded files:")
            for file_path in st.session_state.uploaded_files:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.text(os.path.basename(file_path))
                with col2:
                    if st.button("Remove", key=f"remove_{file_path}"):
                        st.session_state.uploaded_files.remove(file_path)
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        # Reset vector store if files are removed
                        if "vector_store" in st.session_state:
                            del st.session_state.vector_store
                        st.rerun()

        st.write("Upload your documents here. Supported formats: " + ", ".join(self.allowed_extensions))

        # Display vector store parameters in sidebar
        self._display_vector_store_params()
        
        uploaded_files = st.file_uploader(
            "Choose files",
            type=[ext[1:] for ext in self.allowed_extensions],  # Remove dots from extensions
            accept_multiple_files=True
        )

        if uploaded_files:
            st.write("Selected files:")
            for file in uploaded_files:
                st.json({
                    "filename": file.name,
                    "size": f"{file.size / 1024:.2f} KB",
                    "type": file.type
                })

            if st.sidebar.button("Create Vector Store"):
                valid_files = [file for file in uploaded_files if self._is_valid_file(file)]
                if valid_files:
                    with st.spinner("Uploading files..."):
                        saved_paths = []
                        for file in valid_files:
                            saved_path = self._save_uploaded_file(file)
                            if saved_path:
                                if saved_path not in st.session_state.uploaded_files:
                                    st.session_state.uploaded_files.append(saved_path)
                                saved_paths.append(saved_path)
                        
                        if saved_paths:
                            # Create or update vector store
                            if self._create_vector_store(st.session_state.uploaded_files):
                                st.success("Files uploaded and vector store created successfully!")
                                st.rerun()  # Force a rerun to update the chat window
                            else:
                                st.error("Files uploaded but vector store creation failed.")
                else:
                    st.error("No valid files selected. Please upload supported file formats.") 
        
        
        
        # Display vector store management options
        self._display_vector_store_management()