"""
Twitch bot for the VTuber AI Bot.
"""

import os
import logging
import asyncio
from twitchio.ext import commands

logger = logging.getLogger(__name__)

class TwitchBot(commands.Bot):
    """Twitch bot for handling chat commands."""
    
    def __init__(self, config, ai_client=None, tts_manager=None, message_queue=None, queue_processor_callback=None):
        """Initialize the Twitch bot.
        
        Args:
            config: Configuration object containing Twitch settings
            ai_client: AI client for generating responses
            tts_manager: TTS manager for speaking responses
            message_queue: Queue for handling AI responses sequentially
            queue_processor_callback: Callback function to start the message queue processor
        """
        # Store references to other components
        self.config = config
        self.ai_client = ai_client
        self.tts_manager = tts_manager
        self.message_queue = message_queue
        self.queue_processor_callback = queue_processor_callback
        
        # Get authentication details from configuration
        client_id = config.twitch_client_id
        token = config.twitch_token
        
        # Verify we have the required credentials
        if not token:
            logger.warning("TWITCH_TOKEN not found in environment variables. Twitch integration may not work.")
        
        if not client_id:
            logger.warning("TWITCH_CLIENT_ID not found in environment variables. Twitch integration may not work.")
        
        # Initialize the bot with the token for authentication
        super().__init__(
            token=token,
            client_id=client_id,
            nick=config.twitch_nick,
            prefix=config.twitch_prefix,
            initial_channels=[config.twitch_channel]
        )
        
        # Log the configuration
        logger.info(f"Initialized Twitch bot with nick '{config.twitch_nick}' for channel '{config.twitch_channel}'")
        if token:
            logger.info("Using token authentication for Twitch")
        else:
            logger.warning("No token provided for Twitch authentication")
    
    async def initialize(self):
        """Initialize Twitch bot connection."""
        try:
            await self.connect()
            logger.info("Connected to Twitch chat")
        except Exception as e:
            logger.error(f"Failed to connect to Twitch: {e}")
    
    # Get the command name from the config (without the ! prefix)
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # This will be called when the bot is initialized
        cls._command_name = None
    
    async def event_ready(self):
        # Extract the command name without the ! prefix
        command_name = self.config.ai_command_prefix
        if command_name.startswith('!'):
            command_name = command_name[1:]
        
        # Store the command name for reference
        self.__class__._command_name = command_name
        
        # Register the command dynamically
        self.add_command(commands.Command(
            name=command_name,
            func=self.ai_command,
            aliases=[]
        ))
        
        logger.info(f"AI command registered as: !{command_name}")
    
    async def ai_command(self, ctx):
        """Handle AI commands from Twitch chat."""
        try:
            # Extract the message content after the command
            message = ctx.message.content.split(' ', 1)
            if len(message) > 1:
                prompt = message[1]
                logger.info(f"Received Twitch command: {prompt}")
                
                # Check if we're using the message queue system
                if self.message_queue and self.config.enable_message_queue:
                    # Create message item for the queue
                    message_item = {
                        'text': prompt,
                        'source': 'twitch',
                        'context': ctx
                    }
                    
                    try:
                        # Try to add to queue, don't block if queue is full
                        import asyncio
                        await asyncio.wait_for(self.message_queue.put(message_item), 0.1)
                        
                        # Start processing if not already playing audio
                        if self.queue_processor_callback:
                            # Use the callback provided by VTuberBot
                            asyncio.create_task(self.queue_processor_callback())
                        
                        # No longer sending acknowledgment message
                            
                    except asyncio.TimeoutError:
                        # Queue is full, send rejection message
                        logger.warning("Message queue is full, rejecting Twitch command")
                        await ctx.send(self.config.queue_full_message)
                        
                    except Exception as e:
                        logger.error(f"Error adding to message queue: {e}")
                        await ctx.send("Sorry, I encountered an error processing your request.")
                        
                # Process immediately if not using queue
                elif self.ai_client:
                    response = await self.ai_client.generate_response(prompt)
                    
                    # Only send chat response if enabled in config
                    if self.config.ai_chat_response:
                        await ctx.send(response)
                    
                    # Speak the response if TTS is available
                    if self.tts_manager:
                        await self.tts_manager.speak_response(response)
                else:
                    # Always send error messages regardless of setting
                    await ctx.send("AI client not fully initialized yet.")
            else:
                command_name = self.config.ai_command_prefix
                await ctx.send(f"Please provide a message after {command_name}")
        except Exception as e:
            logger.error(f"Error processing Twitch command: {e}")
            await ctx.send("Sorry, I encountered an error processing your request.")
