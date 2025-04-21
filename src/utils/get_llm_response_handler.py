import openai
from typing import List, Dict, Optional, Generator
import time
from src.utils.config import OPENAI_API_KEY, GEMINI_API_KEY
import logging
import google.generativeai as genai
import re

logger = logging.getLogger(__name__)

class LLMResponseHandler:
    def __init__(self):
        openai.api_key = OPENAI_API_KEY
        genai.configure(api_key=GEMINI_API_KEY)
        self.max_retries = 3
        self.retry_delay = 1

    def get_response(self, chat_history: List[Dict], model: str, temperature: float = 0.7, stream: bool = False) -> str:
        """
        Get a response from the appropriate LLM API with retry mechanism.
        
        Args:
            chat_history: List of message dictionaries
            model: The model to use
            temperature: Sampling temperature
            stream: Whether to stream the response
            
        Returns:
            str: The generated response
        """
        # Handle different model types
        if model.lower().startswith("gemini"):
            return self._get_gemini_response(chat_history, model, temperature, stream)
        else:
            return self._get_openai_response(chat_history, model, temperature, stream)

    def _get_openai_response(self, chat_history: List[Dict], model: str, temperature: float, stream: bool) -> str:
        """Get response from OpenAI models."""
        for attempt in range(self.max_retries):
            try:
                response = openai.chat.completions.create(
                    model=model,
                    messages=chat_history,
                    temperature=temperature,
                    max_tokens=500,
                    stream=stream
                )
                if stream:
                    return response
                return response.choices[0].message.content
            except Exception as e:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise Exception(f"Failed to get response from OpenAI: {str(e)}")

    def _get_gemini_response(self, chat_history: List[Dict], model: str, temperature: float, stream: bool) -> str:
        """Get response from Gemini models."""
        try:
            # Configure Gemini model
            gemini_model = genai.GenerativeModel(
                model,
                generation_config=genai.GenerationConfig(
                    temperature=temperature
                )
            )
            
            # Convert chat history to Gemini format
            gemini_history = []
            for message in chat_history[:-1]:
                role = message['role']
                content = message['content']
                # Gemini uses 'model' instead of 'assistant'
                if role == 'assistant':
                    role = 'model'
                gemini_history.append({'role': role, 'parts': [content]})
            
            # Start chat session
            chat = gemini_model.start_chat(history=gemini_history)
            
            # Get response
            response = chat.send_message(chat_history[-1]['content'])
            
            if stream:
                # For streaming, return a generator
                def stream_generator():
                    for word in response.text.split():
                        yield word + " "
                return stream_generator()
            else:
                return response.text
                
        except Exception as e:
            raise Exception(f"Failed to get response from Gemini: {str(e)}")

    def contextualize_question(self, chat_history: List[Dict], model: str) -> str:
        """
        Reformulate the user's question to be standalone.
        
        Args:
            chat_history: List of message dictionaries
            model: The model to use for reformulation
            
        Returns:
            str: Reformulated question
        """
        system_prompt = """Given a chat history and the latest user question which might 
        reference context in the chat history, formulate a standalone question which can 
        be understood without the chat history. Do NOT answer the question, just reformulate 
        it if needed and otherwise return it as is."""

        messages = [{
            "role": "system",
            "content": f"{system_prompt}\n\nChat history:\n{chat_history[:-1]}\n\nLatest question: {chat_history[-1]['content']}"
        }]

        return self.get_response(messages, model, temperature=0)

    def get_rag_response(self, chat_history: List[Dict], model: str, temperature: float = 0.5, context: str = "", stream: bool = False) -> str:
        """
        Get a RAG-enhanced response from the appropriate LLM API.
        
        Args:
            chat_history: List of message dictionaries
            model: The model to use
            temperature: Sampling temperature
            context: Retrieved context for RAG
            stream: Whether to stream the response
            
        Returns:
            str: The generated response
        """
        if len(chat_history) > 2:
            user_question = self.contextualize_question(chat_history, model)
        else:
            user_question = chat_history[-1]["content"]

        prompt = f"""You are an assistant for question-answering tasks.
        Use the following pieces of retrieved context to answer the question.
        If you don't know the answer, say that you don't know.
        
        Context:
        {context}
        
        Question: {user_question}
        
        Remember:
        1. Only use the context to answer the question. If the question has no relation with the context, just say that you can't answer based on the context.
        2. For each piece of information you use from the context, add a reference in square brackets like [1], [2], etc. at the end of the relevant sentence.
        3. At the end of your response, add a "Sources:" section that lists the references with their corresponding document names.
        4. If you don't use any context, don't add any references.
        """

        messages = [{"role": "user", "content": prompt}]
        return self.get_response(messages, model, temperature, stream)

    def stream_response(self, response_stream) -> Generator[str, None, None]:
        """
        Stream the response from the LLM API.
        
        Args:
            response_stream: The streaming response from the LLM
            
        Yields:
            str: The next chunk of the response
        """
        try:
            if isinstance(response_stream, Generator):
                # Handle Gemini streaming
                for chunk in response_stream:
                    yield chunk
            else:
                # Handle OpenAI streaming
                for chunk in response_stream:
                    if chunk.choices[0].delta.content is not None:
                        yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Error streaming response: {e}")
            yield "Error streaming response. Please try again." 