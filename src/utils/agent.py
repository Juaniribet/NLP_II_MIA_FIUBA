import openai
import os
import logging
import json
from typing import List, Dict, Optional

from pydantic import BaseModel
from typing import Literal, Optional
from pydantic import ValidationError
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

from src.utils.prompts import AGENT_PROMPT
from src.utils.config import OPENAI_API_KEY
from src.utils.models import AgentOutput

logger = logging.getLogger(__name__)

class AgentAI:
    def __init__(self):
        openai.api_key = OPENAI_API_KEY
        self.max_retries = 3
        self.retry_delay = 1
        self.known_actions = {
            "get_context_from_vector_store": self.get_context_from_vector_store
        }
        self.prompt = self._build_prompt()
        self.agent_messages = [{"role": "system", "content": self.prompt}]
        self.client = openai.OpenAI()
        self.embeddings = OpenAIEmbeddings()
        self.temp_dir = "temp_vector_store"
        self.token_count = {"user_interaction": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                            "agent_interaction": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}}

    def _build_prompt(self) -> str:
        """
        Build the system prompt for the agent.
        Loads vector store metadata from a JSON file.
        If the file or its directory does not exist, it creates them
        and initializes the file with an empty JSON object {}.
        """
        vector_stores_metadata_path = "temp_vector_store/vector_store_metadata.json"
        directory_path = os.path.dirname(vector_stores_metadata_path)

        os.makedirs(directory_path, exist_ok=True)

        try:
            with open(vector_stores_metadata_path, "r") as f:
                vector_stores = json.load(f)
        except FileNotFoundError:
            # If the file doesn't exist, create it with an empty JSON object
            print(f"Info: {vector_stores_metadata_path} not found. Creating with empty object.")
            with open(vector_stores_metadata_path, "w") as f:
                json.dump({}, f)
            # Load the newly created empty file
            with open(vector_stores_metadata_path, "r") as f:
                vector_stores = json.load(f)
        except Exception as e:
            logger.error(f"Error building prompt: {e}")
            raise

        return AGENT_PROMPT.format(vector_stores=vector_stores, 
                                   known_actions=self.known_actions.keys())
        
    def get_response(self, messages: List[Dict], model) -> str:
        """
        Get a response from OpenAI API with retry mechanism.
        
        Args:
            chat_history: List of message dictionaries
            temperature: Sampling temperature
            stream: Whether to stream the response
            
        Returns:
            str: The generated response
        """
        try:
            response = self.client.beta.chat.completions.parse(
                model=model,
                messages=messages,
                response_format=AgentOutput,
            )

            
            return response
        except Exception as e:
            logger.error(f"Failed to get response from OpenAI: {e}")
            raise

    def get_context_from_vector_store(self, vector_store_name: str, query) -> str:
        """
        Get relevant context from the vector store.
        
        Args:
            vector_store_name: Name of the vector store to query
            query: The search query
            
        Returns:
            str: Retrieved context or empty string if error
        """
        try:
            # Load the vector store by name
            load_path = os.path.join(self.temp_dir, vector_store_name)
            with open("./temp_vector_store/vector_store_metadata.json", "r") as f:
                metadata = json.load(f)
                embeddings_model = metadata.get(vector_store_name)["embedding_model"]
            print(f"Loading vector store from {load_path} with embedding model {embeddings_model}")
            embeddings = OpenAIEmbeddings(model=embeddings_model)
            vectorstore = FAISS.load_local(load_path, embeddings=embeddings, allow_dangerous_deserialization=True)
            retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 8})

            docs = retriever.invoke(query)
            
            context_parts = []
            for i, doc in enumerate(docs, 1):
                source = doc.metadata.get('source', f'Document {i}')
                page = doc.metadata.get('page', 'N/A')
                context_parts.append(f"[{i}] {doc.page_content}\nSource: {source} (Page {page})\n")
            context = "\n".join(context_parts)
            return context
        except Exception as e:
            logger.error(f"Error getting context from vector store: {e}")
            return ""
    
    def run(self, chat_history, model, max_turns: int = 15) -> Optional[str]:
        """
        Run the agent with the given question.
        """
        try:
                        
            self.agent_messages.extend(chat_history[1:])

            if model.startswith("o"):
                self.token_count["agent_interaction"]["reasoning_tokens"] = 0

            for turn in range(max_turns):
                # Get agent's response
                try:
                    response = self.get_response(self.agent_messages, model)

                    result = response.choices[0].message.parsed
                    
                    if not result:
                        logger.error("Invalid agent output format")
                        return None

                    logger.info(f"Turn {turn+1}: {result.type.upper()} - {result.content}")

                    if turn == 0:
                        self.token_count["user_interaction"]["prompt_tokens"] = response.usage.prompt_tokens

                    if (turn == 0) and (result.type == "answer"):
                        self.token_count["user_interaction"]["completion_tokens"] = response.usage.completion_tokens

                    if (turn == 0) and (result.type != "answer"):
                        self.token_count["agent_interaction"]["completion_tokens"] = response.usage.completion_tokens

                    if (turn > 0) and (result.type != "answer"):
                        self.token_count["agent_interaction"]["prompt_tokens"] += response.usage.prompt_tokens
                        self.token_count["agent_interaction"]["completion_tokens"] += response.usage.completion_tokens

                    if (turn > 0) and (result.type == "answer"):
                        self.token_count["agent_interaction"]["prompt_tokens"] += response.usage.prompt_tokens
                        self.token_count["user_interaction"]["completion_tokens"] += response.usage.completion_tokens
                    
                    if model.startswith("o"):
                        self.token_count["agent_interaction"]["reasoning_tokens"] += response.usage.completion_tokens_details.reasoning_tokens

                    
                    self.token_count["user_interaction"]["total_tokens"] = self.token_count["user_interaction"]["prompt_tokens"] + self.token_count["user_interaction"]["completion_tokens"]
                    self.token_count["agent_interaction"]["total_tokens"] = self.token_count["agent_interaction"]["prompt_tokens"] + self.token_count["user_interaction"]["completion_tokens"]

    
                    if result.type == "answer":
                        agent_message = {"role": "assistant", "content": json.dumps({
                                                                                    "type": result.type,
                                                                                    "content": result.content
                                                                                })}
                        self.agent_messages.append(agent_message)
                        
                        return result.content
                        
                    elif result.type == "action":                    

                        action_name, action_param = result.function_name, result.parameters

                        question = action_param.question
                        vector_store_name = action_param.vector_store_name

                        agent_message = {"role": "assistant", "content": json.dumps({
                                                                                    "type": result.type,
                                                                                    "function_name": action_name,
                                                                                    "parameters": {
                                                                                        "question": question,
                                                                                        "vector_store_name": vector_store_name
                                                                                    }

                                                                                })}
                        self.agent_messages.append(agent_message)
                        
                        if action_name not in self.known_actions:
                            error_msg = f"Unknown action: {action_name}"
                            logger.error(error_msg)
                            # Add error as user message and continue
                            self.agent_messages.append({"role": "assistant", 
                                                        "content": f"Error: {error_msg}. Available actions are: {list(self.known_actions.keys())}"})
                            continue
                        
                        # Execute action and get observation
                        observation = self.known_actions[action_name](vector_store_name, question)
                        # Add observation to message history
                        self.agent_messages.append({"role": "assistant", 
                                                    "content": f"Observation: {observation}"})
                        logger.info(f"Observation: {observation[:100]}...")
                        
                    elif result.type == "thought":
                        agent_message = {"role": "assistant", "content": json.dumps({
                                                                                        "type": result.type,
                                                                                        "content": result.content
                                                                                    })}
                        self.agent_messages.append(agent_message)
                        pass
                    
                    else:
                        logger.error(f"Unknown result type: {result.type}")
                        return None
                    
                except ValidationError as e:
                    
                    self.agent_messages.append({
                        "role": "user",
                        "content": f"""Your last response did not validate against the expected JSON schema.
            Please correct the JSON output to match the {AgentOutput.__name__} model structure precisely.
            ValidationError: {e}"""})
                    continue
                    
            logger.warning(f"Maximum number of turns ({max_turns}) reached without a final answer")
            return "I wasn't able to find a definitive answer within the allowed reasoning steps."
            
        except Exception as e:
            logger.error(f"Error running agent: {e}")
            return f"An error occurred: {str(e)}"

