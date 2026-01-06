import os
import sys
import logging
import pandas as pd
import time
import re
import argparse
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# -------------------------------------------------
# Paths
# -------------------------------------------------
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

input_csv = os.path.join("data", "spotrac_contracts.csv")
output_csv = os.path.join("data", "contract_types.csv")
os.makedirs("data", exist_ok=True)

# -------------------------------------------------
# Logging
# -------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger()
logger.info("get_contract_types.py started successfully.")

# -------------------------------------------------
# Imports
# -------------------------------------------------
from utils.google_sheets_manager import GoogleSheetsManager
from utils.scrape_spotrac import scrape_player_contracts, HEADERS
from utils.text_formatter import make_title_case


# -------------------------------------------------
# Main
# -------------------------------------------------
def main(update_csv=False, update_sheets=True, sheet_name="Contract Types"):
    logger.info(f"Loading Spotrac source data: {input_csv}")

    try:
        salary_data = pd.read_csv(input_csv)
    except Exception as e:
        logger.error(f"Failed to load {input_csv}: {e}")
        return

    # -------------------------------------------------
    # Active players only
    # -------------------------------------------------
    active_data = salary_data[
        (salary_data["2025-26"] != "Two-Way") &
        (salary_data["2025-26"] != "-")
    ].copy()

    unique_links = (
        active_data
        .drop_duplicates(subset=["Player Link", "Player Key"])
        .sort_values("Player Key")["Player Link"]
        .tolist()
    )

    logger.info(f"Found {len(unique_links)} active players")

    # -------------------------------------------------
    # CSV update logic
    # -------------------------------------------------
    if update_csv:
        if os.path.exists(output_csv):
            existing_df = pd.read_csv(output_csv)
        else:
            existing_df = pd.DataFrame(
                columns=["Player", "Player Link", "Player Key", "Signed Using", "Drafted"]
            )
            existing_df.to_csv(output_csv, index=False)

        existing_links = set(existing_df["Player Link"])
        to_scrape = [link for link in unique_links if link not in existing_links]

        logger.info(
            f"Existing: {len(existing_links)} | "
            f"To scrape: {len(to_scrape)}"
        )

        # -------------------------------------------------
        # Fast lookup dict (thread-safe)
        # -------------------------------------------------
        player_lookup = (
            active_data
            .set_index("Player Link")[["Player", "Player Key"]]
            .to_dict("index")
        )

        # -------------------------------------------------
        # Threaded scraping (BIG WIN)
        # -------------------------------------------------
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
                    meta = player_lookup.get(link)

                    if not meta:
                        continue

                    player_name = meta["Player"]
                    player_key = meta["Player Key"]

                    try:
                        signed_using, drafted = future.result()
                        signed_using = make_title_case(signed_using)
                    except Exception as e:
                        logger.warning(f"Failed to scrape {player_name}: {e}")
                        continue

                    row = {
                        "Player": player_name,
                        "Player Link": link,
                        "Player Key": player_key,
                        "Signed Using": signed_using,
                        "Drafted": drafted,
                    }

                    pd.DataFrame([row]).to_csv(
                        output_csv, mode="a", header=False, index=False
                    )

                    # ETA logging
                    elapsed = time.time() - start_time
                    rate = elapsed / idx
                    remaining = rate * (len(to_scrape) - idx)

                    logger.info(
                        f"Processed {idx}/{len(to_scrape)} "
                        f"- {player_name} | "
                        f"ETA {int(remaining//60):02d}:{int(remaining%60):02d}"
                    )

        # -------------------------------------------------
        # Post-processing / cleanup
        # -------------------------------------------------
        df = pd.read_csv(output_csv)

        # Determine cutoff year
        year_headers = [c for c in salary_data.columns if re.match(r"^\d{4}-\d{2}$", c)]
        first_year = int(year_headers[0][:4]) if year_headers else 2025

        extracted = df["Signed Using"].fillna("").str.extract(
            r"^(\d{4})\s*/\s*(RFA|UFA)$", flags=re.IGNORECASE
        )

        signed_year = pd.to_numeric(extracted[0], errors="coerce")
        contract_type = extracted[1].str.upper()

        exclude_mask = (
            signed_year.notna() &
            (signed_year <= first_year) &
            contract_type.isin(["RFA", "UFA"])
        )

        df = df[~exclude_mask].sort_values("Player Key", ignore_index=True)
        df.to_csv(output_csv, index=False)

        logger.info(
            f"Filtered expired RFA/UFA contracts (≤ {first_year})"
        )

    # -------------------------------------------------
    # Google Sheets update
    # -------------------------------------------------
    if update_sheets:
        try:
            df = pd.read_csv(output_csv).fillna("")
            sheets = GoogleSheetsManager()

            sheets.clear_range(sheet_name=sheet_name, range_to_clear="A:E")

            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            sheets.write_data(
                [[f"Last updated {timestamp} by {sheets.service_account_email}"]],
                sheet_name=sheet_name,
                start_cell="A1",
            )

            sheets.write_data(
                [df.columns.tolist()] + df.values.tolist(),
                sheet_name=sheet_name,
                start_cell="A2",
            )

            logger.info(f"Google Sheets '{sheet_name}' updated successfully")

        except Exception as e:
            logger.error(f"Google Sheets update failed: {e}")


# -------------------------------------------------
# CLI
# -------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Classify Spotrac contract types"
    )

    csv_group = parser.add_mutually_exclusive_group()
    csv_group.add_argument("--update-csv", action="store_true", dest="update_csv")
    csv_group.add_argument("--no-update-csv", action="store_false", dest="update_csv")
    parser.set_defaults(update_csv=True)

    sheets_group = parser.add_mutually_exclusive_group()
    sheets_group.add_argument("--update-sheets", action="store_true", dest="update_sheets")
    sheets_group.add_argument("--no-update-sheets", action="store_false", dest="update_sheets")
    parser.set_defaults(update_sheets=False)

    parser.add_argument(
        "--sheet",
        dest="sheet_name",
        default="Contract Types",
        help="Google Sheets tab name",
    )

    args = parser.parse_args()

    main(
        update_csv=args.update_csv,
        update_sheets=args.update_sheets,
        sheet_name=args.sheet_name,
    )
