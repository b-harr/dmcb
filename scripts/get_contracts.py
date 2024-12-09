import os
import sys
import logging

# Set up logging for the script
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Get the root project directory (2 levels up from the current script)
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Append the base_dir to sys.path to ensure modules can be imported
sys.path.append(base_dir)

# Define paths for the output directory and file
output_dir = "data"
output_file = "spotrac_contracts.csv"

# Ensure the output folder exists
os.makedirs(output_dir, exist_ok=True)

# Define the full path for the output CSV file
output_csv = os.path.join(output_dir, output_file)

# Import utility functions and modules
from utils.scrape_spotrac import scrape_all_teams
from utils.text_formatter import make_player_key, make_title_case
from utils.google_sheets_manager import GoogleSheetsManager

def main(update_csv=True, update_sheets=False, sheet_name="Contracts"):
    """
    Main function to scrape Spotrac data, process it, and optionally save it to a CSV file
    and/or update Google Sheets.

    Parameters:
        update_csv (bool): Whether to save the data to a CSV file.
        update_sheets (bool): Whether to update the data in Google Sheets.
        sheet_name (str): The name of the Google Sheets tab to update.
    """
    logging.info("Starting data scrape from Spotrac...")
    
    # Attempt to scrape data
    try:
        df = scrape_all_teams()
        if df is None or df.empty:
            raise ValueError("No data was returned from the scrape.")
    except Exception as e:
        logging.error(f"Data scrape failed: {e}")
        sys.exit(1)
    
    # Process the DataFrame if valid data is returned
    logging.info("Processing scraped data...")
    try:
        # Add derived columns for Player Key and Team Link
        df["Player Key"] = df["Player"].apply(make_player_key)
        df["Team Link"] = df["Team"].apply(lambda team: f"https://www.spotrac.com/nba/{team}/yearly")
        
        # Format the Team column to Title Case
        df["Team"] = df["Team"].apply(make_title_case)
        
        # Sort by Player Key for consistency
        df = df.sort_values(by="Player Key", ignore_index=True)
        
        # Dynamically reorder columns
        required_columns = ["Player", "Player Link", "Player Key", "Team", "Team Link", "Position", "Age"]
        dynamic_columns = [col for col in df.columns if col.startswith("20")]
        column_order = required_columns + dynamic_columns
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        df = df[column_order]
    except Exception as e:
        logging.error(f"Error during data processing: {e}")
        sys.exit(1)
    
    # Save the processed data to a CSV file
    if update_csv:
        try:
            df.to_csv(output_csv, mode="w", index=False, encoding="utf-8")
            logging.info(f"Data successfully saved to {output_csv}")
        except Exception as e:
            logging.error(f"Failed to save data to CSV: {e}")
    
    # Update the Google Sheets document if requested
    if update_sheets:
        logging.info(f"Updating Google Sheets: {sheet_name}")
        try:
            sheets_manager = GoogleSheetsManager()
            sheets_manager.write_data([df.columns.tolist()] + df.values.tolist(), sheet_name=sheet_name, start_cell="A1")
            logging.info("Google Sheets updated successfully.")
        except Exception as e:
            logging.error(f"Failed to update Google Sheets: {e}")


# Main execution block
if __name__ == "__main__":
    logging.info("Starting Spotrac data sync script...")
    main(update_csv=True, update_sheets=False)
    logging.info(f"Script execution completed: {__file__}")
