import asyncio
import logging
import os
from src.config import Config
from src.vtuber_bot import VTuberBot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main entry point for the VTuber AI Bot."""
    # Check if OpenAI API key is set
    config = Config()
    missing_config = config.validate()
    
    if missing_config:
        logger.error(f"Missing required configuration: {', '.join(missing_config)}")
        print(f"\nERROR: Missing required configuration: {', '.join(missing_config)}")
        print("Please set these values in your .env file.")
        return
    
    print("\n===== VTuber AI Bot =====\n")
    print("Initializing components...")
    
    # Initialize the bot
    bot = VTuberBot()
    await bot.initialize()
    
    # Run the main event loop
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
