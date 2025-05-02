"""
Text-to-Speech manager for the VTuber AI Bot.
"""

import os
import asyncio
import tempfile
import logging
import threading
import requests
import time
import wave
import pyaudio
import math
import numpy as np
from typing import Any, Optional, Union
from pydub import AudioSegment
from pydub.playback import play as pydub_play

# Import Coqui TTS conditionally to avoid errors if not installed
try:
    from TTS.api import TTS as CoquiTTS
    COQUI_AVAILABLE = True
except ImportError:
    COQUI_AVAILABLE = False
    logging.warning("Coqui TTS not available. Install with 'pip install TTS'")

logger = logging.getLogger(__name__)

class TTSManager:
    """Manages text-to-speech conversion and playback."""
    
    def __init__(self, config: Any, vtube_studio_client: Optional[Any] = None) -> None:
        """Initialize the TTS manager.
        
        Args:
            config: Configuration object containing TTS settings
            vtube_studio_client: VTube Studio client for animations
        """
        self.config = config
        self.tts_engine = config.tts_engine
        self.volume = float(config.tts_volume)
        self.vtube_studio_client = vtube_studio_client
        
        # ElevenLabs specific settings
        self.voice_id = config.elevenlabs_voice_id
        self.api_key = config.elevenlabs_api_key
        
        # Coqui TTS specific settings
        self.coqui_model = config.coqui_model
        self.coqui_vocoder = config.coqui_vocoder
        self.coqui_tts = None
        
        # Initialize Coqui TTS if selected and available
        if self.tts_engine == 'coqui':
            success = self._init_coqui_tts()
            if not success:
                # Fall back to ElevenLabs if Coqui initialization fails
                self.tts_engine = 'elevenlabs'
                logger.info("Falling back to ElevenLabs TTS")
        
        # State variables for audio playback
        self._is_playing = False
        self._playback_done = False
    
    async def speak_response(self, text: str) -> None:
        """Convert text to speech and play it.
        
        This method handles both the audio generation and playback using the configured TTS engine.
        It will trigger VTubeStudio animations if configured and handle playback in a separate thread.
        
        Args:
            text: Text to convert to speech
        """
        if not text or text.strip() == "":
            logger.warning("Empty text provided to TTS, skipping")
            return
        
        try:
            # Set flags to indicate playback is starting
            self._is_playing = True
            self._playback_done = False
            
            # Generate the audio file using prepare_audio
            filename = await self.prepare_audio(text)
            
            if not filename:
                logger.error("Failed to generate TTS audio file")
                self._is_playing = False
                self._playback_done = True
                return
            
            # Trigger VTubeStudio animation if available
            if self.vtube_studio_client:
                await self.vtube_studio_client.trigger_animation()
            
            # Create and start playback thread
            thread = threading.Thread(
                target=self._play_audio_thread,
                args=(filename,),
                daemon=True
            )
            thread.start()
            
            # Wait for playback to complete or timeout
            start_time = time.time()
            timeout = 30  # Maximum wait time in seconds
            
            while self._is_playing and not self._playback_done:
                if time.time() - start_time > timeout:
                    logger.warning("Playback timeout reached, forcing completion")
                    self._is_playing = False
                    self._playback_done = True
                    break
                await asyncio.sleep(0.1)
            
            # Wait for thread to complete with timeout
            wait_start = time.time()
            while thread.is_alive() and time.time() - wait_start < 2.0:
                await asyncio.sleep(0.1)
            
        except Exception as e:
            logger.error(f"Error in speak_response: {e}")
            self._is_playing = False
            self._playback_done = True
    
    async def prepare_audio(self, text: str) -> Optional[str]:
        """Convert text to speech and return the filename without playing it.
        
        Args:
            text: Text to convert to speech
            
        Returns:
            str: Filename of the generated audio file, or None if generation failed
        """
        if not text or text.strip() == "":
            logger.warning("Empty text provided to TTS, skipping")
            return None
        
        # Use appropriate TTS engine
        if self.tts_engine == 'elevenlabs':
            return await self._prepare_audio_elevenlabs(text)
        elif self.tts_engine == 'coqui':
            return await self._prepare_audio_coqui(text)
        else:
            logger.error(f"Unknown TTS engine: {self.tts_engine}")
            return None
    
    async def _prepare_audio_elevenlabs(self, text: str) -> Optional[str]:
        """Convert text to speech using ElevenLabs API.
        
        Args:
            text: Text to convert to speech
            
        Returns:
            str: Filename of the generated audio file, or None if generation failed
        """
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key
            }
            
            data = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.5
                }
            }
            
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                # Save the audio to a temporary file
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                    temp_filename = temp_file.name
                    temp_file.write(response.content)
                
                logger.info(f"Saved ElevenLabs audio response to temporary file: {temp_filename}")
                return temp_filename
            else:
                logger.error(f"Error from ElevenLabs API: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error in prepare_audio_elevenlabs: {e}")
            return None
    
    async def _prepare_audio_coqui(self, text: str) -> Optional[str]:
        """Convert text to speech using Coqui TTS.
        
        Args:
            text: Text to convert to speech
            
        Returns:
            str: Filename of the generated audio file, or None if generation failed
        """
        if not COQUI_AVAILABLE:
            logger.error("Coqui TTS not available but was requested")
            return await self._prepare_audio_elevenlabs(text)  # Fall back to ElevenLabs
        
        try:
            # Create a temporary file for the output
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_filename = temp_file.name
            
            # Run Coqui TTS in a separate thread to avoid blocking
            def generate_tts():
                try:
                    if self.coqui_tts is None:
                        # Initialize if not already done
                        self._init_coqui_tts()
                    
                    # Generate and save the audio
                    self.coqui_tts.tts_to_file(text=text, file_path=temp_filename)
                    logger.info(f"Generated Coqui TTS audio to {temp_filename}")
                except Exception as e:
                    logger.error(f"Error generating Coqui TTS: {e}")
            
            # Create and start the thread
            tts_thread = threading.Thread(target=generate_tts)
            tts_thread.start()
            
            # Wait for the thread to complete with a timeout
            tts_thread.join(timeout=30.0)  # 30 seconds timeout
            
            # Check if the file was created successfully
            if os.path.exists(temp_filename) and os.path.getsize(temp_filename) > 0:
                logger.info(f"Saved Coqui TTS audio response to temporary file: {temp_filename}")
                return temp_filename
            else:
                logger.error("Coqui TTS failed to generate audio or timed out")
                # Fall back to ElevenLabs if Coqui fails
                return await self._prepare_audio_elevenlabs(text)
        except Exception as e:
            logger.error(f"Error in prepare_audio_coqui: {e}")
            # Fall back to ElevenLabs
            return await self._prepare_audio_elevenlabs(text)
    

    
    def _play_mp3(self, filename: str) -> bool:
        """Play an MP3 file using pydub.
        
        Args:
            filename: Path to the MP3 file
            
        Returns:
            bool: True if playback was successful, False if it failed
        """
        try:
            # Load the MP3 file
            sound = AudioSegment.from_mp3(filename)
            
            # Apply volume adjustment
            if self.volume != 1.0 and self.volume > 0:
                # Convert linear volume (0.0-2.0) to dB
                db_change = 20 * math.log10(self.volume)
                sound = sound.apply_gain(db_change)
            
            # Play the audio directly using pydub's built-in playback
            pydub_play(sound)
            logger.info("Audio playback complete")
            return True
            
        except Exception as e:
            logger.error(f"Error in MP3 playback: {e}", exc_info=True)
            return False
    
    def _play_wav(self, filename: str) -> bool:
        """Play a WAV file using PyAudio.
        
        Args:
            filename: Path to the WAV file
            
        Returns:
            bool: True if playback was successful, False if it failed
        """
        try:
            # Open the WAV file
            with wave.open(filename, 'rb') as wf:
                # Create PyAudio instance for playback
                p = pyaudio.PyAudio()
                
                # Open stream
                stream = p.open(
                    format=p.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True
                )
                
                # Read data in chunks and play
                chunk_size = 1024
                data = wf.readframes(chunk_size)
                
                while len(data) > 0:
                    # Convert bytes to numpy array for volume adjustment
                    audio_data = np.frombuffer(data, dtype=np.int16)
                    # Apply volume
                    audio_data = (audio_data * self.volume).astype(np.int16)
                    # Convert back to bytes
                    stream.write(audio_data.tobytes())
                    data = wf.readframes(chunk_size)
                
                # Clean up
                stream.stop_stream()
                stream.close()
                p.terminate()
            
            logger.info("Audio playback complete")
            return True
            
        except Exception as e:
            logger.error(f"Error in WAV playback: {e}", exc_info=True)
            return False
    
    def _init_coqui_tts(self) -> bool:
        """Initialize Coqui TTS if not already initialized.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        if not COQUI_AVAILABLE:
            logger.warning("Coqui TTS not available. Install with 'pip install TTS'")
            return False
            
        try:
            # Check the version of TTS to determine the correct initialization method
            import importlib.metadata
            tts_version = importlib.metadata.version('TTS')
            logger.info(f"Detected Coqui TTS version: {tts_version}")
            
            # Initialize TTS based on version
            if tts_version >= '0.22.0':  # Newer versions use a different API
                self.coqui_tts = CoquiTTS(model_name=self.coqui_model)
            else:  # Older versions used vocoder_name
                self.coqui_tts = CoquiTTS(model_name=self.coqui_model, vocoder_name=self.coqui_vocoder)
                
            logger.info(f"Initialized Coqui TTS with model {self.coqui_model}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Coqui TTS: {e}", exc_info=True)
            return False
    
    def _fallback_play(self, filename: str) -> None:
        """Fall back to system audio player.
        
        Args:
            filename: Path to the audio file
        """
        try:
            os.system(f"start {filename}")
        except Exception as e:
            logger.error(f"Error in fallback playback: {e}", exc_info=True)
    
    def _play_audio_thread(self, filename: str) -> None:
        """Play audio file in a separate thread.
        
        Args:
            filename: Path to the audio file to play
        """
        try:
            logger.info("Playing audio response...")
            success = False
            
            # Try appropriate playback method based on file type
            if filename.endswith('.mp3'):
                success = self._play_mp3(filename)
            elif filename.endswith('.wav'):
                success = self._play_wav(filename)
            
            # Fall back to system player if direct playback failed or unsupported format
            if not success:
                self._fallback_play(filename)
                
        except Exception as e:
            logger.error(f"Error in audio playback thread: {e}", exc_info=True)
            self._fallback_play(filename)
            
        finally:
            # Always signal that playback is done
            self._playback_done = True
            self._is_playing = False
    
    async def play_audio_file(self, filename: str) -> None:
        """Play an audio file directly using pydub for MP3 and PyAudio for WAV.
        This is now a legacy method that delegates to the new thread-based approach.
        
        Args:
            filename: Path to the audio file to play
        """
        # Trigger animation in VTube Studio if available
        if self.vtube_studio_client:
            await self.vtube_studio_client.trigger_animation()
        
        # Set playing flag
        self._is_playing = True
        
        # Play the audio in a separate thread
        play_thread = threading.Thread(
            target=self._play_audio_thread, 
            args=(filename,),
            daemon=True
        )
        play_thread.start()
        
        # Wait for audio to finish playing
        while self._is_playing and not self._playback_done:
            await asyncio.sleep(0.1)  # Small delay to not overload the CPU
        
        # Wait for thread to finish with timeout
        wait_start = time.time()
        while play_thread.is_alive() and time.time() - wait_start < 1.0:
            await asyncio.sleep(0.1)
