import os
import sys

# Dynamically add the project root to PYTHONPATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.csv_handler import read_file, write_file

df = read_file("data", "contract_types.csv")
write_file(df, "tests/data", "types.csv")
