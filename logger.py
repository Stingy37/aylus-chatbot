import logging
import os

def initialize_logger():
    # Remove the existing log file to reset it
    if os.path.exists('app.log'):
        os.remove('app.log')

    # Reset logging handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        filename='app.log',
        filemode='w',
        format='%(asctime)s - %(levelname)s - %(message)s',
        force=True
    )