import os
import sys
import logging
from dotenv import load_dotenv

# Get the root project directory (2 levels up from the current script)
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Append the base_dir to sys.path to ensure modules can be imported
sys.path.append(base_dir)

# Import custom modules for the script
import config
from utils.csv_handler import CSVHandler
from utils.google_sheets_manager import GoogleSheetsManager
import get_spotrac_contracts

# Configure logging to capture detailed script execution and errors
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger()

# Log the script start with a timestamp to track execution
logger.info("The script started successfully.")

# Load environment variables from the .env file
load_dotenv()
logger.info("Environment variables loaded successfully.")

import requests
import re
import pandas as pd
from bs4 import BeautifulSoup
from lxml import html

# Retrieve necessary configuration values from the config module
google_sheets_url = config.google_sheets_url

def update_spotrac_contracts(update_csv=True, update_sheets=False, sheet_name="Contracts"):
    if update_csv == True:
        data_frame = get_spotrac_contracts.main()
        output_csv = config.spotrac_contracts_path
        CSVHandler.write_csv(output_csv, data_frame)
        return

    if update_sheets == True:
        sheets_manager = GoogleSheetsManager()
        return
    
    else:
        print("Nothing to update.")
        return

if __name__ == "__main__":
    update_spotrac_contracts(update_csv=True, update_sheets=False)
    #get_bbref_stats(update_csv=False, update_sheets=False, sheet_name="Stats")
    #get_sportsws_positions(update_csv=False, update_sheets=False)
    #get_contract_types(update_csv=False, update_sheets=True, sheet_name="Contract Types")

