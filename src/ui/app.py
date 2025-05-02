"""
NiceGUI UI for VTuber AI Bot.
"""

import os
import sys
import time
import json
import asyncio
import logging
import pyaudio
from dotenv import load_dotenv, set_key
from pathlib import Path
from io import StringIO
from nicegui import ui, app, events
from datetime import datetime

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.config import Config
from src.vtuber_bot import VTuberBot

# Module-level constants
BOOLEAN_KEYS = ['HOTKEY_MODE', 'AI_CHAT_RESPONSE', 'USE_ASSISTANT_API', 'ENABLE_MESSAGE_QUEUE']
TTS_ENGINE_ELEVENLABS = 'elevenlabs'
TTS_ENGINE_COQUI = 'coqui'
CSS_BTN_BASE = 'flex-1 py-2 px-4 rounded-lg text-center font-medium'
CSS_BTN_GREEN = f'{CSS_BTN_BASE} bg-green-500 text-white shadow'
CSS_BTN_GRAY = f'{CSS_BTN_BASE} bg-gray-600 text-white'
CSS_LABEL_SM = 'text-sm mb-2'
CSS_LABEL_XS = 'text-xs text-gray-500 mt-1'
CSS_LABEL_H6 = 'text-h6'
CSS_ROW_FULL = 'w-full items-center'
CSS_GRID_FULL = 'w-full'
CSS_INPUT_FULL = 'w-full'

# Configure logging
logger = logging.getLogger(__name__)

# Create a string IO for capturing logs
log_stream = StringIO()

# Create a custom handler that writes to our StringIO
class StringIOHandler(logging.StreamHandler):
    def __init__(self, stream=None):
        super().__init__(stream)
        self.stream = stream
        
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            stream.write(msg + '\n')
            stream.flush()
        except Exception:
            self.handleError(record)

# Add our handler to the root logger
root_logger = logging.getLogger()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stream_handler = StringIOHandler(log_stream)
stream_handler.setFormatter(formatter)
root_logger.addHandler(stream_handler)

# Also log to stdout
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(formatter)
root_logger.addHandler(stdout_handler)

# Path to the .env file
ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.env"))

# Global variables
bot_instance = None
bot_thread = None

class BotState:
    """Encapsulate the bot's running state."""
    def __init__(self):
        self.running_event = asyncio.Event()

    def is_running(self):
        return self.running_event.is_set()

    async def start(self):
        self.running_event.set()

    async def stop(self):
        self.running_event.clear()

# Instantiate BotState
bot_state = BotState()

# NiceGUI app configuration
app.title = 'VTuber AI Bot'

def load_env_settings():
    """Load settings from .env file."""
    load_dotenv(ENV_PATH)
    
    # Group settings by category
    settings = {
        "API Keys": {
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
            "ELEVENLABS_API_KEY": os.getenv("ELEVENLABS_API_KEY", ""),
            "ELEVENLABS_VOICE_ID": os.getenv("ELEVENLABS_VOICE_ID", ""),
        },
        "Twitch": {
            "TWITCH_CLIENT_ID": os.getenv("TWITCH_CLIENT_ID", ""),
            "TWITCH_TOKEN": os.getenv("TWITCH_TOKEN", ""),
            "TWITCH_NICK": os.getenv("TWITCH_NICK", ""),
            "TWITCH_CHANNEL": os.getenv("TWITCH_CHANNEL", ""),
            "TWITCH_PREFIX": os.getenv("TWITCH_PREFIX", "!"),
        },
        "VTube Studio": {
            "VTUBESTUDIO_WS_URL": os.getenv("VTUBESTUDIO_WS_URL", "ws://localhost:8001"),
            "VTUBE_STUDIO_IP": os.getenv("VTUBE_STUDIO_IP", "127.0.0.1"),
            "VTUBE_STUDIO_PORT": os.getenv("VTUBE_STUDIO_PORT", "8001"),
        },
        "Audio": {
            "SAMPLE_RATE": os.getenv("SAMPLE_RATE", "44100"),
            "CHUNK_SIZE": os.getenv("CHUNK_SIZE", "1024"),
            "SILENCE_THRESHOLD": os.getenv("SILENCE_THRESHOLD", "300"),
            "SILENCE_DURATION": os.getenv("SILENCE_DURATION", "2.0"),
        },
        "TTS": {
            "TTS_ENGINE": os.getenv("TTS_ENGINE", "elevenlabs"),
            "TTS_VOLUME": os.getenv("TTS_VOLUME", "1.0"),
            "COQUI_MODEL": os.getenv("COQUI_MODEL", "tts_models/en/ljspeech/tacotron2-DDC"),
            "COQUI_VOCODER": os.getenv("COQUI_VOCODER", "vocoder_models/en/ljspeech/hifigan_v2"),
        },
        "Input": {
            "HOTKEY_MODE": os.getenv("HOTKEY_MODE", "True"),
            "RECORDING_HOTKEY": os.getenv("RECORDING_HOTKEY", "f9"),
            "MICROPHONE_DEVICE_ID": os.getenv("MICROPHONE_DEVICE_ID", ""),
        },
        "Logging": {
            "LOG_FILE": os.getenv("LOG_FILE", "vtuber_bot.log"),
            "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
        },
        "AI": {
            "AI_COMMAND_PREFIX": os.getenv("AI_COMMAND_PREFIX", "!AI"),
            "AI_CHAT_RESPONSE": os.getenv("AI_CHAT_RESPONSE", "False"),
            "USE_ASSISTANT_API": os.getenv("USE_ASSISTANT_API", "False"),
            "OPENAI_ASSISTANT_ID": os.getenv("OPENAI_ASSISTANT_ID", ""),
            "AI_SYSTEM_INSTRUCTIONS": os.getenv("AI_SYSTEM_INSTRUCTIONS", 
                "You are Fenris, a friendly and engaging VTuber. Your responses should be concise, entertaining, and suitable for streaming platforms."),
        },
        "Message Queue": {
            "ENABLE_MESSAGE_QUEUE": os.getenv("ENABLE_MESSAGE_QUEUE", "True"),
            "MAX_QUEUE_SIZE": os.getenv("MAX_QUEUE_SIZE", "10"),
            "QUEUE_FULL_MESSAGE": os.getenv("QUEUE_FULL_MESSAGE", "I'm currently busy. Please try again later!"),
        },
    }
    
    return settings

