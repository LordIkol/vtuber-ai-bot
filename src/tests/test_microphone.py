"""
Test module for microphone functionality.
"""

import pyaudio
import wave
import tempfile
import os
import numpy as np
import time
from pydub import AudioSegment
from pydub.playback import play
from ..config import Config

def record_audio(duration=5, sample_rate=44100, chunk_size=1024):
    """Record audio from microphone for a specified duration"""
    p = pyaudio.PyAudio()
    
    # List available audio input devices
    print("\nAvailable audio input devices:")
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    
    for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            print(f"Input Device id {i} - {p.get_device_info_by_host_api_device_index(0, i).get('name')}")
    
    # Ask for device selection
    device_id = input("\nSelect input device ID (press Enter for default): ")
    if device_id.strip():
        device_id = int(device_id)
    else:
        device_id = None
    
    try:
        # Open stream with selected device
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=sample_rate,
            input=True,
            input_device_index=device_id,
            frames_per_buffer=chunk_size
        )
        
        print(f"\nRecording for {duration} seconds...")
        print("Speak into your microphone now!")
        
        # Record audio
        frames = []
        for i in range(0, int(sample_rate / chunk_size * duration)):
            try:
                data = stream.read(chunk_size)
                frames.append(data)
                
                # Calculate audio level for visual feedback
                audio_array = np.frombuffer(data, dtype=np.int16)
                audio_level = np.abs(audio_array).mean()
                level_bar = int(min(audio_level / 50, 50))
                
                # Print a progress bar with audio level
                progress = int((i / (sample_rate / chunk_size * duration)) * 50)
                print(f"\r[{'#' * progress}{' ' * (50-progress)}] {int((i / (sample_rate / chunk_size * duration)) * 100)}% | Level: {audio_level:.1f} [{'#' * level_bar}{' ' * (50-level_bar)}]", end="")
            except Exception as e:
                print(f"\nError reading from microphone: {e}")
                break
        
        print("\nFinished recording!")
        
        # Stop and close the stream
        stream.stop_stream()
        stream.close()
        
        # Save to a WAV file
        filename = "test_audio.wav"
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
            wf.setframerate(sample_rate)
            wf.writeframes(b''.join(frames))
        
        print(f"Audio saved to {filename}")
        return filename
    
    except Exception as e:
        print(f"\nError setting up audio recording: {e}")
        return None
    finally:
        p.terminate()

def detect_silence(audio_data, threshold=300):
    """Detect if audio contains silence based on amplitude threshold"""
    audio_array = np.frombuffer(audio_data, dtype=np.int16)
    audio_level = np.abs(audio_array).mean()
    return audio_level <= threshold

def test_voice_activity_detection(duration=10, sample_rate=44100, chunk_size=1024, threshold=300):
    """Test voice activity detection by monitoring audio levels"""
    p = pyaudio.PyAudio()
    
    # Open stream
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=sample_rate,
        input=True,
        frames_per_buffer=chunk_size
    )
    
    print(f"Monitoring audio levels for {duration} seconds...")
    print(f"Speak into your microphone to see the audio levels")
    print(f"Silence threshold is set to {threshold}")
    
    # Monitor audio levels
    start_time = time.time()
    while time.time() - start_time < duration:
        data = stream.read(chunk_size)
        audio_array = np.frombuffer(data, dtype=np.int16)
        audio_level = np.abs(audio_array).mean()
        
        # Create a visual representation of the audio level
        level_bar = int(min(audio_level / 50, 50))
        is_speech = "SPEECH" if audio_level > threshold else "SILENCE"
        
        print(f"\r[{'#' * level_bar}{' ' * (50-level_bar)}] Level: {audio_level:.1f} - {is_speech}", end="")
        
        time.sleep(0.1)
    
    print("\nFinished monitoring!")
    
    # Stop and close the stream
    stream.stop_stream()
    stream.close()
    p.terminate()

def play_audio(filename):
    """Play the recorded audio file using pydub"""
    if not os.path.exists(filename):
        print(f"File {filename} not found.")
        return False
    
    try:
        print(f"\nPlaying back recorded audio from {filename}...")
        
        # Use pydub for playback (works with both WAV and MP3)
        if filename.endswith('.wav'):
            sound = AudioSegment.from_wav(filename)
        elif filename.endswith('.mp3'):
            sound = AudioSegment.from_mp3(filename)
        else:
            raise ValueError(f"Unsupported file format: {filename}")
        
        # Play the audio
        play(sound)
        print("Playback finished!")
        return True
    except Exception as e:
        print(f"Error using pydub for playback: {e}")
        print("Falling back to PyAudio playback...")
        
        try:
            # Fall back to PyAudio if pydub fails
            # Only works for WAV files
            if not filename.endswith('.wav'):
                print(f"Cannot play {filename} with PyAudio. PyAudio only supports WAV files.")
                return False
                
            # Open the audio file
            wf = wave.open(filename, 'rb')
            
            # Create PyAudio instance
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
                stream.write(data)
                data = wf.readframes(chunk_size)
            
            # Clean up
            stream.stop_stream()
            stream.close()
            p.terminate()
            
            print("Playback finished!")
            return True
        except Exception as e:
            print(f"Error playing audio with PyAudio: {e}")
            return False

def main():
    print("===== VTuber AI Bot - Microphone Test =====")
    print("1. Record a test audio file")
    print("2. Test voice activity detection")
    print("3. Play recorded test audio")
    print("4. Test full audio pipeline (record, play, and analyze)")
    print("q. Quit")
    
    choice = input("Enter your choice: ")
    
    if choice == "1":
        duration = int(input("Enter recording duration in seconds (default: 5): ") or "5")
        filename = record_audio(duration)
        if filename:
            play_choice = input("\nDo you want to play back the recording? (y/n): ")
            if play_choice.lower() == 'y':
                play_audio(filename)
            print("\nYou can now run test_bot.py to test the Whisper API with this audio file.")
    elif choice == "2":
        duration = int(input("Enter monitoring duration in seconds (default: 10): ") or "10")
        threshold = int(input("Enter silence threshold (default: 300): ") or "300")
        test_voice_activity_detection(duration, threshold=threshold)
    elif choice == "3":
        filename = "test_audio.wav"
        play_audio(filename)
    elif choice == "4":
        print("\nTesting full audio pipeline:")
        print("1. Recording audio...")
        duration = int(input("Enter recording duration in seconds (default: 5): ") or "5")
        filename = record_audio(duration)
        
        if filename:
            print("\n2. Playing back recording...")
            play_audio(filename)
            
            print("\n3. Analyzing audio levels...")
            with wave.open(filename, 'rb') as wf:
                # Get audio data
                n_frames = wf.getnframes()
                audio_data = wf.readframes(n_frames)
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                
                # Calculate stats
                mean_level = np.abs(audio_array).mean()
                max_level = np.abs(audio_array).max()
                
                print(f"Audio statistics:")
                print(f"  - Mean level: {mean_level:.2f}")
                print(f"  - Max level: {max_level}")
                print(f"  - Recommended silence threshold: {mean_level * 0.5:.0f}")
                
                # Suggest next steps
                print("\nRecommended next steps:")
                print("1. Run 'python -m src.tests.test_bot' to test the Whisper API with this audio file")
                print("2. Update the SILENCE_THRESHOLD in your .env file if needed")
    elif choice.lower() == "q":
        print("Exiting...")
    else:
        print("Invalid choice!")

if __name__ == "__main__":
    main()
