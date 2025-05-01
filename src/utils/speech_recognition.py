"""
Speech recognition module using OpenAI Whisper API.
"""

import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

class SpeechRecognition:
    """Speech recognition using OpenAI Whisper API."""
    
    def __init__(self, config):
        """Initialize the speech recognition module.
        
        Args:
            config: Configuration object containing API settings
        """
        self.config = config
        self.client = OpenAI(api_key=config.openai_api_key)
    
    async def transcribe_audio(self, audio_file_path):
        """Transcribe audio using OpenAI Whisper API.
        
        Args:
            audio_file_path: Path to the audio file to transcribe
            
        Returns:
            str: Transcribed text or None if transcription failed
        """
        try:
            with open(audio_file_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            
            # Clean up temporary file
            try:
                os.unlink(audio_file_path)
            except Exception as e:
                logger.warning(f"Error removing temporary audio file: {e}")
            
            if transcription.text:
                logger.info(f"Transcription: {transcription.text}")
                return transcription.text
            else:
                logger.warning("No transcription returned from Whisper API")
                return None
                
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            
            # Clean up temporary file in case of error
            try:
                os.unlink(audio_file_path)
            except:
                pass
                
            return None