def get_available_microphones():
    """Get a list of available microphone devices."""
    try:
        p = pyaudio.PyAudio()
        info = p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        
        input_devices = []
        
        for i in range(0, numdevices):
            device_info = p.get_device_info_by_host_api_device_index(0, i)
            if device_info.get('maxInputChannels') > 0:
                input_devices.append((i, device_info.get('name')))
        
        p.terminate()
        return input_devices
    except Exception as e:
        logger.error(f"Error getting microphone devices: {e}")
        return []

def save_env_settings(settings):
    """Save settings to .env file."""
    try:
        # Flatten the settings dictionary
        flat_settings = {}
        for category, category_settings in settings.items():
            for key, value in category_settings.items():
                flat_settings[key] = value
        
        # Create a backup of the .env file
        env_path = Path(ENV_PATH)
        if env_path.exists():
            with open(ENV_PATH, 'r') as f:
                original_content = f.read()
            backup_path = env_path.with_suffix('.env.bak')
            with open(backup_path, 'w') as f:
                f.write(original_content)
        
        # Write settings to .env file without quotes
        with open(ENV_PATH, 'w') as f:
            for key, value in flat_settings.items():
                f.write(f"{key}={value}\n")
        
        # Reload environment variables
        load_dotenv(ENV_PATH, override=True)
        
        logger.info("Settings saved to .env file")
        return True
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        return False

async def run_bot():
    """Run the VTuber bot."""
    async def bot_task():
        global bot_instance
        try:
            logger.info("Starting VTuber AI Bot...")
            
            # Create and initialize the bot
            config = Config()
            missing_config = config.validate()
            
            if missing_config:
                logger.error(f"Missing configuration: {', '.join(missing_config)}")
                return
            
            bot_instance = VTuberBot()
            await bot_instance.initialize()
            
            # Set the running flag
            await bot_state.start()
            await bot_instance.run()
            
        except Exception as e:
            logger.error(f"Error running bot: {e}")
        finally:
            await bot_state.stop()
            logger.info("Bot stopped")
    
    # Create an asyncio task that runs in the background
    asyncio.create_task(bot_task())
    
    return True

async def stop_bot():
    """Stop the VTuber bot."""
    try:
        logger.info("Stopping VTuber AI Bot...")
        if bot_instance:
            # Set the running flag to False to stop the bot's main loop
            bot_instance.running = False
            # Set our UI state
            await bot_state.stop()
            logger.info("Bot stopping - set running flag to False")
        return True
    except Exception as e:
        logger.error(f"Error stopping bot: {e}")
        return False

def select_engine(engine, tts_container, elevenlabs_btn, coqui_btn):
    """Update TTS engine selection and button styles."""
    tts_container.value = engine
    if engine == TTS_ENGINE_ELEVENLABS:
        elevenlabs_btn.classes(replace=CSS_BTN_GREEN)
        coqui_btn.classes(replace=CSS_BTN_GRAY)
    else:
        elevenlabs_btn.classes(replace=CSS_BTN_GRAY)
        coqui_btn.classes(replace=CSS_BTN_GREEN)

