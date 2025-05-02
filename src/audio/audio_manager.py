"""
Audio manager for handling audio recording and processing.
"""

import os
import wave
import tempfile
import logging
import numpy as np
import pyaudio
import threading
import keyboard

logger = logging.getLogger(__name__)

class AudioManager:
    """Manages audio recording and processing for the VTuber AI Bot."""
    
    def __init__(self, config):
        """Initialize the audio manager.
        
        Args:
            config: Configuration object containing audio settings
        """
        self.config = config
        
        # Initialize PyAudio
        self.p = pyaudio.PyAudio()
        self.stream = None
        
        # Audio recording parameters
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = config.sample_rate
        self.CHUNK = config.chunk_size
        self.SILENCE_THRESHOLD = config.silence_threshold
        self.SILENCE_DURATION = config.silence_duration
        
        # Recording state
        self.recording = False
        self.audio_data = []
        self.manual_recording = False
        self.hotkey_mode = config.hotkey_mode
        self.recording_hotkey = config.recording_hotkey
        self.hotkey_thread = None
        
        # Flag for pending audio files to process
        self.pending_audio_file = None
    
    def list_audio_devices(self):
        """List available audio input devices.
        
        Returns:
            List of tuples containing device ID and name
        """
        info = self.p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        
        print("\nAvailable audio input devices:")
        input_devices = []
        
        for i in range(0, numdevices):
            device_info = self.p.get_device_info_by_host_api_device_index(0, i)
            if device_info.get('maxInputChannels') > 0:
                print(f"Input Device id {i} - {device_info.get('name')}")
                input_devices.append((i, device_info.get('name')))
        
        return input_devices
    
    def start_audio_stream(self, device_id=None):
        """Start audio stream for speech recognition.
        
        Args:
            device_id: Optional device ID to use for recording
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Use device ID from config if not explicitly provided
        if device_id is None:
            device_id = self.config.microphone_device_id
            
        # List available devices for informational purposes
        input_devices = self.list_audio_devices()
        
        # Show which device we're using
        if device_id is not None:
            # Find the device name if possible
            device_name = "Unknown"
            for dev_id, dev_name in input_devices:
                if dev_id == device_id:
                    device_name = dev_name
                    break
            logger.info(f"Using microphone device ID {device_id}: {device_name}")
        else:
            logger.info("Using default microphone device")
        
        # Open the audio stream with the selected device
        try:
            self.stream = self.p.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                input_device_index=device_id,
                frames_per_buffer=self.CHUNK,
                stream_callback=self.audio_callback
            )
            self.stream.start_stream()
            logger.info(f"Started audio stream for speech recognition with device ID: {device_id if device_id is not None else 'default'}")
        except Exception as e:
            logger.error(f"Error starting audio stream: {e}")
            print(f"\nError starting audio stream: {e}")
            print("Please check your microphone settings and try again.")
            return False
        
        return True
    
    def audio_callback(self, in_data, frame_count, time_info, status):
        """Callback function for audio stream.
        
        Args:
            in_data: Audio data
            frame_count: Number of frames
            time_info: Time information
            status: Status flag
            
        Returns:
            tuple: (in_data, paContinue)
        """
        if status:
            logger.warning(f"Audio stream status: {status}")
        
        # Convert audio data to numpy array
        audio_data = np.frombuffer(in_data, dtype=np.int16)
        audio_level = np.abs(audio_data).mean()
        
        # Hotkey mode - only record when manually triggered
        if self.hotkey_mode:
            if self.manual_recording:
                # We're manually recording, so collect the audio data
                self.audio_data.append(in_data)
            return (in_data, pyaudio.paContinue)
        
        # Voice activation mode - detect speech automatically
        if audio_level > self.SILENCE_THRESHOLD and not self.recording:
            # Start recording
            logger.info(f"Speech detected, audio level: {audio_level}")
            self.recording = True
            self.audio_data = [in_data]
        elif audio_level > self.SILENCE_THRESHOLD and self.recording:
            # Continue recording
            self.audio_data.append(in_data)
        elif audio_level <= self.SILENCE_THRESHOLD and self.recording:
            # Potential end of speech, check if silence is long enough
            self.audio_data.append(in_data)
            
            # If we have enough chunks to represent SILENCE_DURATION seconds of audio
            silence_chunks = int(self.SILENCE_DURATION * self.RATE / self.CHUNK)
            
            # Check the last few chunks for silence
            if len(self.audio_data) > silence_chunks:
                recent_chunks = self.audio_data[-silence_chunks:]
                recent_audio = np.frombuffer(b''.join(recent_chunks), dtype=np.int16)
                recent_level = np.abs(recent_audio).mean()
                
                if recent_level <= self.SILENCE_THRESHOLD:
                    # End of speech detected
                    logger.info(f"End of speech detected, processing audio")
                    self.recording = False
                    self.save_and_process_audio()
        
        return (in_data, pyaudio.paContinue)
    
    def save_and_process_audio(self):
        """Save recorded audio to a temporary file for processing."""
        if not self.audio_data:
            logger.warning("No audio data to process")
            return
            
        # Save the audio data for processing in the main thread
        audio_data_copy = self.audio_data.copy()
        self.audio_data = []
        
        # Save to a temporary file for processing
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_filename = temp_file.name
                
                with wave.open(temp_filename, 'wb') as wf:
                    wf.setnchannels(self.CHANNELS)
                    wf.setsampwidth(self.p.get_sample_size(self.FORMAT))
                    wf.setframerate(self.RATE)
                    wf.writeframes(b''.join(audio_data_copy))
            
            # Set a flag to process this file in the main event loop
            self.pending_audio_file = temp_filename
            logger.info(f"Saved audio to temporary file for processing: {temp_filename}")
        except Exception as e:
            logger.error(f"Error saving audio for processing: {e}")
    
    def setup_hotkey_listener(self):
        """Set up the hotkey listener for manual recording."""
        if not self.hotkey_mode:
            return
            
        def on_press():
            if not self.manual_recording:
                # Start recording
                self.manual_recording = True
                self.audio_data = []
                print(f"\n[Recording started] Press {self.recording_hotkey} again to stop...")
            else:
                # Stop recording and process
                self.manual_recording = False
                print(f"\n[Recording stopped] Processing audio...")
                self.save_and_process_audio()
        
        # Register the hotkey
        keyboard.add_hotkey(self.recording_hotkey, on_press)
        print(f"\nHotkey mode enabled. Press {self.recording_hotkey} to start/stop recording.")
        
        # Start a thread to keep the keyboard listener running
        self.hotkey_thread = threading.Thread(target=lambda: None, daemon=True)
        self.hotkey_thread.start()
    
    def cleanup(self):
        """Clean up resources."""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        
        if self.p:
            self.p.terminate()
