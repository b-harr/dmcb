import os
from dotenv import load_dotenv
import pandas as pd

def load_config(sheet_name="Stats"):
    load_dotenv()
    return {
        "bbref_stats_url": "https://www.basketball-reference.com/leagues/NBA_2025_totals.html",
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        },
        "creds_path": os.getenv("GOOGLE_SHEETS_CREDENTIALS"),
        "google_sheets_url": os.getenv("GOOGLE_SHEETS_URL"),
        "sheet_name": sheet_name,  # Use dynamic sheet name passed as argument
        "numeric_columns": "PTS,TRB,AST,STL,BLK,TOV,PF,G,MP".split(","),
        "output_csv": os.path.join("data", "bbref_stats.csv")
    }
