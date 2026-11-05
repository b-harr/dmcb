import os
import sys

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from dmcb.services.google_sheets import GoogleSheetsService


def main():
    output = os.path.join("data", "dmcb_owners.csv")
    df = GoogleSheetsService().read_owners()
    column_order = ["Player", "Player Key", "Owner"]
    df = df[column_order].sort_values("Player Key")
    df.to_csv(output, index=False)


if __name__ == "__main__":
    main()
