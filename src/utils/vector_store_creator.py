import os
from dotenv import load_dotenv
from typing import List, Optional
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredPowerPointLoader,
)
from langchain.docstore.document import Document
from src.utils.config import OPENAI_API_KEY
import openai
from langchain_openai import OpenAIEmbeddings
import streamlit as st

load_dotenv()
openai.api_key = OPENAI_API_KEY

class VectorStoreCreator:
    """
    A class to create and manage persistent FAISS vector stores.
    """
    def __init__(self):
        openai.api_key = OPENAI_API_KEY
        self.documents: Optional[List[Document]] = None
        self.split_docs: Optional[List[Document]] = None
        self.db: Optional[FAISS] = None
        self.temp_dir = "temp_vector_store"
        self._ensure_temp_directory()
        self.embeddings = OpenAIEmbeddings(model=st.session_state.vector_store_params["embedding_model"])

    def _ensure_temp_directory(self):
        """Ensure the temporary directory exists."""
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)

    def save_vector_store(self, name: str = "default", vectorstore: FAISS = None):
        """Save the current vector store to disk."""
        if self.db is None:
            raise ValueError("No vector store to save")
        
        save_path = os.path.join(self.temp_dir, name)
        vectorstore.save_local(save_path)
        print(f"Vector store saved to {save_path}")

    def load_vector_store(self, name: str = "default") -> Optional[FAISS]:
        """Load a vector store from disk."""
        try:
            load_path = os.path.join(self.temp_dir, name)
            if not os.path.exists(load_path):
                return None
            
            embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=os.getenv("OPENAI_API_KEY")
            )
            self.db = FAISS.load_local(load_path, embeddings, allow_dangerous_deserialization=True)
            return self.db
        except Exception as e:
            print(f"Error loading vector store: {e}")
            return None

    def delete_vector_store(self, name: str = "default"):
        """Delete a vector store from disk."""
        try:
            store_path = os.path.join(self.temp_dir, name)
            if os.path.exists(store_path):
                import shutil
                shutil.rmtree(store_path)
                print(f"Vector store {name} deleted")
        except Exception as e:
            print(f"Error deleting vector store: {e}")

    def list_vector_stores(self) -> List[str]:
        """List all available vector stores."""
        try:
            return [d for d in os.listdir(self.temp_dir) 
                   if os.path.isdir(os.path.join(self.temp_dir, d))]
        except Exception as e:
            print(f"Error listing vector stores: {e}")
            return []

    def load_documents(self, file_paths: List[str]) -> List[Document]:
        """
        Loads documents from the file paths.
        """
        self.documents = []
        for file_path in file_paths:
            if not os.path.exists(file_path):
                continue

            _, file_extension = os.path.splitext(file_path.lower())
            loader = None

            try:
                if file_extension == ".pdf":
                    loader = PyPDFLoader(file_path)
                elif file_extension == ".txt":
                    loader = TextLoader(file_path, encoding="utf-8")
                elif file_extension == ".docx":
                    loader = UnstructuredWordDocumentLoader(file_path)
                elif file_extension == ".pptx":
                    loader = UnstructuredPowerPointLoader(file_path)
                else:
                    continue

                loaded_docs = loader.load()
                for i, doc in enumerate(loaded_docs):
                    if isinstance(doc, Document) and hasattr(doc, 'metadata'):
                        doc.metadata['source'] = os.path.basename(file_path)
                        # Add page number for PDFs
                        if file_extension == ".pdf" and hasattr(doc, 'metadata'):
                            doc.metadata['page'] = i + 1
                        # For other document types, we'll use the chunk number as a pseudo-page
                        else:
                            doc.metadata['page'] = i + 1

                self.documents.extend(loaded_docs)

            except Exception as e:
                print(f"Error loading file {file_path}: {e}")
                continue

        return self.documents

    def split_documents(self,
                       chunk_size: int = 1000,
                       chunk_overlap: int = 200) -> List[Document]:
        """
        Splits the loaded documents into smaller chunks.
        """
        if not self.documents:
            return []

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
            length_function=len,
        )

        self.split_docs = text_splitter.split_documents(self.documents)
        return self.split_docs

    def create_vector_store(self,
                          embedding_model_name: str = "text-embedding-3-small",
                          name: str = "default") -> Optional[FAISS]:
        """
        Creates embeddings for the split documents and returns the FAISS index.
        """
        if not self.split_docs:
            print("No split documents available for vector store creation")
            return None

        try:
            print(f"Creating embeddings using model: {embedding_model_name}")

            self.db = FAISS.from_documents(self.split_docs, self.embeddings)
            self.save_vector_store(name, self.db)
            return self.db

        except Exception as e:
            print(f"Error creating vector store: {str(e)}")
            return None

    def add_documents_to_vector_store(self, 
                                    documents: List[Document],
                                    embedding_model_name: str = "text-embedding-3-small") -> bool:
        """
        Add new documents to an existing vector store.
        
        Args:
            documents: List of documents to add
            embedding_model_name: Name of the embedding model to use
            
        Returns:
            bool: True if documents were added successfully, False otherwise
        """
        if not self.db:
            print("No vector store available to add documents to")
            return False
            
        try:
            print(f"Adding {len(documents)} documents to existing vector store")
            embeddings = OpenAIEmbeddings(
                model=embedding_model_name,
                openai_api_key=OPENAI_API_KEY
            )
            
            # Add documents to existing vector store
            self.db.add_documents(documents)
            return True
            
        except Exception as e:
            print(f"Error adding documents to vector store: {str(e)}")
            return False

    def process_files(self, file_paths: List[str], name: str = "default") -> Optional[FAISS]:
        """
        Process files and create or update a vector store.
        If a vector store with the given name exists, new documents will be added to it.
        """
        try:
            print(f"Starting to process {len(file_paths)} files")
            
            # Load new documents
            new_documents = self.load_documents(file_paths)
            if not new_documents:
                print("No documents were loaded successfully")
                return None
            print(f"Successfully loaded {len(new_documents)} documents")

            # Split the new documents
            self.split_documents()
            if not self.split_docs:
                print("No documents were split successfully")
                return None
            print(f"Successfully split documents into {len(self.split_docs)} chunks")

            # Check if vector store exists
            existing_store = self.load_vector_store(name)
            if existing_store:
                print(f"Adding documents to existing vector store: {name}")
                # Add new documents to existing store
                if self.add_documents_to_vector_store(self.split_docs):
                    self.save_vector_store(name, self.db)
                    return self.db
                else:
                    print("Failed to add documents to existing vector store")
                    return None
            else:
                print(f"Creating new vector store: {name}")
                # Create new vector store
                return self.create_vector_store(name=name)

        except Exception as e:
            print(f"Error processing files: {str(e)}")
            return None

    def cleanup(self):
        """Clean up temporary files and reset state."""
        self.documents = None
        self.split_docs = None
        self.db = None
        # Optionally clean up temp directory
        # if os.path.exists(self.temp_dir):
        #     shutil.rmtree(self.temp_dir)
