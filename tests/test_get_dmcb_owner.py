import os
import sys

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from scripts.utils import scrape_owners


def main():
    sheet = "Owned"
    output = os.path.join("data", "dmcb_owners.csv")
    df = scrape_owners(sheet, output)
    column_order = ["Player", "Player Key", "Owner"]
    df = df[column_order].sort_values("Player Key")
    df.to_csv(output, index=False)


if __name__ == "__main__":
    main()
