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
        
        # OpenAI Assistant API Configuration
        self.use_assistant_api = os.getenv('USE_ASSISTANT_API', 'False').lower() == 'true'
        self.openai_assistant_id = os.getenv('OPENAI_ASSISTANT_ID')
        
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
        
        # Audio device configuration
        self.output_device_id = os.getenv('OUTPUT_DEVICE_ID', '')
        # Convert to int if provided, otherwise None
        if self.output_device_id.strip():
            try:
                self.output_device_id = int(self.output_device_id)
            except ValueError:
                self.output_device_id = None
        else:
            self.output_device_id = None
        
        # TTS Configuration
        self.tts_engine = os.getenv('TTS_ENGINE', 'elevenlabs').lower()  # 'elevenlabs' or 'coqui'
        self.tts_volume = float(os.getenv('TTS_VOLUME', '1.0'))
        
        # Coqui TTS Configuration
        self.coqui_model = os.getenv('COQUI_MODEL', 'tts_models/en/ljspeech/tacotron2-DDC')
        self.coqui_vocoder = os.getenv('COQUI_VOCODER', 'vocoder_models/en/ljspeech/hifigan_v2')
        
        # Input Configuration
        self.hotkey_mode = os.getenv('HOTKEY_MODE', 'True').lower() == 'true'
        self.recording_hotkey = os.getenv('RECORDING_HOTKEY', 'f9')
        self.microphone_device_id = os.getenv('MICROPHONE_DEVICE_ID', '')
        # Convert to int if provided, otherwise None
        if self.microphone_device_id.strip():
            try:
                self.microphone_device_id = int(self.microphone_device_id)
            except ValueError:
                self.microphone_device_id = None
        else:
            self.microphone_device_id = None
        
        # Logging Configuration
        self.log_file = os.getenv('LOG_FILE', 'vtuber_bot.log')
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        
        # AI Command Settings
        self.ai_command_prefix = os.getenv('AI_COMMAND_PREFIX', '!Fenris')
        self.ai_chat_response = os.getenv('AI_CHAT_RESPONSE', 'False').lower() == 'true'
        
        # AI System Instructions (for standard Chat Completions API)
        default_instructions = """You are Fenris, a friendly and engaging VTuber AI assistant. 
            Your responses should be concise, entertaining, and suitable for streaming platforms. 
            Keep your responses under 2-3 sentences when possible. 
            You can be playful and show personality, but always remain helpful and appropriate for all audiences. 
            If asked about topics you don't have information on, be honest about your limitations.
            Avoid overly technical language unless specifically asked for technical details."""
        self.ai_system_instructions = os.getenv('AI_SYSTEM_INSTRUCTIONS', default_instructions)
        
        # Message Queue Settings
        self.enable_message_queue = os.getenv('ENABLE_MESSAGE_QUEUE', 'True').lower() == 'true'
        self.max_queue_size = int(os.getenv('MAX_QUEUE_SIZE', '10'))
        self.queue_full_message = os.getenv('QUEUE_FULL_MESSAGE', "I'm currently busy. Please try again later!")
    
    def validate(self):
        """Validate that all required configuration is present."""
        missing = []
        
        if not self.openai_api_key:
            missing.append("OPENAI_API_KEY")
            
        # Check for Assistant API configuration if enabled
        if self.use_assistant_api and not self.openai_assistant_id:
            missing.append("OPENAI_ASSISTANT_ID (required when USE_ASSISTANT_API is True)")
        
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
