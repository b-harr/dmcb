import os
from dotenv import load_dotenv
import gspread
import logging
import json

# Set up module-level logging to track the operations of the Google Sheets manager
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Load environment variables from the .env file
load_dotenv()

# Constants loaded from the .env file, which include Google Sheets credentials and the target sheet URL
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
GOOGLE_SHEETS_URL = os.getenv("GOOGLE_SHEETS_URL")

class GoogleSheetsManager:
    """
    A class to manage interactions with Google Sheets, including reading, writing, and clearing data.
    
    It uses the gspread library to interact with Google Sheets via the Google Sheets API.
    """

    def __init__(self):
        """
        Initializes the GoogleSheetsManager by authenticating with Google Sheets API using a service account.
        
        - Loads the credentials and sheet URL from environment variables.
        - Logs the initialization process.
        - Connects to the Google Sheets document specified by the URL.
        """
        try:
            logger.info("Initializing GoogleSheetsManager...")
            # Authenticate using the service account JSON credentials
            self.gc = gspread.service_account(filename=GOOGLE_SHEETS_CREDENTIALS)
            # Open the Google Sheets document by URL
            self.sheet = self.gc.open_by_url(GOOGLE_SHEETS_URL)

            # Load the credentials JSON to extract the service account email
            with open(GOOGLE_SHEETS_CREDENTIALS, 'r') as f:
                credentials = json.load(f)
                self.service_account_email = credentials.get("client_email")
                
            logger.info(f"Successfully connected to Google Sheets. Service Account Email: {self.service_account_email}")
        except Exception as e:
            # Log an error if authentication or connection fails
            logger.error(f"Failed to initialize GoogleSheetsManager: {e}")
            raise


    def get_worksheet(self, sheet_name=None):
        """
        Retrieves a specific worksheet from the Google Sheets document.
        
        Args:
            sheet_name (str, optional): The name of the worksheet to access. Defaults to the value in SHEET_NAME or 'Sheet1'.
        
        Returns:
            gspread.models.Worksheet: The worksheet object corresponding to the provided sheet name.
        
        Raises:
            Exception: If the worksheet cannot be accessed.
        """
        try:
            # Use the provided sheet name or default to SHEET_NAME
            sheet_name = sheet_name
            worksheet = self.sheet.worksheet(sheet_name)
            logger.info(f"Accessed worksheet: {sheet_name}")
            return worksheet
        except Exception as e:
            # Log an error if accessing the worksheet fails
            logger.error(f"Error accessing worksheet '{sheet_name}': {e}")
            raise

    def read_data(self, sheet_name=None):
        """
        Reads all data from a specified worksheet.
        
        Args:
            sheet_name (str, optional): The name of the worksheet from which to read data. Defaults to 'Sheet1'.
        
        Returns:
            list: A 2D list of all data in the worksheet.
        
        Raises:
            Exception: If reading data from the worksheet fails.
        """
        try:
            # Get the worksheet object
            worksheet = self.get_worksheet(sheet_name)
            # Retrieve all values from the worksheet
            data = worksheet.get_all_values()
            logger.info(f"Read {len(data)} rows from worksheet '{sheet_name}'.")
            return data
        except Exception as e:
            # Log an error if reading data fails
            logger.error(f"Error reading data from worksheet '{sheet_name}': {e}")
            raise

    def write_data(self, data, sheet_name=None, start_cell="A1"):
        """
        Writes data to the worksheet starting from a specified cell.
        
        Args:
            data (list of lists): The 2D data array to write to the sheet.
            sheet_name (str, optional): The worksheet name to write data to. Defaults to 'Sheet1'.
            start_cell (str, optional): The cell to start writing from. Defaults to "A1".
        
        Raises:
            Exception: If writing data to the worksheet fails.
        """
        try:
            # Get the worksheet object
            worksheet = self.get_worksheet(sheet_name)
            # Update the sheet with the data starting from the specified cell
            worksheet.update(start_cell, data)
            logger.info(f"Written data to worksheet '{sheet_name}' starting at '{start_cell}'.")
        except Exception as e:
            # Log an error if writing data fails
            logger.error(f"Error writing data to worksheet '{sheet_name}': {e}")
            raise

    def clear_data(self, sheet_name=None):
        """
        Clears all data from a specified worksheet.
        
        Args:
            sheet_name (str, optional): The worksheet name to clear data from. Defaults to 'Sheet1'.
        
        Raises:
            Exception: If clearing the data from the worksheet fails.
        """
        try:
            # Get the worksheet object
            worksheet = self.get_worksheet(sheet_name)
            # Clear all contents of the worksheet
            worksheet.clear()
            logger.info(f"Cleared data from worksheet '{sheet_name}'.")
        except Exception as e:
            # Log an error if clearing data fails
            logger.error(f"Error clearing data in worksheet '{sheet_name}': {e}")
            raise

# Example usage (for testing or manual execution)
if __name__ == "__main__":
    # Initialize the GoogleSheetsManager instance
    sheets_manager = GoogleSheetsManager()

    # Example: Read data from the "Stats" worksheet
    print("Reading data from the sheet...")
    data = sheets_manager.read_data(sheet_name="Stats")
    print(data)
