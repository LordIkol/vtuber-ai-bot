"""
AI client for generating responses using OpenAI GPT and Assistant API.
"""

import logging
import asyncio
from typing import Any, Optional
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

class AIClient:
    """Client for generating AI responses using OpenAI GPT and Assistant API."""
    
    DEFAULT_SYSTEM_INSTRUCTIONS = """You are Fenris, a friendly and engaging VTuber AI assistant. 
    Your responses should be concise, entertaining, and suitable for streaming platforms. 
    Keep your responses under 2-3 sentences when possible. 
    You can be playful and show personality, but always remain helpful and appropriate for all audiences. 
    If asked about topics you don't have information on, be honest about your limitations.
    Avoid overly technical language unless specifically asked for technical details."""
    
    DEFAULT_MAX_ATTEMPTS = 60  # Maximum number of polling attempts for assistant API
    
    def __init__(self, config: Any) -> None:
        """Initialize the AI client.
        
        Args:
            config: Configuration object containing AI settings
        """
        self.config: Any = config
        self.client: AsyncOpenAI = AsyncOpenAI(api_key=config.openai_api_key)
        
        # Store assistant ID if provided
        self.assistant_id: Optional[str] = getattr(config, 'openai_assistant_id', None)
        self.use_assistant: bool = getattr(config, 'use_assistant_api', False)
        
        # Thread management for assistant API
        self.thread_id: Optional[str] = None
        self.thread_created: bool = False
        
        # Get system instructions and other config values with defaults
        self.system_instructions: str = getattr(config, 'ai_system_instructions', self.DEFAULT_SYSTEM_INSTRUCTIONS)
        self.max_attempts: int = getattr(config, 'assistant_api_max_attempts', self.DEFAULT_MAX_ATTEMPTS)
    
    async def generate_response(self, prompt: str) -> str:
        """Generate a response using OpenAI GPT with fallback.
        
        Args:
            prompt: User prompt to generate a response for
            
        Returns:
            str: Generated response
        """
        try:
            # Use Assistant API if configured
            if self.use_assistant and self.assistant_id:
                return await self.generate_assistant_response(prompt)
            else:
                # Use standard chat completions API
                return await self._generate_chat_completion(prompt)
        except Exception as e:
            logger.error("Error generating GPT response", exc_info=True)
            
            # Check if it's a quota exceeded error
            if "quota" in str(e).lower() or "insufficient_quota" in str(e).lower():
                logger.warning("OpenAI API quota exceeded, using fallback response generation")
                return self.generate_fallback_response(prompt)
            
            return "Sorry, I encountered an error. Please try again."
    
    async def generate_assistant_response(self, prompt: str) -> str:
        """Generate a response using OpenAI Assistant API.
        
        Args:
            prompt: User prompt to generate a response for
            
        Returns:
            str: Generated response from the assistant
        """
        try:
            # Create a thread if we don't have one yet
            if not self.thread_created:
                thread = self.client.beta.threads.create()
                self.thread_id = thread.id
                self.thread_created = True
                logger.info(f"Created new assistant thread with ID: {self.thread_id}")
            
            # Add the user message to the thread
            await self.client.beta.threads.messages.create(
                thread_id=self.thread_id,
                role="user",
                content=prompt
            )
            
            # Run the assistant on the thread
            run = await self.client.beta.threads.runs.create(
                thread_id=self.thread_id,
                assistant_id=self.assistant_id
            )
            
            # Poll for the run to complete
            attempts = 0
            while attempts < self.max_attempts:
                run_status = await self.client.beta.threads.runs.retrieve(
                    thread_id=self.thread_id,
                    run_id=run.id
                )
                
                if run_status.status == "completed":
                    # Get the assistant's response
                    messages = await self.client.beta.threads.messages.list(
                        thread_id=self.thread_id
                    )
                    
                    # Find the most recent assistant message
                    for message in messages.data:
                        if message.role == "assistant":
                            # Extract the text content from the message
                            if hasattr(message, 'content') and message.content:
                                for content_item in message.content:
                                    if content_item.type == "text":
                                        return content_item.text.value
                            break
                    
                    # If we couldn't find a response, return a default message
                    return "I processed your request, but couldn't generate a proper response."
                
                elif run_status.status == "failed":
                    logger.error(f"Assistant run failed: {run_status.last_error}", exc_info=True)
                    return "Sorry, I encountered an error processing your request."
                
                # Wait before polling again
                await asyncio.sleep(1)
                attempts += 1
            
            # If we've reached the maximum number of attempts, return a timeout message
            logger.error("Assistant API timeout: Run did not complete in the expected time", exc_info=True)
            return "Sorry, it's taking me longer than expected to process your request. Please try again."
            
        except Exception as e:
            logger.error("Error using Assistant API", exc_info=True)
            
            # Fall back to standard chat completions if assistant fails
            logger.info("Falling back to standard chat completions")
            return await self._generate_chat_completion(prompt)
    
    async def _generate_chat_completion(self, prompt: str) -> str:
        """Generate a response using OpenAI's chat completions API.
        
        Args:
            prompt: User prompt to generate a response for
            
        Returns:
            str: Generated response from the model
        """
        response = await self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": self.system_instructions},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    
    async def generate_fallback_response(self, prompt: str) -> str:
        """Generate a fallback response when OpenAI API is unavailable.
        
        Args:
            prompt: User prompt to generate a response for
            
        Returns:
            str: Fallback response
        """
        # Simple rule-based responses
        prompt_lower = prompt.lower()
        
        if any(word in prompt_lower for word in ("hello", "hi", "hey")):
            return "Hello! I'm your VTuber AI assistant. How can I help you today?"
        
        if "how are you" in prompt_lower:
            return "I'm doing well, thank you for asking! How about you?"
        
        if any(phrase in prompt_lower for phrase in ("what can you do", "help")):
            return "I can chat with you, respond to Twitch commands, and control your VTube Studio avatar. Just speak naturally or type commands in Twitch chat!"
        
        if "thank" in prompt_lower:
            return "You're welcome! I'm happy to help."
        
        if "joke" in prompt_lower:
            return "Why don't scientists trust atoms? Because they make up everything!"
        
        if "weather" in prompt_lower:
            return "I don't have access to real-time weather data, but I hope it's nice where you are!"
        
        # Default response
        return "I'm currently operating in fallback mode due to API limitations. I can only respond to basic queries right now."