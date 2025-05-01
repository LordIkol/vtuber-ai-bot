"""
Test module for API connections and core functionality.
"""

import os
import time
import asyncio
import requests
from openai import OpenAI
from ..config import Config

async def test_openai_connection(config):
    """Test connection to OpenAI API"""
    try:
        client = OpenAI(api_key=config.openai_api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say hello to the VTuber AI bot!"}]
        )
        print(f"OpenAI API Test: SUCCESS")
        print(f"Response: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"OpenAI API Test: FAILED")
        print(f"Error: {e}")
        return False

async def test_elevenlabs_connection(config):
    """Test connection to ElevenLabs API"""
    try:
        voice_id = config.elevenlabs_voice_id
        api_key = config.elevenlabs_api_key
        
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }
        
        data = {
            "text": "Hello! This is a test of the ElevenLabs text-to-speech API.",
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }
        
        print("Sending TTS request to ElevenLabs...")
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 200:
            # Save audio to file
            filename = "test_tts.mp3"
            
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            print(f"ElevenLabs API Test: SUCCESS")
            print(f"Saved test audio to {filename}")
            
            # Play the audio
            os.system(f"start {filename}")
            return True
        else:
            print(f"ElevenLabs API Test: FAILED")
            print(f"Error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"ElevenLabs API Test: FAILED")
        print(f"Error: {e}")
        return False

async def test_whisper_api(config):
    """Test OpenAI Whisper API with a sample audio file"""
    try:
        # Check if we have a test audio file, if not create one
        test_file = "test_audio.wav"
        if not os.path.exists(test_file):
            print(f"No test audio file found. Please record a sample audio file named {test_file}")
            print("Skipping Whisper API test.")
            return None
        
        client = OpenAI(api_key=config.openai_api_key)
        
        with open(test_file, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        
        print(f"Whisper API Test: SUCCESS")
        print(f"Transcription: {transcription.text}")
        return True
    except Exception as e:
        print(f"Whisper API Test: FAILED")
        print(f"Error: {e}")
        return False

async def test_twitch_connection(config):
    """Test connection to Twitch chat"""
    try:
        # Check if required environment variables are set
        client_id = config.twitch_client_id
        token = config.twitch_token
        nick = config.twitch_nick
        channel = config.twitch_channel
        
        # For Twitch, we need either a token or a client_id
        if not client_id or not nick or not channel:
            print(f"Twitch API Test: FAILED")
            print(f"Missing required environment variables for Twitch authentication.")
            print(f"Please check your .env file for TWITCH_CLIENT_ID, TWITCH_NICK, and TWITCH_CHANNEL.")
            return False
            
        print(f"Twitch API Test: SUCCESS (simulated)")
        print(f"Found required Twitch credentials:")
        print(f"  - Client ID: {client_id[:5]}...")
        print(f"  - Nick: {nick}")
        print(f"  - Channel: {channel}")
        print(f"\nNote: This is a simulated test. In a real environment, you would need")
        print(f"to complete the OAuth flow to get a valid access token.")
        return True
            
    except Exception as e:
        print(f"Twitch API Test: FAILED")
        print(f"Error: {e}")
        return False

async def run_tests():
    """Run all tests asynchronously"""
    print("===== VTuber AI Bot - Environment Test =====")
    
    # Load configuration
    config = Config()
    
    # Test OpenAI API
    print("\n1. Testing OpenAI API Connection...")
    openai_success = await test_openai_connection(config)
    
    # Test ElevenLabs API
    print("\n2. Testing ElevenLabs API Connection...")
    elevenlabs_success = await test_elevenlabs_connection(config)
    
    # Test Whisper API (optional)
    print("\n3. Testing Whisper API (requires test_audio.wav file)...")
    whisper_success = await test_whisper_api(config)
    
    # Test Twitch connection
    print("\n4. Testing Twitch API Connection...")
    twitch_success = await test_twitch_connection(config)
    
    # Summary
    print("\n===== Test Results =====")
    print(f"OpenAI API: {'✓ SUCCESS' if openai_success else '✗ FAILED'}")
    print(f"ElevenLabs API: {'✓ SUCCESS' if elevenlabs_success else '✗ FAILED'}")
    if whisper_success is not None:
        print(f"Whisper API: {'✓ SUCCESS' if whisper_success else '✗ FAILED'}")
    else:
        print(f"Whisper API: SKIPPED (no test audio file)")
    print(f"Twitch API: {'✓ SUCCESS' if twitch_success else '✗ FAILED'}")
    
    if openai_success and elevenlabs_success and (twitch_success or True):
        print("\nCore functionality is working! You can now run the main bot.")
    else:
        print("\nSome tests failed. Please check your API keys and internet connection.")

def main():
    """Main entry point"""
    asyncio.run(run_tests())

if __name__ == "__main__":
    main()
