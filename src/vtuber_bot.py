"""
Main VTuber AI Bot class that coordinates all components.
"""

import os
import sys
import time
import asyncio
import tempfile
import threading
from queue import Queue
from datetime import datetime

# Import our custom logger
from src.utils.logger import get_logger, UI_INFO

from .audio.audio_manager import AudioManager
from .config.config import Config
from .tts.tts_manager import TTSManager
from .twitch.twitch_bot import TwitchBot
from .vtube_studio.vtube_studio_client import VTubeStudioClient
from .utils.ai_client import AIClient
from .utils.speech_recognition import SpeechRecognition

# Configure logging with our custom logger
logger = get_logger(__name__)


class VTuberBot:
    """Main VTuber AI Bot class that coordinates all components."""

    def __init__(self):
        """Initialize the VTuber AI Bot."""
        self.config = Config()
        self.audio_manager = AudioManager(self.config)
        self.vtube_studio = VTubeStudioClient(self.config)
        self.tts_manager = TTSManager(self.config, vtube_studio_client=self.vtube_studio)
        self.ai_client = AIClient(self.config)
        self.speech_recognition = SpeechRecognition(self.config)
        self.message_queue = asyncio.Queue(maxsize=self.config.max_queue_size)

        self.is_playing_audio = False
        self.next_audio_file = None
        self.next_audio_text = None

        async def start_processing_if_needed():
            if not self.is_playing_audio:
                asyncio.create_task(self.process_next_message())

        self.twitch_bot = TwitchBot(
            self.config,
            ai_client=self.ai_client,
            tts_manager=self.tts_manager,
            message_queue=self.message_queue,
            queue_processor_callback=start_processing_if_needed
        )

        self.running = False

    async def initialize(self):
        """Initialize all components and connections."""
        await self.vtube_studio.initialize()
        await self.twitch_bot.initialize()

    async def process_speech(self, text):
        """Process transcribed speech and generate response."""
        try:
            logger.info(f"Speech input: {text}")
            logger.ui_info(f"Speech input: {text}")  # This will show in the UI

            if self.config.enable_message_queue:
                message_item = {'text': text, 'source': 'voice', 'context': None}
                try:
                    await asyncio.wait_for(self.message_queue.put(message_item), 0.1)
                    logger.info(f"Added voice message to queue: {text}")
                    logger.ui_info(f"Added to queue: {text}")  # This will show in the UI
                    if not self.is_playing_audio:
                        asyncio.create_task(self.process_next_message())
                except asyncio.TimeoutError:
                    logger.warning("Message queue is full, voice input ignored")
                    # Warning level already shows in UI
                    print("Message queue is full. Please wait for current messages to be processed.")
            else:
                response = await self.ai_client.generate_response(text)
                await self.tts_manager.speak_response(response)
                await self.vtube_studio.trigger_animation()

        except Exception as e:
            logger.error(f"Error processing speech: {e}")

    async def prefetch_next_message(self):
        """Prefetch the next message's audio while current one is playing."""
        try:
            if self.message_queue.empty():
                return

            next_message = next(iter(self.message_queue._queue), None)  # access _queue (internal deque)
            if not next_message:
                return

            text = next_message['text']
            logger.info(f"Prefetching audio for next message: {text}")
            response = await self.ai_client.generate_response(text)
            audio_file = await self.tts_manager.prepare_audio(response)

            if audio_file:
                self.next_audio_file = audio_file
                self.next_audio_text = text
                logger.info("Successfully prefetched audio for next message")

        except Exception as e:
            logger.error(f"Error prefetching next message: {e}")
            self.next_audio_file = None
            self.next_audio_text = None

    async def process_next_message(self):
        """Process the next message in the queue and then check for more."""
        try:
            self.is_playing_audio = True
            message_item = await self.message_queue.get()

            try:
                text = message_item['text']
                source = message_item['source']
                context = message_item['context']

                logger.info(f"Processing message from {source}: {text}")
                logger.ui_info(f"Processing: {text}")  # This will show in the UI

                if self.next_audio_file and self.next_audio_text == text:
                    logger.info("Using prefetched audio file")
                    response = self.next_audio_text
                    audio_file = self.next_audio_file
                    self.next_audio_file = None
                    self.next_audio_text = None
                    if not self.message_queue.empty():
                        asyncio.create_task(self.prefetch_next_message())
                else:
                    response = await self.ai_client.generate_response(text)
                    audio_file = await self.tts_manager.prepare_audio(response)

                if source == 'twitch' and context and self.config.ai_chat_response:
                    await context.send(response)

                if not self.message_queue.empty() and not self.next_audio_file:
                    asyncio.create_task(self.prefetch_next_message())

                if audio_file:
                    self.tts_manager._is_playing = True
                    self.tts_manager._playback_done = False

                    thread = threading.Thread(target=self.tts_manager._play_audio_thread, args=(audio_file,))
                    thread.daemon = True
                    thread.start()

                    start_time = time.time()
                    timeout = 60
                    while self.tts_manager._is_playing and not self.tts_manager._playback_done:
                        if time.time() - start_time > timeout:
                            logger.warning("Playback timeout reached, forcing completion")
                            self.tts_manager._is_playing = False
                            self.tts_manager._playback_done = True
                            break
                        await asyncio.sleep(0.1)

                    await asyncio.to_thread(thread.join, 2.0)

                await self.vtube_studio.trigger_animation()

            except Exception as e:
                logger.error(f"Error processing message: {e}")
                if context:
                    try:
                        await context.send(f"Sorry, I encountered an error: {str(e)[:100]}")
                    except:
                        pass

            self.message_queue.task_done()

            if not self.message_queue.empty():
                logger.info("Processing next message in queue")
                await asyncio.sleep(0.5)
                asyncio.create_task(self.process_next_message())
            else:
                logger.info("No more messages in queue")
                logger.ui_info("Queue empty - ready for new input")  # This will show in the UI

        except Exception as e:
            logger.error(f"Error in message processor: {e}")
        finally:
            if self.message_queue.empty():
                self.is_playing_audio = False

    async def run(self):
        """Run the main event loop."""
        logger.info("Setting up microphone for voice input")
        if not self.audio_manager.start_audio_stream():
            logger.error("Failed to start audio stream")
            print("\nFailed to start audio stream. Please check your microphone settings and try again.")
            return

        if self.audio_manager.hotkey_mode:
            logger.info(f"Using recording hotkey: {self.audio_manager.recording_hotkey}")
            self.audio_manager.setup_hotkey_listener()

        logger.info("===== VTuber AI Bot is running! =====")
        logger.info("- Speak into your microphone to interact with the bot")
        logger.info("- Use '!AI <message>' in Twitch chat to get responses")
        logger.info(f"- Message queue enabled (max size: {self.config.max_queue_size})")
        logger.info("VTuber AI Bot is ready for interaction")

        self.running = True

        try:
            while self.running:
                if self.audio_manager.pending_audio_file and os.path.exists(self.audio_manager.pending_audio_file):
                    temp_filename = self.audio_manager.pending_audio_file
                    self.audio_manager.pending_audio_file = None
                    transcription = await self.speech_recognition.transcribe_audio(temp_filename)
                    if transcription:
                        await self.process_speech(transcription)

                # No command processing - removed CLI interface

                await asyncio.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("Shutting down...")
            print("\nShutting down VTuber AI Bot...")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            print(f"\nAn error occurred: {e}\nThe bot will now exit.")
        finally:
            self.running = False
            self.audio_manager.cleanup()
            await self.vtube_studio.close()
            print("Goodbye!")

    # CLI interface removed - now using GUI for all commands

    async def update_input_device(self, device_id):
        """Update input device."""
        try:
            self.config.microphone_device_id = device_id
            if self.audio_manager.stream:
                self.audio_manager.stream.stop_stream()
                self.audio_manager.stream.close()
            success = self.audio_manager.start_audio_stream(device_id)
            if success:
                logger.info(f"Input device changed to {device_id}")
                return True
            else:
                logger.error(f"Failed to change input device to {device_id}")
                return False
        except Exception as e:
            logger.error(f"Error updating input device: {e}")
            return False

    async def update_output_device(self, device_id):
        """Update output device."""
        try:
            self.config.output_device_id = device_id
            if hasattr(self.tts_manager, 'output_device_id'):
                self.tts_manager.output_device_id = device_id
                logger.info(f"Output device changed to {device_id}")
                return True
        except Exception as e:
            logger.error(f"Error updating output device: {e}")
            return False

    async def stop(self):
        """Stop the VTuber AI Bot."""
        logger.info("Stopping VTuber AI Bot...")
        self.running = False
        self.audio_manager.cleanup()
        await self.twitch_bot.disconnect()
        await self.vtube_studio.disconnect()
        logger.info("VTuber AI Bot stopped")
