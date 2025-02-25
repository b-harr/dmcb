import os
import sys

# Dynamically add the project root to PYTHONPATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.text_formatter import format_text

string = "sign and trade"
formatted_string = format_text(string)
print(formatted_string)
