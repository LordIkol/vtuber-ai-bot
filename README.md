# VTuber AI Bot

A Python-based VTuber AI bot that can interact via voice and Twitch chat. This bot uses OpenAI's GPT for AI responses, ElevenLabs for high-quality text-to-speech, and can integrate with VTube Studio for avatar animations.

## Features

- **Modern Web UI**: Easy-to-use interface built with NiceGUI for controlling all bot functions
- **Voice Interaction**: Speak to your microphone and get AI-powered responses
- **AI Chat**: Powered by OpenAI's GPT models with optional Assistant API support
- **Dual TTS Support**: Choose between ElevenLabs and Coqui TTS engines
- **Twitch Integration**: Respond to chat commands with AI responses
- **VTube Studio Integration**: Trigger avatar animations
- **Hotkey Support**: Optional keyboard shortcuts to control recording
- **Real-time Logs**: View bot activity and errors in real-time through the UI
- **Message Queue**: Manage multiple requests with configurable queue size

## Setup

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Set up FFmpeg**:
The bot requires FFmpeg for audio processing. Run the setup script to download and configure FFmpeg:
```bash
python setup_ffmpeg.py
```

3. **Configure the bot**:
Create a `.env` file with your configuration (see Configuration section below)

4. **Start the UI**:
```bash
python ui_main.py
```
The UI will open in your default web browser at http://localhost:8080

## Configuration

All configuration is done through the `.env` file. Here's a complete list of available settings:

### API Keys
```
# Required API Keys
OPENAI_API_KEY=your_openai_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
ELEVENLABS_VOICE_ID=your_voice_id
```

### Twitch Integration
```
# Twitch Authentication (optional but required for Twitch features)
TWITCH_CLIENT_ID=your_twitch_client_id
TWITCH_TOKEN=your_twitch_token
TWITCH_NICK=your_twitch_username
TWITCH_CHANNEL=your_channel_name
TWITCH_PREFIX=!
```

### VTube Studio Integration
```
# VTube Studio Configuration
VTUBESTUDIO_WS_URL=ws://localhost:8001
VTUBE_STUDIO_IP=127.0.0.1
VTUBE_STUDIO_PORT=8001
```

### Audio Settings
```
# Audio Configuration
SAMPLE_RATE=44100
CHUNK_SIZE=1024
SILENCE_THRESHOLD=300
SILENCE_DURATION=2.0

# TTS Configuration
TTS_ENGINE=coqui
TTS_VOLUME=1.0
COQUI_MODEL=tts_models/en/ljspeech/tacotron2-DDC
COQUI_VOCODER=vocoder_models/en/ljspeech/hifigan_v2
```

### Input Settings
```
# Input Configuration
HOTKEY_MODE=True
RECORDING_HOTKEY=f9
```

### AI Command Settings
```
# AI Command Settings
AI_COMMAND_PREFIX=!AI
AI_CHAT_RESPONSE=false
USE_ASSISTANT_API=false
OPENAI_ASSISTANT_ID=your_assistant_id_here
AI_SYSTEM_INSTRUCTIONS=You are a friendly and engaging VTuber AI assistant. Your responses should be concise, entertaining, and suitable for streaming platforms.

# Message Queue Settings
ENABLE_MESSAGE_QUEUE=true
MAX_QUEUE_SIZE=5
QUEUE_FULL_MESSAGE=The message queue is full
```

### Logging
```
# Logging Configuration
LOG_FILE=vtuber_bot.log
LOG_LEVEL=INFO
```

## Usage

### Voice Interaction
- Press the configured hotkey (default: F9) to start/stop recording
- Speak naturally to interact with the bot
- The bot will respond with AI-generated text and speech

### Twitch Chat Commands
- Use the configured AI command prefix (default: `!AI`) followed by your message
- Example: `!AI Tell me a joke`
- The bot will respond in chat and/or with voice based on your settings

### Web UI Features
- **Settings Tab**: Configure all bot settings including API keys and audio options
- **Logs Tab**: View real-time bot activity and error logs
- **Controls**:
  - Start/Stop Bot: Control the bot's operation
  - TTS Volume Slider: Adjust speech volume in real-time
  - TTS Engine Toggle: Switch between ElevenLabs and Coqui TTS
  - Clear Logs: Clear the log display
  - Shutdown: Safely stop the bot and close the UI

## Configuration Details

### TTS Configuration
- **TTS_ENGINE**: Choose between 'elevenlabs' or 'coqui' for text-to-speech
- **TTS_VOLUME**: Controls volume (0.1-2.0, default: 1.0)
- **COQUI_MODEL**: Coqui TTS model to use
- **COQUI_VOCODER**: Coqui vocoder model for audio generation

### AI Configuration
- **AI_CHAT_RESPONSE**: Enable/disable text responses in Twitch chat
- **USE_ASSISTANT_API**: Use OpenAI's Assistant API instead of Chat Completions
- **OPENAI_ASSISTANT_ID**: Assistant ID when using Assistant API
- **AI_SYSTEM_INSTRUCTIONS**: Custom personality/behavior instructions for the AI

### Input Configuration
- **HOTKEY_MODE**: Use hotkey (true) or voice activity detection (false)
- **RECORDING_HOTKEY**: Keyboard key to start/stop recording (when HOTKEY_MODE is true)
- **MICROPHONE_DEVICE_ID**: Specific microphone to use (empty for default)

### Message Queue
- **ENABLE_MESSAGE_QUEUE**: Process messages sequentially to prevent overlap
- **MAX_QUEUE_SIZE**: Maximum pending messages (1-50)
- **QUEUE_FULL_MESSAGE**: Response when queue is full

## Requirements

- Python 3.8+
- VTube Studio (for avatar animations)
- OpenAI API key
- ElevenLabs API key
- Twitch Developer account (for bot authentication)

## Troubleshooting

- **VTube Studio Connection Error**: If you see a connection error, make sure VTube Studio is running and the WebSocket API is enabled
- **No Audio Input**: Check your microphone settings and make sure it's properly connected
- **API Key Issues**: Verify your API keys are correct in the `.env` file

## License

This project is licensed under the MIT License - see the LICENSE file for details.
