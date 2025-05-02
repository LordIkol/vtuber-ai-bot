"""
Custom logger implementation for VTuber AI Bot.
Provides standard logging plus a dedicated UI_INFO level for UI-specific messages.
"""

import logging
import sys
from io import StringIO

# Define custom log levels
UI_INFO = 25  # Between INFO (20) and WARNING (30)

# Create a string IO for capturing logs for UI display
log_stream = StringIO()

class StringIOHandler(logging.StreamHandler):
    """Custom handler that writes to a StringIO object for UI display."""
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

# Add a UI_INFO method to the Logger class
def ui_info(self, msg, *args, **kwargs):
    """Log a message with UI_INFO level that will appear in the UI."""
    self.log(UI_INFO, msg, *args, **kwargs)

# Add the method to the Logger class
logging.Logger.ui_info = ui_info

# Add the custom level name to the logging module
logging.addLevelName(UI_INFO, 'UI_INFO')

def setup_logging(log_level=logging.INFO, ui_log_level=UI_INFO):
    """
    Set up logging for the VTuber AI Bot.
    
    Args:
        log_level: The minimum log level for console output
        ui_log_level: The minimum log level for UI display
    """
    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatters
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Add handler for console output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    # Add handler for UI display
    ui_handler = StringIOHandler(log_stream)
    ui_handler.setFormatter(formatter)
    ui_handler.setLevel(ui_log_level)  # Only show UI_INFO and above in the UI
    root_logger.addHandler(ui_handler)
    
    return root_logger

def get_logger(name):
    """
    Get a logger instance with the specified name.
    
    Args:
        name: The name of the logger, typically __name__
        
    Returns:
        A logger instance with ui_info method
    """
    return logging.getLogger(name)

def clear_log_stream():
    """Clear the log stream used for UI display."""
    log_stream.truncate(0)
    log_stream.seek(0)

def get_log_stream():
    """Get the log stream used for UI display."""
    return log_stream
