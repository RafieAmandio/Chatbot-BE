import openai
from typing import List, Dict, Any, AsyncGenerator
from tenacity import retry, stop_after_attempt, wait_exponential
import logging
from app.config import settings

logger = logging.getLogger(__name__)

# Configure OpenAI client
openai.api_key = settings.openai_api_key


class OpenAIService:
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
    
    @retry(
        stop=stop_after_attempt(settings.openai_max_retries),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def create_embedding(self, text: str) -> List[float]:
        """Create embedding for a single text"""
        try:
            response = await self.client.embeddings.create(
                model=settings.openai_embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error creating embedding: {e}")
            raise
    
    @retry(
        stop=stop_after_attempt(settings.openai_max_retries),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def create_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for multiple texts"""
        try:
            response = await self.client.embeddings.create(
                model=settings.openai_embedding_model,
                input=texts
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(f"Error creating batch embeddings: {e}")
            raise
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Create chat completion"""
        try:
            params = {
                "model": settings.openai_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": stream
            }
            
            if tools:
                params["tools"] = tools
                params["tool_choice"] = "auto"
            
            response = await self.client.chat.completions.create(**params)
            
            if stream:
                return response
            else:
                return {
                    "content": response.choices[0].message.content,
                    "tool_calls": response.choices[0].message.tool_calls,
                    "usage": response.usage
                }
        except Exception as e:
            logger.error(f"Error in chat completion: {e}")
            raise
    
    async def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Create streaming chat completion"""
        try:
            params = {
                "model": settings.openai_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True
            }
            
            if tools:
                params["tools"] = tools
                params["tool_choice"] = "auto"
            
            stream = await self.client.chat.completions.create(**params)
            
            async for chunk in stream:
                if chunk.choices:
                    choice = chunk.choices[0]
                    delta = choice.delta
                    
                    chunk_data = {
                        "content": delta.content if delta.content else "",
                        "tool_calls": delta.tool_calls if hasattr(delta, 'tool_calls') and delta.tool_calls else None,
                        "finish_reason": choice.finish_reason
                    }
                    
                    yield chunk_data
                    
        except Exception as e:
            logger.error(f"Error in streaming chat completion: {e}")
            raise
    
    def get_token_count(self, text: str) -> int:
        """Estimate token count for text"""
        # Simple approximation: 1 token ≈ 4 characters
        return len(text) // 4
    
    def truncate_messages(self, messages: List[Dict[str, str]], max_tokens: int = 16000) -> List[Dict[str, str]]:
        """Truncate messages to fit within token limit"""
        total_tokens = 0
        truncated_messages = []
        
        # Always keep system message if present
        if messages and messages[0].get("role") == "system":
            truncated_messages.append(messages[0])
            total_tokens += self.get_token_count(messages[0]["content"])
            messages = messages[1:]
        
        # Add messages from the end (most recent first)
        for message in reversed(messages):
            message_tokens = self.get_token_count(message["content"])
            if total_tokens + message_tokens > max_tokens:
                break
            truncated_messages.insert(-len(truncated_messages) if truncated_messages else 0, message)
            total_tokens += message_tokens
        
        return truncated_messages


# Global OpenAI service instance
openai_service = OpenAIService() 