async def list_microphones(input_elements):
    """List available microphones and allow user selection."""
    mics = get_available_microphones()
    with ui.dialog() as dialog, ui.card():
        ui.label('Available Microphones').classes(CSS_LABEL_H6)
        for mic_id, mic_name in mics:
            with ui.row().classes(CSS_ROW_FULL):
                ui.label(f"ID {mic_id}: {mic_name}").classes('flex-grow')
                def use_mic(mic_id=mic_id):
                    input_elements['MICROPHONE_DEVICE_ID'].value = str(mic_id)
                    dialog.close()
                ui.button(f"Use ID {mic_id}", on_click=use_mic).props('color=primary size=sm')
        ui.button('Close', on_click=dialog.close).props('color=secondary')

def create_input_field(key, value, input_elements):
    """Create an input field based on the key and value type."""
    if key in BOOLEAN_KEYS:
        input_elements[key] = ui.switch(value=value.lower() == 'true')
    elif key == 'TTS_ENGINE':
        with ui.element('div').classes(CSS_GRID_FULL):
            tts_container = ui.element('div')
            tts_container.value = value
            ui.label('TTS Engine Selection:').classes(CSS_LABEL_SM)
            with ui.element('div').classes('flex justify-center w-full'):
                with ui.element('div').classes('bg-gray-300 rounded-lg p-1 flex w-full'):
                    is_elevenlabs = value == TTS_ENGINE_ELEVENLABS
                    # Create buttons with custom styling
                    elevenlabs_btn = ui.button(
                        'ElevenLabs (Cloud)',
                        on_click=lambda: select_engine(TTS_ENGINE_ELEVENLABS, tts_container, elevenlabs_btn, coqui_btn)
                    ).props('flat').classes(CSS_BTN_GREEN if is_elevenlabs else CSS_BTN_GRAY)
                    
                    coqui_btn = ui.button(
                        'Coqui (Local)',
                        on_click=lambda: select_engine(TTS_ENGINE_COQUI, tts_container, elevenlabs_btn, coqui_btn)
                    ).props('flat').classes(CSS_BTN_GREEN if not is_elevenlabs else CSS_BTN_GRAY)
            ui.label('Select your preferred TTS engine').classes(CSS_LABEL_XS)
            input_elements[key] = tts_container
    elif key == 'AI_SYSTEM_INSTRUCTIONS':
        input_elements[key] = ui.textarea(value=value, placeholder=key).classes(CSS_INPUT_FULL)
    elif 'API_KEY' in key or 'TOKEN' in key:
        input_elements[key] = ui.input(value=value, placeholder=key, password=True).classes(CSS_INPUT_FULL)
    elif key == 'MICROPHONE_DEVICE_ID':
        with ui.row().classes(CSS_ROW_FULL):
            input_elements[key] = ui.input(value=value, placeholder=key).classes(CSS_INPUT_FULL)
            ui.button('List Microphones', on_click=lambda: asyncio.create_task(list_microphones(input_elements))).props('color=primary size=sm')
    else:
        input_elements[key] = ui.input(value=value, placeholder=key).classes(CSS_INPUT_FULL)

