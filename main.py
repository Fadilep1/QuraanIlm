import time
from bot import startBot
from bot.utils import runFlask, getLogger, checkVersion

# Configuration: Set these directly in the script
LOCAL = False  # Set to True if running locally
STOP_FLASK = False  # Set to True to disable Flask server

if __name__ == "__main__":
    if not LOCAL and not STOP_FLASK:
        runFlask()

    checkVersion()
    logger = getLogger(__name__)

    # Infinite loop to restart the bot in case of errors
    while True:
        try:
            startBot()
        except KeyboardInterrupt:
            if LOCAL:
                break  # Exit gracefully in local testing
        except Exception as e:
            if LOCAL:
                raise e  # Show full error in local testing
            logger.error(f"Error occurred: {e}")
            time.sleep(5)  # Optional delay before restarting
