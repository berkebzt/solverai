import logging
from typing import List, Dict, AsyncGenerator, Optional
import httpx
from config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """Service for interacting with LLMs (Ollama local or OpenAI cloud)"""

    def __init__(self):
        self.ollama_base_url = settings.ollama_base_url
        # Workaround for localhost resolution issues with httpx/Ollama
        if "localhost" in self.ollama_base_url:
            self.ollama_base_url = self.ollama_base_url.replace("localhost", "127.0.0.1")
        self.ollama_model = "llama3.1:8b" # Force model name
        self.openai_api_key = settings.openai_api_key
        self.use_ollama = True  # Default to local
        import os
        self.mock_mode = os.getenv("LLM_MOCK_MODE", "false").lower() == "true"

    async def check_ollama_availability(self) -> bool:
        """Check if Ollama is available"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.ollama_base_url}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            return False

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        context: Optional[str] = None,
    ):
        """
        Generate a response from the LLM

        Args:
            messages: List of message dicts with 'role' and 'content'
            stream: Whether to stream the response

        Returns:
            Complete response string or async generator for streaming
        """

        # Inject context if provided
        if context:
            system_msg_idx = -1
            for i, msg in enumerate(messages):
                if msg["role"] == "system":
                    system_msg_idx = i
                    break
            
            context_prompt = f"\n\nContext information is below.\n---------------------\n{context}\n---------------------\nGiven the context information and not prior knowledge, answer the query."
            
            if system_msg_idx >= 0:
                messages[system_msg_idx]["content"] += context_prompt
            else:
                messages.insert(0, {"role": "system", "content": "You are a helpful AI assistant." + context_prompt})

        # Check for mock mode
        if self.mock_mode:
            logger.info("Using Mock LLM")
            mock_response = "This is a mock response from SolverAI."
            if stream:
                async def mock_stream():
                    for word in mock_response.split():
                        yield word + " "
                        import asyncio
                        await asyncio.sleep(0.1)
                return mock_stream()
            return mock_response

        # Check Ollama availability
        ollama_available = await self.check_ollama_availability()

        if ollama_available:
            logger.info(f"Using Ollama with model: {self.ollama_model}")
            return await self._generate_ollama(messages, stream)
        elif self.openai_api_key:
            logger.info("Ollama unavailable, falling back to OpenAI")
            return await self._generate_openai(messages, stream)
        else:
            raise Exception(
                "No LLM available. Ollama is down and no OpenAI API key configured."
            )

    async def _generate_ollama(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
    ) -> str | AsyncGenerator[str, None]:
        """Generate response using Ollama"""

        if stream:
            return self._stream_ollama(messages)
        else:
            return await self._complete_ollama(messages)

    def _format_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Format messages into Llama 3 prompt format"""
        prompt = "<|begin_of_text|>"
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                prompt += f"<|start_header_id|>system<|end_header_id|>\n\n{content}<|eot_id|>"
            elif role == "user":
                prompt += f"<|start_header_id|>user<|end_header_id|>\n\n{content}<|eot_id|>"
            elif role == "assistant":
                prompt += f"<|start_header_id|>assistant<|end_header_id|>\n\n{content}<|eot_id|>"
        prompt += "<|start_header_id|>assistant<|end_header_id|>\n\n"
        return prompt

    async def _complete_ollama(self, messages: List[Dict[str, str]]) -> str:
        """Get complete response from Ollama using /api/generate"""
        prompt = self._format_prompt(messages)
        async with httpx.AsyncClient(timeout=120.0) as client:
            payload = {
                "model": self.ollama_model,
                "prompt": prompt,
                "stream": False,
            }

            response = await client.post(
                f"{self.ollama_base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()

            data = response.json()
            return data["response"]

    async def _stream_ollama(
        self, messages: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        """Stream response from Ollama using /api/generate"""
        prompt = self._format_prompt(messages)
        async with httpx.AsyncClient(timeout=120.0) as client:
            payload = {
                "model": self.ollama_model,
                "prompt": prompt,
                "stream": True,
            }

            async with client.stream(
                "POST",
                f"{self.ollama_base_url}/api/generate",
                json=payload,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.strip():
                        import json
                        try:
                            chunk = json.loads(line)
                            if "response" in chunk:
                                content = chunk["response"]
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue

    async def _generate_openai(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
    ) -> str | AsyncGenerator[str, None]:
        """Generate response using OpenAI API"""

        if stream:
            return self._stream_openai(messages)
        else:
            return await self._complete_openai(messages)

    async def _complete_openai(self, messages: List[Dict[str, str]]) -> str:
        """Get complete response from OpenAI"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": "gpt-4-turbo-preview",
                "messages": messages,
                "stream": False,
            }

            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()

            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def _stream_openai(
        self, messages: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        """Stream response from OpenAI"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": "gpt-4-turbo-preview",
                "messages": messages,
                "stream": True,
            }

            async with client.stream(
                "POST",
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            break

                        import json
                        try:
                            chunk = json.loads(data)
                            if chunk["choices"][0]["delta"].get("content"):
                                yield chunk["choices"][0]["delta"]["content"]
                        except json.JSONDecodeError:
                            continue

    def format_conversation_history(
        self,
        messages: List[Dict[str, str]],
        max_history: int = 10,
    ) -> List[Dict[str, str]]:
        """
        Format conversation history for LLM context

        Args:
            messages: Full conversation history
            max_history: Maximum number of recent messages to include

        Returns:
            Formatted message list for LLM
        """
        # Keep system message if present
        system_messages = [m for m in messages if m["role"] == "system"]

        # Get recent user/assistant messages
        chat_messages = [m for m in messages if m["role"] in ["user", "assistant"]]
        recent_messages = chat_messages[-max_history:] if len(chat_messages) > max_history else chat_messages

        return system_messages + recent_messages


# Create singleton instance
llm_service = LLMService()
