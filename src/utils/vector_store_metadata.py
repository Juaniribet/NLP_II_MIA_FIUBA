import json
import os
from typing import Dict

class VectorStoreMetadata:
    def __init__(self, vector_store_dir: str = "temp_vector_store"):
        self.vector_store_dir = vector_store_dir
        self.metadata_file = os.path.join(vector_store_dir, "vector_store_metadata.json")
        self._ensure_metadata_file()

    def _ensure_metadata_file(self):
        """Ensure the metadata file exists."""
        # Ensure vector store directory exists
        if not os.path.exists(self.vector_store_dir):
            os.makedirs(self.vector_store_dir)
        
        # Create metadata file if it doesn't exist
        if not os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'w') as f:
                json.dump({}, f)

    def add_vector_store(self, name: str, description: str, embedding_model: str) -> bool:
        """
        Add a new vector store to the metadata file.
        
        Args:
            name: Name of the vector store
            description: Description of the vector store
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Read existing metadata
            with open(self.metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Add new vector store
            metadata[name] = {"description" : description, "embedding_model" : embedding_model}
            
            # Write updated metadata
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata, f, indent=4)
            
            return True
        except Exception as e:
            print(f"Error adding vector store metadata: {e}")
            return False

    def get_vector_store_description(self, name: str) -> str:
        """
        Get the description of a vector store.
        
        Args:
            name: Name of the vector store
            
        Returns:
            str: Description of the vector store, or empty string if not found
        """
        try:
            with open(self.metadata_file, 'r') as f:
                metadata = json.load(f)
            return metadata.get(name, "")
        except Exception as e:
            print(f"Error getting vector store description: {e}")
            return ""

    def list_vector_stores(self) -> Dict[str, str]:
        """
        Get all vector stores and their descriptions.
        
        Returns:
            Dict[str, str]: Dictionary of vector store names and descriptions
        """
        try:
            with open(self.metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Filter out vector stores that don't exist in the directory
            existing_stores = {}
            for name, description in metadata.items():
                store_path = os.path.join(self.vector_store_dir, name)
                if os.path.exists(store_path):
                    existing_stores[name] = description
                else:
                    # Remove non-existent vector store from metadata
                    self.delete_vector_store(name)
            
            return existing_stores
        except Exception as e:
            print(f"Error listing vector stores: {e}")
            return {}

    def delete_vector_store(self, name: str) -> bool:
        """
        Delete a vector store from the metadata file.
        
        Args:
            name: Name of the vector store to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Read existing metadata
            with open(self.metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Remove vector store if it exists
            if name in metadata:
                del metadata[name]
                
                # Write updated metadata
                with open(self.metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=4)
                
                return True
            return False
        except Exception as e:
            print(f"Error deleting vector store metadata: {e}")
            return False 