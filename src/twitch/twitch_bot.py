"""
Twitch bot for the VTuber AI Bot.
"""

import os
import logging
import asyncio
from typing import Optional, Any, Callable, Coroutine, Union
from twitchio.ext import commands

logger = logging.getLogger(__name__)

class TwitchBot(commands.Bot):
    """Twitch bot for handling chat commands."""
    
    # Class variable to track command registration
    _command_registered: bool = False
    
    def __init__(self, 
                 config: Any,
                 ai_client: Optional[Any] = None,
                 tts_manager: Optional[Any] = None,
                 message_queue: Optional[asyncio.Queue] = None,
                 queue_processor_callback: Optional[Callable[[], Coroutine[Any, Any, None]]] = None):
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
            
        # Initialize command name
        self._command_name = None
    
    async def initialize(self) -> None:
        """Initialize Twitch bot connection."""
        try:
            await self.connect()
            logger.info("Connected to Twitch chat")
        except Exception as e:
            logger.error(f"Failed to connect to Twitch: {e}")
            raise  # Re-raise to let caller handle connection failures
    
    async def event_ready(self) -> None:
        """Event handler called when the bot is ready to process commands."""
        # Only register command once
        if not TwitchBot._command_registered:
            # Extract the command name without the ! prefix
            command_name = self.config.ai_command_prefix
            if command_name.startswith('!'):
                command_name = command_name[1:]
            
            # Store the command name for reference
            self._command_name = command_name
            
            # Register the command dynamically with cooldown
            cmd = commands.Command(
                name=command_name,
                func=self.ai_command,
                aliases=[],
                cooldown=commands.Cooldown(rate=1, per=5, bucket=commands.Bucket.user)  # 1 command per 5 seconds per user
            )
            self.add_command(cmd)
            
            # Mark command as registered
            TwitchBot._command_registered = True
            logger.info(f"AI command registered as: !{command_name}")
    
    async def _safe_send(self, ctx: commands.Context, message: str) -> None:
        """Safely send a message to the Twitch chat.
        
        Args:
            ctx: The command context
            message: The message to send
        """
        try:
            await ctx.send(message)
        except Exception as e:
            logger.error(f"Failed to send message to Twitch chat: {e}")

    async def _process_queued_message(self, ctx: commands.Context, prompt: str) -> None:
        """Process a message through the queue system.
        
        Args:
            ctx: The command context
            prompt: The user's prompt to process
        """
        message_item = {
            'text': prompt,
            'source': 'twitch',
            'context': ctx
        }
        
        try:
            # Try to add to queue, don't block if queue is full
            await asyncio.wait_for(self.message_queue.put(message_item), 0.1)
            
            # Start processing if callback is available
            if self.queue_processor_callback:
                asyncio.create_task(self.queue_processor_callback())
                
        except asyncio.TimeoutError:
            logger.warning("Message queue is full, rejecting Twitch command")
            await self._safe_send(ctx, self.config.queue_full_message)
            
        except Exception as e:
            logger.error(f"Error adding to message queue: {e}")
            await self._safe_send(ctx, "Sorry, I encountered an error processing your request.")

    async def _process_immediate_message(self, ctx: commands.Context, prompt: str) -> None:
        """Process a message immediately without queueing.
        
        Args:
            ctx: The command context
            prompt: The user's prompt to process
        """
        try:
            response = await self.ai_client.generate_response(prompt)
            
            # Send chat response if enabled
            if self.config.ai_chat_response:
                await self._safe_send(ctx, response)
            
            # Speak response if TTS is available
            if self.tts_manager:
                await self.tts_manager.speak_response(response)
                
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            await self._safe_send(ctx, "Sorry, I encountered an error generating a response.")

    @commands.cooldown(rate=1, per=5, bucket=commands.Bucket.user)
    async def ai_command(self, ctx: commands.Context) -> None:
        """Handle AI commands from Twitch chat."""
        try:
            # Extract the message content after the command
            message = ctx.message.content.split(' ', 1)
            if len(message) > 1:
                prompt = message[1]
                logger.info(f"Received Twitch command: {prompt}")
                
                # Process through queue if enabled
                if self.message_queue and self.config.enable_message_queue:
                    await self._process_queued_message(ctx, prompt)
                # Process immediately if queue is disabled
                elif self.ai_client:
                    await self._process_immediate_message(ctx, prompt)
                else:
                    await self._safe_send(ctx, "AI client not fully initialized yet.")
            else:
                await self._safe_send(ctx, f"Please provide a message after {self.config.ai_command_prefix}")
                
        except commands.CommandOnCooldown as e:
            await self._safe_send(ctx, f"Please wait {e.retry_after:.1f} seconds before using this command again.")
        except Exception as e:
            logger.error(f"Error processing Twitch command: {e}")
            await self._safe_send(ctx, "Sorry, I encountered an error processing your request.")

    async def shutdown(self) -> None:
        """Gracefully shut down the Twitch bot."""
        try:
            # Close the Twitch connection
            await self.close()
            logger.info("Twitch bot connection closed")
            
            # Clear any pending messages from the queue
            if self.message_queue:
                while not self.message_queue.empty():
                    try:
                        self.message_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break
                logger.info("Message queue cleared")
                
        except Exception as e:
            logger.error(f"Error during Twitch bot shutdown: {e}")
