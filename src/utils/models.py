from pydantic import BaseModel, model_validator, Field, ConfigDict
from typing import Literal, Optional

# 1. Define a specific Pydantic model for the action's parameters
class GetContextParameters(BaseModel):
    """Defines the expected parameters for the get_context_from_vector_store action."""
    question: str = Field(..., description="The precise question to ask the vector store.")
    vector_store_name: str = Field(..., description="The exact name of the vector store to query.")

    # Pydantic V2 configuration to disallow extra fields in the JSON schema
    model_config = ConfigDict(extra='forbid')


# 2. Define the AgentOutput model with proper validation
class AgentOutput(BaseModel):
    """Represents the structured output expected from the AI agent."""
    type: Literal["thought", "answer", "action"]
    content: Optional[str]
    function_name: Optional[Literal["get_context_from_vector_store"]]
    parameters: Optional[GetContextParameters]

    # Pydantic V2 configuration
    model_config = ConfigDict(extra='forbid')

    @model_validator(mode='after')
    def validate_structure(self):
        """Ensures that fields are set correctly based on the 'type'."""
        # For thought/answer types
        if self.type in ("thought", "answer"):
            # Content must be present and non-empty
            if not self.content:
                raise ValueError(f"'content' must be present and non-empty when type is '{self.type}'")
        
        # For action type
        elif self.type == "action":
            # Content must be None
            if self.content is not None:
                raise ValueError("'content' must be None when type is 'action'")
            
            # function_name must be the specific value
            if self.function_name != "get_context_from_vector_store":
                raise ValueError("'function_name' must be 'get_context_from_vector_store' when type is 'action'")
            
            # parameters must be present
            if self.parameters is None:
                raise ValueError("'parameters' must be present when type is 'action'")
        
        return self