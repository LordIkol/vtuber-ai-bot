"""
Main entry point for the VTuber AI Bot UI.
"""

import os
import sys

# Add the project root to the path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Import the UI module
from src.ui.app import ui

# Define the main function to run the UI
def main():
    # Import inside function to avoid circular imports
    from src.ui.app import start_ui
    start_ui()

if __name__ in {"__main__", "__mp_main__"}:
    main()
