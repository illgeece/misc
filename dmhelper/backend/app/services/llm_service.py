"""Large Language Model service using Ollama."""

import logging
from typing import List, Dict, Any, Optional
import ollama
from pydantic import BaseModel

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    """Chat message model."""
    role: str  # "user", "assistant", "system"
    content: str


class LLMResponse(BaseModel):
    """LLM response model."""
    content: str
    model: str
    context_length: int
    response_time_ms: Optional[int] = None


class LLMService:
    """Service for interacting with Ollama LLM."""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = ollama.Client(host=self.settings.ollama_base_url)
        self._ensure_model_available()
    
    def _ensure_model_available(self) -> None:
        """Ensure the configured model is available locally."""
        try:
            # Check if model exists locally
            models = self.client.list()
            # Handle different response formats
            if hasattr(models, 'models'):
                model_list = models.models
            else:
                model_list = models.get('models', [])
            
            model_names = []
            for model in model_list:
                if hasattr(model, 'name'):
                    model_names.append(model.name)
                elif isinstance(model, dict) and 'name' in model:
                    model_names.append(model['name'])
                else:
                    # Try to extract model name from string representation
                    model_str = str(model)
                    if ':' in model_str:
                        model_names.append(model_str)
            
            if self.settings.ollama_model not in model_names:
                logger.info(f"Model {self.settings.ollama_model} not found locally. Pulling...")
                self.client.pull(self.settings.ollama_model)
                logger.info(f"Successfully pulled {self.settings.ollama_model}")
            else:
                logger.info(f"Model {self.settings.ollama_model} is available")
                
        except Exception as e:
            logger.error(f"Error ensuring model availability: {e}")
            raise RuntimeError(f"Failed to setup Ollama model: {e}")
    
    async def generate_response(
        self, 
        messages: List[ChatMessage],
        system_prompt: Optional[str] = None,
        context: Optional[str] = None
    ) -> LLMResponse:
        """Generate a response using the LLM."""
        try:
            # Prepare messages for Ollama
            ollama_messages = []
            
            # Add system prompt if provided
            if system_prompt:
                ollama_messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            # Add context if provided
            if context:
                ollama_messages.append({
                    "role": "system", 
                    "content": f"Context information:\n{context}"
                })
            
            # Add conversation messages
            for msg in messages:
                ollama_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            # Generate response
            response = self.client.chat(
                model=self.settings.ollama_model,
                messages=ollama_messages,
                options={
                    'temperature': self.settings.temperature,
                    'num_predict': self.settings.max_tokens,
                }
            )
            
            return LLMResponse(
                content=response['message']['content'],
                model=self.settings.ollama_model,
                context_length=len(str(ollama_messages)),
                response_time_ms=response.get('total_duration', 0) // 1_000_000  # Convert to ms
            )
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            raise RuntimeError(f"LLM generation failed: {e}")
    
    async def generate_dm_response(
        self,
        user_message: str,
        conversation_history: List[ChatMessage],
        retrieved_context: Optional[str] = None
    ) -> LLMResponse:
        """Generate a DM-specific response with proper context."""
        
        system_prompt = """You are an experienced Dungeon Master's AI assistant for D&D 5e. You help DMs by:

1. Answering rules questions with precise, accurate information
2. Providing creative suggestions for story, NPCs, and encounters  
3. Helping with character creation and validation
4. Offering tactical advice for combat and encounters
5. Citing sources when referencing specific rules

Always be helpful, creative, and maintain the spirit of collaborative storytelling. When unsure about rules, clearly state your uncertainty and suggest consulting official sources."""

        # Combine user message with any retrieved context
        full_messages = conversation_history + [ChatMessage(role="user", content=user_message)]
        
        return await self.generate_response(
            messages=full_messages,
            system_prompt=system_prompt,
            context=retrieved_context
        )
    
    def health_check(self) -> Dict[str, Any]:
        """Check if the LLM service is healthy."""
        try:
            # Simple test generation
            response = self.client.chat(
                model=self.settings.ollama_model,
                messages=[{"role": "user", "content": "Hello"}],
                options={'num_predict': 10}
            )
            
            return {
                "status": "healthy",
                "model": self.settings.ollama_model,
                "base_url": self.settings.ollama_base_url,
                "test_response": response['message']['content'][:50] + "..."
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "model": self.settings.ollama_model,
                "base_url": self.settings.ollama_base_url
            }


# Global instance
llm_service = LLMService() 