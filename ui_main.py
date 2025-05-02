"""
Main entry point for the VTuber AI Bot UI.
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the project root to the path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Define the main function to run the UI
def main():
    # Import inside function to avoid circular imports
    from src.ui.app import start_ui
    
    print("\n==== Starting VTuber AI Bot UI ====\n")
    print("The UI will open in your default browser. If it doesn't open automatically,")
    print("navigate to http://localhost:8080 in your web browser.\n")
    print("Press Ctrl+C in this terminal window to stop the server when you're done.\n")
    
    # Start the UI
    start_ui()

if __name__ in {"__main__", "__mp_main__"}:
    main()
