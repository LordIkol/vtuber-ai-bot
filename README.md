# VTuber AI Bot

A Python-based VTuber AI bot that can interact via voice and Twitch chat. This bot uses OpenAI's GPT for AI responses, ElevenLabs for high-quality text-to-speech, and can integrate with VTube Studio for avatar animations.

## Features

- **Voice Interaction**: Speak to your microphone and get AI-powered responses
- **AI Chat**: Powered by OpenAI's GPT models
- **High-Quality TTS**: Using ElevenLabs for natural-sounding voice
- **Twitch Integration**: Respond to chat commands with AI responses
- **VTube Studio Integration**: Trigger avatar animations
- **Hotkey Support**: Use keyboard shortcuts to control recording
- **Configurable Settings**: Customize all aspects of the bot via .env file

## Setup

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Configure the bot**:
Create a `.env` file with your configuration (see Configuration section below)

3. **Run the bot**:
```bash
python main.py
```

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
TTS_VOLUME=1.0
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
AI_CHAT_RESPONSE=true

# Message Queue Settings
ENABLE_MESSAGE_QUEUE=true
MAX_QUEUE_SIZE=10
QUEUE_FULL_MESSAGE=I'm currently busy. Please try again later!
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

### Console Commands
- `volume <level>` - Set TTS volume (0.1-2.0)
- `chatresponse` - Toggle chat responses for AI commands on/off
- `messagequeue` - Toggle message queue on/off
- `queuesize <n>` - Set maximum message queue size (1-50)
- `status` - Show current bot status
- `exit` - Exit the bot
- `help` - Show available commands

## Configuration Details

### AI_CHAT_RESPONSE
When set to `true`, the bot will respond to AI commands in Twitch chat with text. When set to `false`, the bot will only respond with voice (TTS) and not send text to the chat.

### TTS_VOLUME
Controls the volume of the text-to-speech output. Values range from 0.1 (very quiet) to 2.0 (very loud). Default is 1.0.

### HOTKEY_MODE
When set to `true`, the bot will use a hotkey to start/stop recording. When set to `false`, the bot will use voice activity detection.

### ENABLE_MESSAGE_QUEUE
When set to `true`, the bot will process AI commands one at a time in a queue. This prevents multiple messages from playing simultaneously. When set to `false`, messages will be processed immediately as they arrive.

### MAX_QUEUE_SIZE
Sets the maximum number of messages that can be in the queue at once. When the queue is full, new messages will be rejected with the QUEUE_FULL_MESSAGE. Values range from 1 to 50.

### QUEUE_FULL_MESSAGE
The message sent to Twitch chat when the queue is full and a new command is received.

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
