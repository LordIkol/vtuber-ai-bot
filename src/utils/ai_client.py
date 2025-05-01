"""
AI client for generating responses using OpenAI GPT.
"""

import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

class AIClient:
    """Client for generating AI responses using OpenAI GPT."""
    
    def __init__(self, config):
        """Initialize the AI client.
        
        Args:
            config: Configuration object containing AI settings
        """
        self.config = config
        self.client = OpenAI(api_key=config.openai_api_key)
    
    async def generate_response(self, prompt):
        """Generate a response using OpenAI GPT with fallback.
        
        Args:
            prompt: User prompt to generate a response for
            
        Returns:
            str: Generated response
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating GPT response: {e}")
            
            # Check if it's a quota exceeded error
            if "quota" in str(e).lower() or "insufficient_quota" in str(e).lower():
                logger.warning("OpenAI API quota exceeded, using fallback response generation")
                return self.generate_fallback_response(prompt)
            
            return "Sorry, I encountered an error. Please try again."
    
    def generate_fallback_response(self, prompt):
        """Generate a fallback response when OpenAI API is unavailable.
        
        Args:
            prompt: User prompt to generate a response for
            
        Returns:
            str: Fallback response
        """
        # Simple rule-based responses
        prompt_lower = prompt.lower()
        
        if "hello" in prompt_lower or "hi" in prompt_lower or "hey" in prompt_lower:
            return "Hello! I'm your VTuber AI assistant. How can I help you today?"
        
        if "how are you" in prompt_lower:
            return "I'm doing well, thank you for asking! How about you?"
        
        if "what can you do" in prompt_lower or "help" in prompt_lower:
            return "I can chat with you, respond to Twitch commands, and control your VTube Studio avatar. Just speak naturally or type commands in Twitch chat!"
        
        if "thank" in prompt_lower:
            return "You're welcome! I'm happy to help."
        
        if "joke" in prompt_lower:
            return "Why don't scientists trust atoms? Because they make up everything!"
        
        if "weather" in prompt_lower:
            return "I don't have access to real-time weather data, but I hope it's nice where you are!"
        
        # Default response
        return "I'm currently operating in fallback mode due to API limitations. I can only respond to basic queries right now."
