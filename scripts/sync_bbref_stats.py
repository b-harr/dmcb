import logging
import sys
import os

# Dynamically add the project root to PYTHONPATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config import load_config
from utils.data_fetcher import fetch_data, parse_html
from utils.data_processor import add_fantasy_stats
from utils.google_sheets import update_sheet

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

def main():
    logger.info("The script started successfully.")
    
    # Load configuration
    config = load_config()
    
    # Fetch and parse data
    html_content = fetch_data(config["bbref_stats_url"], config["headers"])
    data_frame = parse_html(html_content, config["numeric_columns"])
    
    # Process the data
    processed_data = add_fantasy_stats(data_frame, config["numeric_columns"])
    
    # Save to CSV
    processed_data.to_csv(config["output_csv"], index=False)
    logger.info(f"Data successfully written to the file: {config['output_csv']}")
    
    # Update Google Sheets
    update_sheet(processed_data, config)
    logger.info("Google Sheets updated successfully.")

if __name__ == "__main__":
    main()
