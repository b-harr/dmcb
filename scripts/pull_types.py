import os
import sys
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from scripts.utils import make_title_case, scrape_players

DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_DIR = os.path.join(BASE_DIR, ".logs")
INPUT_PATH = os.path.join(DATA_DIR, "spotrac_contracts.csv")
OUTPUT_PATH = os.path.join(DATA_DIR, "contract_types.csv")
OUTPUT_COLUMNS = ["Player", "Player Link", "Player Key", "Signed Using", "Drafted"]
MAX_WORKERS = 5
MAX_RETRIES = 3
RETRY_DELAY = 2

os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    force=True,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "pull_types.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)


class ForbiddenScrapeError(RuntimeError):
    pass


def _has_signed_using(value: object) -> bool:
    if pd.isna(value):
        return False
    return str(value).strip().casefold() not in {"", "na", "n/a", "none", "nan"}


def get_player_urls_to_scrape(
    contracts: pd.DataFrame, contract_types: pd.DataFrame
) -> list[str]:
    if "Player Link" not in contracts.columns:
        raise ValueError("Spotrac contracts data must contain a 'Player Link' column")

    season_columns = [
        column
        for column in contracts.columns
        if re.fullmatch(r"\d{4}-\d{2}", str(column))
    ]
    if season_columns:
        first_values = contracts[season_columns[0]].astype("string").str.strip().str.casefold()
        contracts = contracts.loc[~first_values.eq("two-way").fillna(False)]

    source_links = (
        contracts["Player Link"].dropna().astype(str).str.strip().drop_duplicates().tolist()
    )
    source_links = [link for link in source_links if link]

    if contract_types.empty or "Player Link" not in contract_types.columns:
        return source_links

    if "Signed Using" not in contract_types.columns:
        return source_links

    complete_rows = contract_types.loc[
        contract_types["Signed Using"].map(_has_signed_using), "Player Link"
    ]
    complete_links = set(complete_rows.dropna().astype(str).str.strip())
    return [link for link in source_links if link not in complete_links]


def _scrape_player_with_retries(player_url: str) -> pd.Series:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = scrape_players([player_url])
            if result.empty:
                raise RuntimeError("scraper returned no player details")

            details = result.iloc[0].copy()
            if not _has_signed_using(details.get("Signed Using")):
                details["Signed Using"] = "NA"
                logging.info(
                    "%s has no Signed Using value on its Spotrac page; recording 'NA'",
                    player_url,
                )
            return details
        except Exception as error:
            if "403 client error: forbidden for url" in str(error).casefold():
                raise ForbiddenScrapeError(str(error)) from error
            if attempt == MAX_RETRIES:
                raise RuntimeError(
                    f"Failed to scrape after {MAX_RETRIES} attempts: {error}"
                ) from error

            delay = RETRY_DELAY * attempt
            logging.warning(
                "%s scrape attempt %s/%s failed: %s; retrying in %ss",
                player_url,
                attempt,
                MAX_RETRIES,
                error,
                delay,
            )
            time.sleep(delay)

    raise RuntimeError(f"Failed to scrape {player_url}")


def _save_contract_types(contract_types: pd.DataFrame) -> None:
    temporary_path = f"{OUTPUT_PATH}.tmp"
    contract_types = contract_types.reindex(columns=OUTPUT_COLUMNS).sort_values(
        "Player Key", kind="stable", na_position="last"
    )
    contract_types["Signed Using"] = contract_types["Signed Using"].map(
        lambda value: make_title_case(value) if isinstance(value, str) else value
    )
    contract_types.to_csv(temporary_path, index=False)
    os.replace(temporary_path, OUTPUT_PATH)


def _upsert_contract_details(
    contract_types: pd.DataFrame,
    source_player: pd.Series,
    details: pd.Series,
) -> pd.DataFrame:
    player_url = str(source_player.name).strip()
    row = {
        "Player": source_player.get("Player", details.get("Player", "")),
        "Player Link": player_url,
        "Player Key": source_player.get("Player Key", details.get("Player Key", "")),
        "Signed Using": details.get("Signed Using", ""),
        "Drafted": details.get("Drafted", ""),
    }

    matching_rows = contract_types["Player Link"].astype("string").str.strip().eq(player_url)
    if matching_rows.any():
        contract_types.loc[matching_rows, OUTPUT_COLUMNS] = [row[column] for column in OUTPUT_COLUMNS]
    else:
        contract_types = pd.concat(
            [contract_types, pd.DataFrame([row], columns=OUTPUT_COLUMNS)],
            ignore_index=True,
        )
    return contract_types


def main() -> pd.DataFrame:
    logging.info("Loading Spotrac contracts from %s", INPUT_PATH)
    contracts = pd.read_csv(INPUT_PATH)
    if contracts.empty:
        raise ValueError(f"Spotrac contracts data is empty: {INPUT_PATH}")
    if not {"Player", "Player Link", "Player Key"}.issubset(contracts.columns):
        raise ValueError("Spotrac contracts data is missing required player columns")
    contracts["Player Link"] = contracts["Player Link"].astype("string").str.strip()

    if os.path.exists(OUTPUT_PATH):
        contract_types = pd.read_csv(OUTPUT_PATH)
    else:
        contract_types = pd.DataFrame(columns=OUTPUT_COLUMNS)

    for column in OUTPUT_COLUMNS:
        if column not in contract_types.columns:
            contract_types[column] = pd.NA
    contract_types = contract_types.reindex(columns=OUTPUT_COLUMNS)
    contract_types["_signed_using_present"] = contract_types["Signed Using"].map(
        _has_signed_using
    )
    contract_types = (
        contract_types.sort_values("_signed_using_present", kind="stable")
        .drop_duplicates("Player Link", keep="last")
        .drop(columns="_signed_using_present")
        .reset_index(drop=True)
    )

    urls_to_scrape = get_player_urls_to_scrape(contracts, contract_types)
    logging.info("Found %s players missing a Signed Using value", len(urls_to_scrape))
    _save_contract_types(contract_types)
    if not urls_to_scrape:
        return contract_types.sort_values("Player Key", kind="stable", na_position="last").reset_index(drop=True)

    source_players = (
        contracts.dropna(subset=["Player Link"])
        .drop_duplicates("Player Link", keep="first")
        .set_index("Player Link")
    )
    started_at = time.time()
    failures = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(_scrape_player_with_retries, url): url
            for url in urls_to_scrape
        }

        for completed_count, future in enumerate(as_completed(futures), start=1):
            player_url = futures[future]
            try:
                details = future.result()
                source_player = source_players.loc[player_url]
                contract_types = _upsert_contract_details(
                    contract_types, source_player, details
                )
                _save_contract_types(contract_types)
                logging.info(
                    "Saved %s/%s: %s",
                    completed_count,
                    len(urls_to_scrape),
                    source_player["Player"],
                )
            except ForbiddenScrapeError as error:
                for pending_future in futures:
                    if pending_future is not future:
                        pending_future.cancel()
                logging.critical("Stopping after a forbidden response: %s", error)
                raise
            except Exception as error:
                failures.append(f"{player_url}: {error}")
                logging.error("Failed %s: %s", player_url, error)

    elapsed = time.time() - started_at
    logging.info(
        "Finished in %.1fs: %s succeeded, %s failed",
        elapsed,
        len(urls_to_scrape) - len(failures),
        len(failures),
    )
    if failures:
        message = "Unfinished player scrapes: " + "; ".join(failures)
        logging.error(message)
        raise RuntimeError(message)

    return contract_types.sort_values("Player Key", kind="stable", na_position="last").reset_index(drop=True)


if __name__ == "__main__":
    main()
