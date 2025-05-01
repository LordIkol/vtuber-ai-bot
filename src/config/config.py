"""
Configuration settings for the VTuber AI Bot.
"""

import os
from dotenv import load_dotenv

class Config:
    """Configuration class for the VTuber AI Bot."""
    
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # API Keys
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.elevenlabs_api_key = os.getenv('ELEVENLABS_API_KEY')
        self.elevenlabs_voice_id = os.getenv('ELEVENLABS_VOICE_ID')
        
        # Twitch Configuration
        self.twitch_client_id = os.getenv('TWITCH_CLIENT_ID')
        self.twitch_token = os.getenv('TWITCH_TOKEN')
        self.twitch_nick = os.getenv('TWITCH_NICK')
        self.twitch_channel = os.getenv('TWITCH_CHANNEL')
        self.twitch_prefix = os.getenv('TWITCH_PREFIX', '!')
        
        # VTube Studio Configuration
        self.vtube_studio_ws_url = os.getenv('VTUBESTUDIO_WS_URL')
        self.vtube_studio_ip = os.getenv('VTUBE_STUDIO_IP', '127.0.0.1')
        self.vtube_studio_port = int(os.getenv('VTUBE_STUDIO_PORT', '8001'))
        
        # Audio Configuration
        self.sample_rate = int(os.getenv('SAMPLE_RATE', '44100'))
        self.chunk_size = int(os.getenv('CHUNK_SIZE', '1024'))
        self.silence_threshold = int(os.getenv('SILENCE_THRESHOLD', '300'))
        self.silence_duration = float(os.getenv('SILENCE_DURATION', '2.0'))
        
        # TTS Configuration
        self.tts_volume = float(os.getenv('TTS_VOLUME', '1.0'))
        
        # Input Configuration
        self.hotkey_mode = os.getenv('HOTKEY_MODE', 'True').lower() == 'true'
        self.recording_hotkey = os.getenv('RECORDING_HOTKEY', 'f9')
        
        # Logging Configuration
        self.log_file = os.getenv('LOG_FILE', 'vtuber_bot.log')
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        
        # AI Command Settings
        self.ai_command_prefix = os.getenv('AI_COMMAND_PREFIX', '!Fenris')
        self.ai_chat_response = os.getenv('AI_CHAT_RESPONSE', 'False').lower() == 'true'
        
        # Message Queue Settings
        self.enable_message_queue = os.getenv('ENABLE_MESSAGE_QUEUE', 'True').lower() == 'true'
        self.max_queue_size = int(os.getenv('MAX_QUEUE_SIZE', '10'))
        self.queue_full_message = os.getenv('QUEUE_FULL_MESSAGE', "I'm currently busy. Please try again later!")
    
    def validate(self):
        """Validate that all required configuration is present."""
        missing = []
        
        if not self.openai_api_key:
            missing.append("OPENAI_API_KEY")
        
        if not self.elevenlabs_api_key:
            missing.append("ELEVENLABS_API_KEY")
            
        if not self.elevenlabs_voice_id:
            missing.append("ELEVENLABS_VOICE_ID")
        
        # Twitch is optional, but if any Twitch config is provided, all should be
        if any([self.twitch_client_id, self.twitch_token, self.twitch_nick, self.twitch_channel]) and \
           not all([self.twitch_client_id, self.twitch_token, self.twitch_nick, self.twitch_channel]):
            missing.append("TWITCH_* (some Twitch configuration is missing)")
        
        if not self.vtube_studio_ws_url:
            missing.append("VTUBESTUDIO_WS_URL")
        
        return missing
