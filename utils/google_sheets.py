import os
from dotenv import load_dotenv
import gspread
import logging

# Set up module-level logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Load environment variables
load_dotenv()

# Constants from .env
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
GOOGLE_SHEETS_URL = os.getenv("GOOGLE_SHEETS_URL")
SHEET_NAME = os.getenv("SHEET_NAME", "Sheet1")  # Default to "Sheet1" if not provided

class GoogleSheetsManager:
    def __init__(self):
        try:
            logger.info("Initializing GoogleSheetsManager...")
            self.gc = gspread.service_account(filename=GOOGLE_SHEETS_CREDENTIALS)
            self.sheet = self.gc.open_by_url(GOOGLE_SHEETS_URL)
            logger.info("Successfully connected to Google Sheets.")
        except Exception as e:
            logger.error(f"Failed to initialize GoogleSheetsManager: {e}")
            raise

    def get_worksheet(self, sheet_name=None):
        """
        Retrieve a worksheet by name. Defaults to SHEET_NAME from .env.
        """
        try:
            sheet_name = sheet_name or SHEET_NAME
            worksheet = self.sheet.worksheet(sheet_name)
            logger.info(f"Accessed worksheet: {sheet_name}")
            return worksheet
        except Exception as e:
            logger.error(f"Error accessing worksheet '{sheet_name}': {e}")
            raise

    def read_data(self, sheet_name=None):
        """
        Read all data from a worksheet.
        """
        try:
            worksheet = self.get_worksheet(sheet_name)
            data = worksheet.get_all_values()
            logger.info(f"Read {len(data)} rows from worksheet '{sheet_name or SHEET_NAME}'.")
            return data
        except Exception as e:
            logger.error(f"Error reading data from worksheet '{sheet_name or SHEET_NAME}': {e}")
            raise

    def write_data(self, data, sheet_name=None, start_cell="A1"):
        """
        Write a 2D array of data to the worksheet starting from start_cell.
        """
        try:
            worksheet = self.get_worksheet(sheet_name)
            worksheet.update(start_cell, data)
            logger.info(f"Written data to worksheet '{sheet_name or SHEET_NAME}' starting at '{start_cell}'.")
        except Exception as e:
            logger.error(f"Error writing data to worksheet '{sheet_name or SHEET_NAME}': {e}")
            raise

    def clear_data(self, sheet_name=None):
        """
        Clear all data from the worksheet.
        """
        try:
            worksheet = self.get_worksheet(sheet_name)
            worksheet.clear()
            logger.info(f"Cleared data from worksheet '{sheet_name or SHEET_NAME}'.")
        except Exception as e:
            logger.error(f"Error clearing data in worksheet '{sheet_name or SHEET_NAME}': {e}")
            raise


# Example usage
#if __name__ == "__main__":
#    sheets_manager = GoogleSheetsManager()
#    print("Reading data from the sheet...")
#    data = sheets_manager.read_data(sheet_name="Stats")
#    print(data)
#    sheets_manager.write_data([["Test"]], sheet_name="Stats", start_cell="A1")
