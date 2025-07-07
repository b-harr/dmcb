import os
import sys
import logging
import pandas as pd
import time

# Set up paths
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)
input_csv = os.path.join("data", "spotrac_contracts.csv")
output_csv = os.path.join("data", "contract_types.csv")
os.makedirs("data", exist_ok=True)

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger()
logger.info("The script started successfully.")

# Imports
from utils.google_sheets_manager import GoogleSheetsManager
from utils.scrape_spotrac import scrape_player_contracts
from utils.text_formatter import make_title_case

def main(update_csv=False, update_sheets=True, sheet_name="Contract Types"):
    logger.info(f"Starting script to scrape player data from {input_csv}")

    try:
        salary_data = pd.read_csv(input_csv)
        logger.info(f"Successfully loaded salary data from {input_csv}")
    except Exception as e:
        logger.error(f"Failed to load salary data: {e}")
        exit()

    active_data = salary_data[(salary_data["2025-26"] != "Two-Way") & (salary_data["2025-26"] != "-")]
    unique_links = active_data.drop_duplicates(subset=["Player Link", "Player Key"]).sort_values(by="Player Key")["Player Link"].tolist()
    logger.info(f"Found {len(unique_links)} unique player links to scrape")

    if update_csv:
        # Check for already scraped players
        if os.path.exists(output_csv):
            scraped_df = pd.read_csv(output_csv)
            already_scraped_links = set(scraped_df["Player Link"].tolist())
        else:
            scraped_df = pd.DataFrame(columns=["Player", "Player Link", "Player Key", "Signed Using"])
            already_scraped_links = set()
            scraped_df.to_csv(output_csv, index=False)

        to_scrape = [link for link in unique_links if link not in already_scraped_links]
        already_scraped = len(already_scraped_links)
        logger.info(f"Resuming scrape — {already_scraped} players already scraped, {len(to_scrape)} remaining.")

        start_time = time.time()
        for idx, link in enumerate(to_scrape):
            player_row = active_data[active_data["Player Link"] == link].iloc[0]
            player_key = player_row["Player Key"]
            player_name = player_row["Player"]

            try:
                signed_using = scrape_player_contracts(link)
                signed_using = make_title_case(signed_using)
            except Exception as e:
                logger.warning(f"Failed to scrape {player_name}: {e}")
                continue

            scraped_row = {
                "Player": player_name,
                "Player Link": link,
                "Player Key": player_key,
                "Signed Using": signed_using
            }

            pd.DataFrame([scraped_row]).to_csv(output_csv, mode="a", header=False, index=False, encoding="utf-8")

            # Calculate ETA
            total_done = idx + already_scraped + 1
            percent_complete = total_done / len(unique_links) * 100
            elapsed = time.time() - start_time
            rate = elapsed / (idx + 1)
            remaining_time = rate * (len(to_scrape) - (idx + 1))
            eta_min = int(remaining_time // 60)
            eta_sec = int(remaining_time % 60)

            logger.info(
                f"Processed {idx + 1}/{len(to_scrape)} this session "
                f"({total_done}/{len(unique_links)} total, {percent_complete:.1f}%) "
                f"- {player_name} | ETA: {eta_min:02d}:{eta_sec:02d}"
            )

    if update_sheets:
        try:
            df = pd.read_csv(output_csv).fillna('')
            sheets_manager = GoogleSheetsManager()
            sheets_manager.clear_data(sheet_name=sheet_name)
            logger.info(f"Cleared existing data in Google Sheets '{sheet_name}'.")

            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            sheets_manager.write_data(
                [[f"Last updated {timestamp} by {sheets_manager.service_account_email} from {os.path.basename(__file__)}"]],
                sheet_name=sheet_name,
                start_cell="A1"
            )
            sheets_manager.write_data([df.columns.tolist()] + df.values.tolist(), sheet_name=sheet_name, start_cell="A2")
            logger.info(f"Data successfully written to the '{sheet_name}' sheet.")

        except Exception as e:
            logger.error(f"Error updating Google Sheets: {e}")

if __name__ == "__main__":
    main(update_csv=True, update_sheets=False)
    # main(update_csv=False, update_sheets=True)