# Create the NiceGUI UI
@ui.page('/')
def main_page():
    """Main NiceGUI UI page."""
    # Load settings
    settings = load_env_settings()
    
    # Create UI elements
    with ui.header().classes('bg-primary text-white w-full'):
        ui.label('VTuber AI Bot').classes('text-h4')
    
    # Set up a container for the content with max width
    with ui.element('div').classes('w-full max-w-6xl mx-auto'):
        # Create tabs
        with ui.tabs().classes('w-full') as tabs:
            settings_tab = ui.tab('Settings', icon='settings')
            logs_tab = ui.tab('Logs', icon='article')
        
        # Create tab panels container
        with ui.tab_panels(tabs).classes('w-full'):
            
            # Settings Tab Content
            with ui.tab_panel(settings_tab):
                ui.label('Bot Settings').classes('text-h5')
                
                # Store input elements for each setting
                input_elements = {}
            
                # Create an accordion for each category
                for category, category_settings in settings.items():
                    with ui.expansion(f"{category} Settings", icon='settings').classes('w-full'):
                        with ui.grid(columns=2).classes(CSS_GRID_FULL):
                            for key, value in category_settings.items():
                                ui.label(key).classes('self-center')
                                create_input_field(key, value, input_elements)
            
                # Save button
                async def save_settings():
                    # Collect all settings
                    updated_settings = {}
                    for category, category_settings in settings.items():
                        updated_settings[category] = {}
                        for key in category_settings:
                            # Handle different input types
                            if isinstance(input_elements[key], ui.switch):
                                updated_settings[category][key] = str(input_elements[key].value)
                            elif key == 'TTS_ENGINE':
                                # Get the value from the radio container
                                updated_settings[category][key] = input_elements[key].value
                            else:
                                updated_settings[category][key] = input_elements[key].value
                    
                    # Save settings
                    success = save_env_settings(updated_settings)
                    if success:
                        ui.notify('Settings saved successfully!', type='positive')
                    else:
                        ui.notify('Failed to save settings', type='negative')
                
                ui.button('Save Settings', on_click=save_settings).classes('mt-4')
        
            # Logs Tab Content
            with ui.tab_panel(logs_tab):
                ui.label('Bot Logs').classes('text-h5')
                
                # Control panel
                with ui.row().classes(CSS_ROW_FULL):
                    # Status label
                    status_label = ui.label('Status: Stopped').classes(CSS_LABEL_H6 + ' text-negative')
                    ui.space()
                    
                    # Volume slider
                    with ui.column().classes('items-center'):
                        ui.label('TTS Volume').classes(CSS_LABEL_SM)
                        volume_slider = ui.slider(min=0.0, max=1.0, step=0.1, value=float(os.getenv('TTS_VOLUME', '0.8')))
                        
                        async def on_volume_change(e):
                            volume = volume_slider.value
                            if bot_instance and hasattr(bot_instance, 'tts_manager'):
                                bot_instance.tts_manager.volume = volume
                                logger.info(f'TTS volume set to {volume}')
                            set_key(ENV_PATH, 'TTS_VOLUME', str(volume))
                        
                        volume_slider.on('change', on_volume_change)
                    
                    ui.space()
                    
                    # Start/Stop button and handler
                    async def toggle_bot():
                        if not bot_state.is_running():
                            if await run_bot():
                                start_stop_button.text = 'Stop Bot'
                                start_stop_button.props('color=negative')
                                status_label.text = 'Status: Running'
                                status_label.classes(replace=CSS_LABEL_H6 + ' text-positive')
                                ui.notify('Bot started', type='positive')
                        else:
                            if await stop_bot():
                                start_stop_button.text = 'Start Bot'
                                start_stop_button.props('color=primary')
                                status_label.text = 'Status: Stopped'
                                status_label.classes(replace=CSS_LABEL_H6 + ' text-negative')
                                ui.notify('Bot stopped', type='warning')
                    
                    start_stop_button = ui.button('Start Bot', on_click=toggle_bot).props('color=primary')
                    
                    # Clear logs button
                    def clear_logs():
                        log_stream.truncate(0)
                        log_stream.seek(0)
                        log_display.content = ''
                        ui.notify('Logs cleared', type='info')
                    
                    ui.button('Clear Logs', on_click=clear_logs).props('color=warning')
                    
                    # Shutdown server button
                    async def shutdown_server():
                        logger.info("Shutting down server...")
                        
                        # First stop the bot if it's running
                        if bot_state.is_running():
                            logger.info("Stopping bot before shutdown...")
                            await bot_state.stop()
                            ui.notify('Stopping bot and shutting down server...', type='warning')
                        else:
                            ui.notify('Shutting down server...', type='warning')
                        
                        # Give a moment for the bot to clean up
                        await asyncio.sleep(0.5)
                        
                        # Execute JavaScript to close the browser tab
                        ui.run_javascript('setTimeout(() => { window.close(); }, 1000)')
                        
                        # Schedule complete termination after a short delay
                        def exit_app():
                            logger.info("Exiting application completely")
                            import os, signal
                            # Send SIGTERM to our own process
                            os.kill(os.getpid(), signal.SIGTERM)
                        
                        # Schedule server shutdown and then exit
                        ui.timer(1.5, exit_app)
                        app.shutdown()
                    
                    ui.button('Shutdown Server', on_click=shutdown_server).props('color=negative')
                
                # Log display
                log_display = ui.code('').classes('w-full h-96 overflow-auto')
                
                # Auto-refresh toggle
                with ui.row().classes(CSS_ROW_FULL):
                    auto_refresh = ui.switch('Auto-refresh logs', value=True)
                    ui.label('Refresh rate (seconds):')
                    refresh_rate = ui.slider(min=1, max=10, value=2, step=1)
                
                # Function to update logs
                async def update_logs():
                    while True:
                        if auto_refresh.value:
                            log_content = log_stream.getvalue()
                            log_display.content = log_content
                        await asyncio.sleep(refresh_rate.value)
                
                # Start the log update task
                ui.timer(0.1, lambda: asyncio.create_task(update_logs()))

# Main entry point for the UI
def start_ui():
    print("\n==== Starting VTuber AI Bot UI ====\n")
    print("The UI will open in your default browser. If it doesn't open automatically,")
    print("navigate to http://localhost:8080 in your web browser.\n")
    print("Press Ctrl+C in this terminal window to stop the server when you're done.\n")
    ui.run(title="VTuber AI Bot", favicon="🤖", show=True, port=8080)

if __name__ in {"__main__", "__mp_main__"}:
    start_ui()
