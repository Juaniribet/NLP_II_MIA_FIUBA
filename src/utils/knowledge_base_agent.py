from typing import List, Dict, Optional
from pydantic import BaseModel
from openai import OpenAI
from src.utils.vector_store_creator import VectorStoreCreator
from src.utils.get_llm_response_handler import LLMResponseHandler
import os

class KnowledgeBase(BaseModel):
    name: str
    description: str
    vector_store: Optional[object] = None

class KnowledgeBaseAgent:
    def __init__(self):
        self.vector_store_creator = VectorStoreCreator()
        self.llm_handler = LLMResponseHandler()
        self.client = OpenAI()
        self.knowledge_bases: Dict[str, KnowledgeBase] = {}
        self._load_existing_knowledge_bases()

    def _load_existing_knowledge_bases(self):
        """Load all existing vector stores as knowledge bases."""
        available_stores = self.vector_store_creator.list_vector_stores()
        for store_name in available_stores:
            vector_store = self.vector_store_creator.load_vector_store(store_name)
            if vector_store:
                # Get a sample document to generate description
                docs = vector_store.similarity_search("", k=1)
                description = docs[0].page_content[:200] + "..." if docs else "No description available"
                
                self.knowledge_bases[store_name] = KnowledgeBase(
                    name=store_name,
                    description=description,
                    vector_store=vector_store
                )

    def select_knowledge_base(self, question: str) -> Optional[KnowledgeBase]:
        """
        Use LLM to select the most appropriate knowledge base for the question.
        """
        if not self.knowledge_bases:
            return None

        # Create a prompt with available knowledge bases
        knowledge_base_info = "\n".join([
            f"- {kb.name}: {kb.description[:200]}..."
            for kb in self.knowledge_bases.values()
        ])

        prompt = f"""Given the following question and available knowledge bases, select the most appropriate one to answer the question.
        If none of the knowledge bases seem relevant, respond with 'none'.

        Question: {question}

        Available Knowledge Bases:
        {knowledge_base_info}

        Respond with only the name of the selected knowledge base or 'none' if none are appropriate.
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-2024-08-06",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that selects the most appropriate knowledge base for answering questions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0
            )
            
            selected_name = response.choices[0].message.content.strip()
            
            if selected_name.lower() == 'none':
                return None
                
            return self.knowledge_bases.get(selected_name)
            
        except Exception as e:
            print(f"Error selecting knowledge base: {e}")
            return None

    def get_rag_response(self, question: str, knowledge_base: KnowledgeBase) -> str:
        """
        Get a RAG-enhanced response using the selected knowledge base.
        """
        if not knowledge_base or not knowledge_base.vector_store:
            return "I don't have access to the appropriate knowledge base to answer this question."

        try:
            # Get relevant context from the vector store
            docs = knowledge_base.vector_store.similarity_search(question, k=3)
            context = "\n\n".join([doc.page_content for doc in docs])

            # Get RAG response using the LLM handler
            chat_history = [{"role": "user", "content": question}]
            response = self.llm_handler.get_rag_response(
                chat_history=chat_history,
                model="gpt-4o-2024-08-06",
                temperature=0.7,
                context=context
            )

            return response

        except Exception as e:
            print(f"Error getting RAG response: {e}")
            return "I encountered an error while trying to answer your question."

    def answer_question(self, question: str) -> str:
        """
        Main method to answer a question using the most appropriate knowledge base.
        """
        # Select the most appropriate knowledge base
        selected_kb = self.select_knowledge_base(question)
        
        if not selected_kb:
            return "I don't have access to the appropriate knowledge base to answer this question."
        
        # Get RAG response using the selected knowledge base
        return self.get_rag_response(question, selected_kb)

    def add_knowledge_base(self, name: str, vector_store: object) -> bool:
        """
        Add a new knowledge base to the agent.
        """
        try:
            # Get a sample document to generate description
            docs = vector_store.similarity_search("", k=1)
            description = docs[0].page_content[:200] + "..." if docs else "No description available"
            
            self.knowledge_bases[name] = KnowledgeBase(
                name=name,
                description=description,
                vector_store=vector_store
            )
            return True
        except Exception as e:
            print(f"Error adding knowledge base: {e}")
            return False

    def remove_knowledge_base(self, name: str) -> bool:
        """
        Remove a knowledge base from the agent.
        """
        try:
            if name in self.knowledge_bases:
                del self.knowledge_bases[name]
                return True
            return False
        except Exception as e:
            print(f"Error removing knowledge base: {e}")
            return False 