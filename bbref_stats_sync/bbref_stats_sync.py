from config import load_config
from data_fetcher import fetch_data_with_retry, parse_html
from data_processor import process_data
from google_sheets import update_google_sheet
import logging
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

def main():
    logger.info("The script started successfully.")
    
    # Load configuration
    config = load_config()
    
    # Fetch and parse data
    html_content = fetch_data_with_retry(config["bbref_url"], config["headers"])
    data_frame = parse_html(html_content, config["numeric_columns"])
    
    # Process the data
    processed_data = process_data(data_frame, config["numeric_columns"])
    
    # Save to CSV
    processed_data.to_csv(config["output_csv"], index=False)
    logger.info(f"Data successfully written to the file: {config['output_csv']}")
    
    # Update Google Sheets
    update_google_sheet(processed_data, config)
    logger.info("Google Sheets updated successfully.")

if __name__ == "__main__":
    main()
