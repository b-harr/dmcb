import argparse
import logging
import os
import re
import requests
import sys
import time
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

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

# Global constants
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
}


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
            scraped_df = pd.DataFrame(columns=["Player", "Player Link", "Player Key", "Signed Using", "Drafted"])
            already_scraped_links = set()
            scraped_df.to_csv(output_csv, index=False)

        to_scrape = [link for link in unique_links if link not in already_scraped_links]
        already_scraped = len(already_scraped_links)
        logger.info(f"Resuming scrape — {already_scraped} players already scraped, {len(to_scrape)} remaining.")

        # Restart from the beginning if all or more links have already been scraped
        if already_scraped >= len(unique_links):
            logger.info("All player links have already been scraped. Restarting from the beginning.")
            os.remove(output_csv)
            scraped_df = pd.DataFrame(columns=["Player", "Player Link", "Player Key", "Signed Using", "Drafted"])
            already_scraped_links = set()
            scraped_df.to_csv(output_csv, index=False)
            to_scrape = unique_links
            already_scraped = 0

        with requests.Session() as session:
            session.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})

            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {
                    executor.submit(scrape_player_contracts, link, session): link
                    for link in to_scrape
                }

            player_lookup = (
                active_data
                .set_index("Player Link")[["Player", "Player Key"]]
                .to_dict(orient="index")
            )

            start_time = time.time()

            with requests.Session() as session:
                session.headers.update(HEADERS)

                with ThreadPoolExecutor(max_workers=5) as executor:
                    futures = {
                        executor.submit(scrape_player_contracts, link, session): link
                        for link in to_scrape
                    }

                    for idx, future in enumerate(as_completed(futures), start=1):
                        link = futures[future]
                        player_meta = player_lookup[link]

                        player_name = player_meta["Player"]
                        player_key = player_meta["Player Key"]

                        try:
                            signed_using, drafted = future.result()
                            signed_using = make_title_case(signed_using)
                        except Exception as e:
                            logger.warning(f"Failed to scrape {player_name}: {e}")
                            continue

                        scraped_row = {
                            "Player": player_name,
                            "Player Link": link,
                            "Player Key": player_key,
                            "Signed Using": signed_using,
                            "Drafted": drafted,
                        }

                        pd.DataFrame([scraped_row]).to_csv(
                            output_csv, mode="a", header=False, index=False
                        )

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

        # Dynamically determine the cutoff year from the first entry in salary_data["2025-26"]
        try:
            # Extract the first year from the column headers that look like a year
            year_headers = [col for col in salary_data.columns if re.match(r"^\d{4}-\d{2}$", col)]
            if year_headers:
                first_year = int(year_headers[0][:4])
            else:
                # Fallback: try to extract from the first non-empty value in the column
                first_year = int(str(salary_data["2025-26"].dropna().iloc[0])[:4])
        except Exception as e:
            logger.error(f"Could not determine cutoff year from salary_data['2025-26']: {e}")
            first_year = 2025  # fallback to 2025

        # Load the output CSV into a DataFrame
        df = pd.read_csv(output_csv)

        # Extract year and contract type from 'Signed Using' column using regex
        signed_using_info = df["Signed Using"].fillna("").str.extract(r"^(\d{4})\s*/\s*(RFA|UFA)$", flags=re.IGNORECASE)
        signed_year = signed_using_info[0]
        contract_type = signed_using_info[1]

        # Safely convert signed_year to float for comparison, avoiding ValueError on NaN
        signed_year_num = pd.to_numeric(signed_year, errors="coerce")
        is_year_valid = signed_year_num.notna() & (signed_year_num <= first_year)
        is_contract_type_rfa_ufa = contract_type.str.upper().isin(["RFA", "UFA"])

        # Create a mask for rows to exclude (where both conditions are met)
        exclude_mask = is_year_valid & is_contract_type_rfa_ufa

        # Keep only rows that do not match the exclusion criteria
        filtered_df = df[~exclude_mask].copy()

        # Sort by Player Key before saving
        filtered_df = filtered_df.sort_values(by="Player Key", ignore_index=True)

        # Save the filtered DataFrame back to CSV
        filtered_df.to_csv(output_csv, index=False)
        logger.info(f"Removed players with Signed Using like YYYY / RFA or YYYY / UFA (YYYY ≤ {first_year}) from output CSV.")

    if update_sheets:
        try:
            df = pd.read_csv(output_csv)
            df = df.fillna('')
            sheets_manager = GoogleSheetsManager()
            sheets_manager.clear_range(sheet_name=sheet_name, range_to_clear="A:E")
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
    parser = argparse.ArgumentParser(description="Process Spotrac contracts and classify contract types.")

    # Mutually exclusive group for CSV updating
    csv_group = parser.add_mutually_exclusive_group()
    csv_group.add_argument(
        "--update-csv",
        action="store_true",
        dest="update_csv",
        help="Regenerate CSV file (default)",
    )
    csv_group.add_argument(
        "--no-update-csv",
        action="store_false",
        dest="update_csv",
        help="Do not regenerate CSV, load existing instead",
    )
    parser.set_defaults(update_csv=True)

    # Mutually exclusive group for Sheets updating
    sheets_group = parser.add_mutually_exclusive_group()
    sheets_group.add_argument(
        "--update-sheets",
        action="store_true",
        dest="update_sheets",
        help="Update Google Sheets with results",
    )
    sheets_group.add_argument(
        "--no-update-sheets",
        action="store_false",
        dest="update_sheets",
        help="Do not update Google Sheets (default)",
    )
    parser.set_defaults(update_sheets=False)

    parser.add_argument(
        "--sheet",
        dest="sheet_name",
        type=str,
        default="Contract Types",
        help="Google Sheets tab name to update",
    )

    args = parser.parse_args()

    main(
        update_csv=args.update_csv,
        update_sheets=args.update_sheets,
        sheet_name=args.sheet_name
    )
