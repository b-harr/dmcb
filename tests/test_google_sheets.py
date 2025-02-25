import os
import sys

# Dynamically add the project root to PYTHONPATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.google_sheets import update_sheet
from utils.file_handler import read_file


df = read_file("data", "contract_types.csv")
print(df)
sheet_name = "Sheet62"

update_sheet(df, "Sheet62")
print(df)
