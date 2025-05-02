"""
Main VTuber AI Bot class that coordinates all components.
"""

import os
import sys
import time
import asyncio
import logging
import keyboard
import threading
from datetime import datetime
from asyncio import Queue

from .audio.audio_manager import AudioManager
from .config.config import Config
from .tts.tts_manager import TTSManager
from .twitch.twitch_bot import TwitchBot
from .vtube_studio.vtube_studio_client import VTubeStudioClient
from .utils.ai_client import AIClient
from .utils.speech_recognition import SpeechRecognition

logger = logging.getLogger(__name__)

class VTuberBot:
    """Main VTuber AI Bot class that coordinates all components."""
    
    def __init__(self):
        """Initialize the VTuber AI Bot."""
        # Load configuration
        self.config = Config()
        
        # Initialize components
        self.audio_manager = AudioManager(self.config)
        self.vtube_studio = VTubeStudioClient(self.config)
        self.tts_manager = TTSManager(self.config, vtube_studio_client=self.vtube_studio)
        self.ai_client = AIClient(self.config)
        self.speech_recognition = SpeechRecognition(self.config)
        
        # Message queue for handling AI responses
        self.message_queue = asyncio.Queue(maxsize=self.config.max_queue_size)
        self.is_playing_audio = False  # Flag to track if we're currently playing audio
        self.next_audio_file = None  # Store the next prepared audio file
        self.next_audio_text = None  # Store the text for the next audio
        
        # Create a simple callback that checks if we're already playing audio
        async def start_processing_if_needed():
            if not self.is_playing_audio:
                asyncio.create_task(self.process_next_message())
        
        # Initialize Twitch bot with references to other components
        self.twitch_bot = TwitchBot(
            self.config,
            ai_client=self.ai_client,
            tts_manager=self.tts_manager,
            message_queue=self.message_queue,
            queue_processor_callback=start_processing_if_needed
        )
    
    async def initialize(self):
        """Initialize all components and connections."""
        # Initialize VTube Studio connection
        await self.vtube_studio.initialize()
        
        # Initialize Twitch bot
        await self.twitch_bot.initialize()
    
    async def process_speech(self, text):
        """Process transcribed speech and generate response.
        
        Args:
            text: Transcribed speech text
        """
        try:
            logger.info(f"Speech input: {text}")
            
            if self.config.enable_message_queue:
                # Create a message item with source='voice'
                message_item = {
                    'text': text,
                    'source': 'voice',
                    'context': None  # No Twitch context for voice messages
                }
                
                # Add to queue
                try:
                    # Try to add to queue, don't wait if queue is full
                    await asyncio.wait_for(self.message_queue.put(message_item), 0.1)
                    logger.info(f"Added voice message to queue: {text}")
                    
                    # Start processing the queue if not already playing audio
                    if not self.is_playing_audio:
                        asyncio.create_task(self.process_next_message())
                except asyncio.TimeoutError:
                    logger.warning("Message queue is full, voice input ignored")
                    print("Message queue is full. Please wait for current messages to be processed.")
            else:
                # Process immediately if queue is disabled
                response = await self.ai_client.generate_response(text)
                await self.tts_manager.speak_response(response)
                await self.vtube_studio.trigger_animation()
                
        except Exception as e:
            logger.error(f"Error processing speech: {e}")
            
    async def prefetch_next_message(self):
        """Prefetch the next message's audio while the current one is playing."""
        try:
            # Peek at the next message in the queue without removing it
            # We can't actually peek at asyncio.Queue, so we need to get creative
            # Get a copy of the queue's internal deque
            if self.message_queue.empty():
                return
                
            # Get the next message without removing it from the queue
            # This is a bit hacky but works for our purpose
            next_message = None
            for i, item in enumerate(self.message_queue._queue):
                if i == 0:  # First item in the queue
                    next_message = item
                    break
            
            if not next_message:
                return
                
            text = next_message['text']
            logger.info(f"Prefetching audio for next message: {text}")
            
            # Generate AI response for the next message
            response = await self.ai_client.generate_response(text)
            
            # Prepare the audio file without playing it
            audio_file = await self.tts_manager.prepare_audio(response)
            
            if audio_file:
                # Store the prepared audio file and text
                self.next_audio_file = audio_file
                self.next_audio_text = text
                logger.info("Successfully prefetched audio for next message")
            
        except Exception as e:
            logger.error(f"Error prefetching next message: {e}")
            # Clear any partial prefetch data
            self.next_audio_file = None
            self.next_audio_text = None
    
    async def process_next_message(self):
        """Process the next message in the queue and then check for more."""
        try:
            # Set the flag to indicate we're processing audio
            self.is_playing_audio = True
            
            # Get the next message from the queue
            message_item = await self.message_queue.get()
            
            try:
                text = message_item['text']
                source = message_item['source']
                context = message_item['context']
                
                logger.info(f"Processing message from {source}: {text}")
                
                # Check if we have a prefetched audio file ready
                if self.next_audio_file and self.next_audio_text:
                    # If the prefetched text matches our current text, use the prefetched audio
                    if self.next_audio_text == text:
                        logger.info("Using prefetched audio file")
                        response = self.next_audio_text
                        audio_file = self.next_audio_file
                        self.next_audio_file = None
                        self.next_audio_text = None
                        
                        # Start prefetching the next message if available
                        if not self.message_queue.empty():
                            asyncio.create_task(self.prefetch_next_message())
                    else:
                        # If the text doesn't match, generate a new response
                        logger.info("Prefetched text doesn't match, generating new response")
                        response = await self.ai_client.generate_response(text)
                        audio_file = await self.tts_manager.prepare_audio(response)
                else:
                    # Generate AI response and prepare audio
                    response = await self.ai_client.generate_response(text)
                    audio_file = await self.tts_manager.prepare_audio(response)
                
                # Handle response based on source
                if source == 'twitch' and context is not None:
                    # Send chat response if enabled
                    if self.config.ai_chat_response:
                        await context.send(response)
                
                # Start prefetching the next message while this one is playing
                if not self.message_queue.empty() and not self.next_audio_file:
                    asyncio.create_task(self.prefetch_next_message())
                
                # Play the audio (this will block until audio playback is complete)
                if audio_file:
                    # Set flags to indicate playback is starting
                    self.tts_manager._is_playing = True
                    self.tts_manager._playback_done = False
                    
                    # Play the audio file in a separate thread
                    thread = threading.Thread(target=self.tts_manager._play_audio_thread, args=(audio_file,))
                    thread.daemon = True
                    thread.start()
                    
                    # Wait for playback to complete or timeout
                    start_time = time.time()
                    timeout = 60  # 60 second timeout
                    
                    while self.tts_manager._is_playing and not self.tts_manager._playback_done:
                        if time.time() - start_time > timeout:
                            logger.warning("Playback timeout reached, forcing completion")
                            self.tts_manager._is_playing = False
                            self.tts_manager._playback_done = True
                            break
                        await asyncio.sleep(0.1)
                    
                    # Wait for thread to complete
                    if thread.is_alive():
                        thread.join(2.0)  # Wait up to 2 seconds for thread to finish
                
                # Trigger avatar animation
                await self.vtube_studio.trigger_animation()
                
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                if message_item.get('context'):
                    try:
                        await message_item['context'].send(f"Sorry, I encountered an error: {str(e)[:100]}")
                    except:
                        pass
            
            # Mark the task as done
            self.message_queue.task_done()
            
            # Check if there are more messages in the queue
            if not self.message_queue.empty():
                # Process the next message
                logger.info("Processing next message in queue")
                # Small delay before processing the next message
                await asyncio.sleep(0.5)
                asyncio.create_task(self.process_next_message())
            else:
                logger.info("No more messages in queue")
            
        except Exception as e:
            logger.error(f"Error in message processor: {e}")
        finally:
            # Clear the flag if there are no more messages to process
            if self.message_queue.empty():
                self.is_playing_audio = False
    
    async def run(self):
        """Run the main event loop."""
        # Start audio stream with configured microphone device
        logger.info("Setting up microphone for voice input")
        if not self.audio_manager.start_audio_stream():
            logger.error("Failed to start audio stream")
            print("\nFailed to start audio stream. Please check your microphone settings and try again.")
            return
        
        # Set up hotkey listener if in hotkey mode
        if self.audio_manager.hotkey_mode:
            logger.info(f"Using recording hotkey: {self.audio_manager.recording_hotkey}")
            self.audio_manager.setup_hotkey_listener()
        
        logger.info("===== VTuber AI Bot is running! =====")
        logger.info("- Speak into your microphone to interact with the bot")
        logger.info("- Use '!AI <message>' in Twitch chat to get responses")
        logger.info(f"- Message queue enabled (max size: {self.config.max_queue_size})")
        logger.info("VTuber AI Bot is ready for interaction")
        
        # Set up command processing
        self.running = True
        self._command_list = []
        
        # Start command input thread
        input_thread = threading.Thread(target=self.command_input_thread, daemon=True)
        input_thread.start()
        
        # Keep the event loop running
        try:
            while self.running:
                # Check for pending audio files to process
                if self.audio_manager.pending_audio_file and os.path.exists(self.audio_manager.pending_audio_file):
                    temp_filename = self.audio_manager.pending_audio_file
                    self.audio_manager.pending_audio_file = None  # Reset the flag
                    
                    # Transcribe audio
                    transcription = await self.speech_recognition.transcribe_audio(temp_filename)
                    
                    if transcription:
                        await self.process_speech(transcription)
                
                # Check for commands
                if self._command_list:
                    # Get the first command from the list
                    command = self._command_list.pop(0)
                    await self.process_command(command)
                
                # Short sleep to prevent CPU hogging
                await asyncio.sleep(0.1)
                
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            print("\nShutting down VTuber AI Bot...")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            print(f"\nAn error occurred: {e}")
            print("The bot will now exit.")
        finally:
            # Clean up resources
            self.running = False
            self.audio_manager.cleanup()
            await self.vtube_studio.close()
            print("Goodbye!")
    
    def command_input_thread(self):
        """Thread for reading command input from the console."""
        while self.running:
            try:
                # Read input from the console
                cmd = input()
                if cmd.strip():
                    # Use a simple list for commands instead of asyncio Queue
                    # This avoids the need for asyncio in the input thread
                    self._command_list.append(cmd.strip())
            except EOFError:
                # End of input stream
                break
            except Exception as e:
                logger.error(f"Error in command input thread: {e}")
    
    async def process_command(self, command):
        """Process a command from the console.
        
        Args:
            command: The command to process
        """
        cmd_parts = command.split()
        cmd = cmd_parts[0].lower()
        
        if cmd == "help":
            print("\nAvailable commands:")
            print("  volume <level>  - Set TTS volume (0.1-2.0, e.g., 'volume 0.8')")
            print("  chatresponse    - Toggle chat responses for AI commands on/off")
            print("  messagequeue    - Toggle message queue on/off")
            print("  queuesize <n>   - Set maximum message queue size (1-50)")
            print("  status         - Show current bot status")
            print("  exit           - Exit the bot")
            print("  help           - Show this help message")
        
        elif cmd == "volume":
            if len(cmd_parts) > 1:
                try:
                    volume = float(cmd_parts[1])
                    if volume < 0:
                        print("Volume cannot be negative. Using 0.0 (muted).")
                        volume = 0.0
                    elif volume > 2.0:
                        print("Volume cannot be greater than 2.0. Using 2.0.")
                        volume = 2.0
                    
                    # Update the volume setting
                    self.tts_manager.volume = volume
                    print(f"TTS volume set to {volume}")
                except ValueError:
                    print(f"Invalid volume value: {cmd_parts[1]}. Please use a number between 0.0 and 2.0.")
            else:
                print(f"Current TTS volume: {self.tts_manager.volume}")
                print("Usage: volume <level> (0.0-2.0)")
        
        elif cmd == "chatresponse":
            # Toggle chat response setting
            self.config.ai_chat_response = not self.config.ai_chat_response
            status = "enabled" if self.config.ai_chat_response else "disabled"
            print(f"Chat responses for AI commands {status}")
            
        elif cmd == "messagequeue":
            # Toggle message queue setting
            self.config.enable_message_queue = not self.config.enable_message_queue
            status = "enabled" if self.config.enable_message_queue else "disabled"
            print(f"Message queue {status}")
            
        elif cmd == "queuesize":
            if len(cmd_parts) > 1:
                try:
                    size = int(cmd_parts[1])
                    if size < 1:
                        print("Queue size cannot be less than 1. Using 1.")
                        size = 1
                    elif size > 50:
                        print("Queue size cannot be greater than 50. Using 50.")
                        size = 50
                    
                    # Update the queue size setting
                    old_size = self.config.max_queue_size
                    self.config.max_queue_size = size
                    
                    # Create a new queue with the updated size
                    new_queue = asyncio.Queue(maxsize=size)
                    
                    # Transfer items from old queue if possible
                    if not self.message_queue.empty():
                        print("Warning: Changing queue size will clear the current queue.")
                    
                    # Replace the queue
                    self.message_queue = new_queue
                    print(f"Message queue size changed from {old_size} to {size}")
                except ValueError:
                    print(f"Invalid queue size value: {cmd_parts[1]}. Please use a number between 1 and 50.")
            else:
                print(f"Current message queue size: {self.config.max_queue_size}")
                print("Usage: queuesize <n> (1-50)")
        
        elif cmd == "status":
            print("\nVTuber AI Bot Status:")
            print(f"  TTS Volume: {self.tts_manager.volume}")
            print(f"  Chat Responses: {'Enabled' if self.config.ai_chat_response else 'Disabled'}")
            print(f"  Message Queue: {'Enabled' if self.config.enable_message_queue else 'Disabled'}")
            print(f"  Queue Size: {self.config.max_queue_size} (Current: {self.message_queue.qsize()}/{self.config.max_queue_size})")
            print(f"  Hotkey Mode: {'Enabled' if self.audio_manager.hotkey_mode else 'Disabled'}")
            print(f"  Recording Hotkey: {self.audio_manager.recording_hotkey}")
            print(f"  VTube Studio: {'Connected' if self.vtube_studio.ws else 'Disconnected'}")
            print(f"  Twitch: {'Connected' if self.twitch_bot._connection else 'Disconnected'}")

        
        elif cmd == "exit":
            print("Exiting VTuber AI Bot...")
            self.running = False
        
        else:
            print(f"Unknown command: {cmd}. Type 'help' for available commands.")

