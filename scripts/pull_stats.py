import os
import sys
import logging
import pandas as pd

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from scripts.utils import scrape_bbref_stats, make_player_key

LOG_DIR = os.path.join(".logs")
DATA_DIR = os.path.join("data")
LOG_FILE = "pull_stats.log"
OUTPUT_FILE = "bbref_stats.csv"

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

log_path = os.path.join(LOG_DIR, LOG_FILE)
output_path = os.path.join(DATA_DIR, OUTPUT_FILE)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_path, mode="a", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

NUMERIC_COLUMNS = ["PTS", "TRB", "AST", "STL", "BLK", "TOV", "PF", "G", "MP"]


def get_fantasy_stats(year: int) -> pd.DataFrame:
    df = scrape_bbref_stats(year)
    df = df[df["Player"] != "League Average"].dropna(subset=["Player"])
    df["Player Key"] = df["Player"].apply(make_player_key)
    df = df.sort_values(by=["Player Key", "Team"]).drop_duplicates(subset="Player Key")
    df[NUMERIC_COLUMNS] = df[NUMERIC_COLUMNS].apply(pd.to_numeric, errors="coerce").fillna(0)

    try:
        df["FP"] = (df["PTS"] + df["TRB"] + df["AST"] + df["STL"] + df["BLK"]
                    - df["TOV"] - df["PF"]).astype(int)  # Fantasy Points: PTS/REB/AST/STL/BLK +1, TO/PF/TF -1
        df["FPPG"] = (df["FP"] / df["G"]).round(1)  # Fantasy Points Per Game
        df["FPPM"] = (df["FP"] / df["MP"]).round(2)  # Fantasy Points Per Minute
        df["MPG"] = (df["MP"] / df["G"]).round(1)  # Minutes Per Game
        df["FPR"] = ((df["FP"] ** 2) / (df["G"] * df["MP"])).round(1)  # Fantasy Point Rating = FPPG * FPPM = (FP ** 2) / (G * MP)
        df = df.replace([float('inf'), float('-inf')], 0).fillna(0)
    except Exception as e:
        logging.error(f"Error during metric calculations: {e}")
        return

    try:
        df.to_csv(output_path, index=False, encoding="utf-8")
        logging.info(f"Data saved to CSV: {output_path}")
        return df
    except Exception as e:
        logging.error(f"Error saving to CSV: {e}")
        return

def main():
    df = get_fantasy_stats(2026)


if __name__ == "__main__":
    logging.info(f"Script execution started: {__file__}")
    main()
    logging.info(f"Script execution completed: {__file__}")
