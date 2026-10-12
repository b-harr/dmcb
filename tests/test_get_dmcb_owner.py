import os
import sys

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from scripts.utils import scrape_dmcb_owner


def main():
    sheet = "Owned"
    output = "data/dmcb_owners.csv"
    df = scrape_dmcb_owner(sheet, output)
    column_order = ["Player", "Player Key", "Owner"]
    #df = df[column_order].sort_values("Player Key")
    df.to_csv(output, index=False)


if __name__ == "__main__":
    main()
