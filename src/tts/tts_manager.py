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
from pydub import AudioSegment
from pydub.playback import play as pydub_play

logger = logging.getLogger(__name__)

class TTSManager:
    """Manages text-to-speech conversion and playback."""
    
    def __init__(self, config, vtube_studio_client=None):
        """Initialize the TTS manager.
        
        Args:
            config: Configuration object containing TTS settings
            vtube_studio_client: VTube Studio client for animations
        """
        self.config = config
        self.voice_id = config.elevenlabs_voice_id
        self.api_key = config.elevenlabs_api_key
        self.volume = config.tts_volume
        self.vtube_studio_client = vtube_studio_client
        
        # State variables for audio playback
        self._is_playing = False
        self._playback_done = False
    
    async def speak_response(self, text):
        """Convert text to speech using ElevenLabs API and play directly.
        
        Args:
            text: Text to convert to speech
        """
        try:
            # Reset playback state
            self._is_playing = False
            self._playback_done = False
            
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
            
            logger.info(f"Sending TTS request for: {text}")
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                # Save audio to temporary file
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                    temp_filename = temp_file.name
                    temp_file.write(response.content)
                
                logger.info(f"Saved audio response to temporary file: {temp_filename}")
                
                return temp_filename
            else:
                logger.error(f"Error from ElevenLabs API: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error generating TTS audio file: {e}")
            return None
    
    async def prepare_audio(self, text):
        """Convert text to speech and return the filename without playing it.
        
        Args:
            text: Text to convert to speech
            
        Returns:
            str: Filename of the generated audio file, or None if generation failed
        """
        if not text or text.strip() == "":
            logger.warning("Empty text provided to TTS, skipping")
            return None
        
        try:
            # Use the same ElevenLabs API call as in speak_response
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
                
                logger.info(f"Saved audio response to temporary file: {temp_filename}")
                return temp_filename
            else:
                logger.error(f"Error from ElevenLabs API: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error in prepare_audio: {e}")
            return None
    
    async def speak_response(self, text):
        """Convert text to speech and play it.
        
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
            
            # Trigger animation in VTube Studio if available
            if self.vtube_studio_client:
                await self.vtube_studio_client.trigger_animation()
            
            # Play the audio file in a separate thread
            thread = threading.Thread(target=self._play_audio_thread, args=(filename,))
            thread.daemon = True
            thread.start()
            
            # Wait for playback to complete or timeout
            start_time = time.time()
            timeout = 60  # 60 second timeout
            
            while self._is_playing and not self._playback_done:
                if time.time() - start_time > timeout:
                    logger.warning("Playback timeout reached, forcing completion")
                    self._is_playing = False
                    self._playback_done = True
                    break
                await asyncio.sleep(0.1)
            
            # Wait for thread to complete
            if thread.is_alive():
                thread.join(2.0)  # Wait up to 2 seconds for thread to finish
            
        except Exception as e:
            logger.error(f"Error in speak_response: {e}")
            self._is_playing = False
            self._playback_done = True
    
    def _play_audio_thread(self, filename):
        """Play audio file in a separate thread.
        
        Args:
            filename: Path to the audio file to play
        """
        try:
            print("Playing audio response...")
            
            # Use pydub for MP3 files
            if filename.endswith('.mp3'):
                try:
                    # Load the MP3 file
                    sound = AudioSegment.from_mp3(filename)
                    
                    # Apply volume adjustment
                    if self.volume != 1.0:
                        # Adjust volume - pydub uses dB for volume adjustment
                        # 0 dB is original volume, negative values reduce volume, positive increase it
                        # Convert our linear volume (0.0-2.0) to dB
                        if self.volume > 0:
                            db_change = 20 * math.log10(self.volume)
                            sound = sound.apply_gain(db_change)
                    
                    # Play the audio directly using pydub's built-in playback
                    pydub_play(sound)
                    
                    # Signal that playback is complete
                    self._playback_done = True
                    self._is_playing = False
                    
                    print("Audio playback complete")
                except Exception as e:
                    logger.error(f"Error in audio playback: {e}")
                    # Fall back to system player only if playback fails
                    os.system(f"start {filename}")
                    # Signal completion after starting external player
                    self._playback_done = True
                    self._is_playing = False
            
            # For WAV files, use PyAudio for direct playback
            elif filename.endswith('.wav'):
                try:
                    # Open the WAV file
                    wf = wave.open(filename, 'rb')
                    
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
                        # Play the audio chunk
                        stream.write(data)
                        data = wf.readframes(chunk_size)
                    
                    # Clean up
                    stream.stop_stream()
                    stream.close()
                    p.terminate()
                    wf.close()
                    
                    # Signal that playback is complete
                    self._playback_done = True
                    self._is_playing = False
                    
                    print("Audio playback complete")
                except Exception as e:
                    logger.error(f"Error playing audio file: {e}")
                    # Fall back to system player if direct playback fails
                    os.system(f"start {filename}")
                    # Signal completion after starting external player
                    self._playback_done = True
                    self._is_playing = False
            else:
                # For other file types, use system player
                os.system(f"start {filename}")
                # Signal completion after starting external player
                self._playback_done = True
                self._is_playing = False
                
        except Exception as e:
            logger.error(f"Error in audio playback thread: {e}")
        finally:
            # Signal that playback is done
            self._playback_done = True
            self._is_playing = False
    
    async def play_audio_file(self, filename):
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
        
        # Wait for thread to finish
        play_thread.join(timeout=1.0)
