# dmcb

## Project Summary: NBA Fantasy Basketball Stats Automation
This project is focused on automating the process of fetching, processing, and exporting NBA player statistics from Basketball-Reference for use in a fantasy basketball league hosted on Sports.ws. The processed data includes custom fantasy metrics and is synchronized with a Google Sheets document for easy sharing and analysis.

# sync_bbref_stats

A Python script to scrape player statistics from Basketball-Reference, process the data for fantasy basketball analysis, and sync the results to a Google Sheet.

---

## Features
- Scrapes the latest player statistics from Basketball-Reference.
- Cleans, processes, and calculates advanced metrics (e.g., Fantasy Points, FPPG, FPPM).
- Outputs a CSV file for local storage.
- Automatically updates a Google Sheet with the processed data.

---

# sync_sportsws_positions

A Python script to scrape player positions from Sports.ws and sync the results to a Google Sheet.

---

# get_spotrac_contracts

A Python script to scrape team contracts from Spotrac, process the data, and save the output as a CSV file.

---

# get_contract_types

A Python script to scrape player contract types from Spotrac, process the data, and save the output as a CSV file.

---

## Requirements
- Python 3.8 or higher
- Dependencies (see `requirements.txt`)

---

## Setup Instructions

### 1. Clone the Repository
```bash
git clone <repository-url>
cd dmcb
```

### 2. Install Dependencies
```bash
pip3 install -r requirements.txt
```

### 3. Set Up Environment Variables
Create a `.env` file in the project root with the following keys:
```env
GOOGLE_SHEETS_CREDENTIALS=path/to/credentials.json
```

### 4. Configure Google Sheets API
- Follow [this guide](https://gspread.readthedocs.io/en/latest/oauth2.html) to create a service account and download the credentials JSON file.
- Share the Google Sheet with the service account email from the JSON file.

---

## Usage

Run the script from the command line:
```bash
python3 scripts/get_stats.py
```

---

## Project Structure

```
dmcb/  
├── data/                           # Directory for storing output data  
│   ├── bbref_archive/              # Basketball Reference archived statistics  
│   │   └── NBA_{year}_totals.csv   # Basketball Reference statistics data  
│   ├── bbref_stats.csv             # Basketball Reference statistics data  
│   ├── contract_types.csv          # Spotrac contract type data by player  
│   ├── sportsws_positions.csv      # Sports.ws default positions  
│   └── spotrac_contracts.csv       # Spotrac contract data by NBA team  
├── docs/                           # Directory for storing output data  
│   ├── dmcb_logo.png               # DMCB "Riz" logo  
│   └── league_rules.md             # DMCB league rules  
├── logs/                           # Directory for storing output logs  
│   ├── get_stats_error.log         # Error logs  
│   └── get_stats.log               # Execution logs  
├── notebooks/                      # Directory for storing Google Colab Jupyter notebooks  
│   └── dmcb_colab.ipynb            # Main Colab notebook  
├── scripts/                        # Directory for individual Python scripts  
│   ├── get_contract_types.py       # Scrapes contract types to CSV  
│   ├── get_contracts.py            # Scrapes Spotrac contracts to CSV  
│   ├── get_positions.py            # Syncs Sports.ws player positions to Google Sheets  
│   └── get_stats.py                # Syncs Basketball Reference stats to Google Sheets  
├── secrets/                        # Directory for secrets files (excluded via .gitignore)  
├── utils/                          # Directory for individual Python utilities  
│   ├── __init__.py                 # Makes scripts executable  
│   ├── google_sheets_manager.py    # Manages connections to Google Sheets  
│   ├── scrape_bbref.py             # Scrapes Basketball-Reference.com  
│   ├── scrape_sportsws.py          # Scrapes Sports.ws  
│   ├── scrape_spotrac.py           # Scrapes Spotrac.com NBA contracts  
│   └── text_formatter.py           # Helper functions to process text  
├── .env                            # Environment variables (excluded via .gitignore)  
├── .gitignore                      # Git ignore rules  
├── README.md                       # Project documentation  
└── requirements.txt                # Python dependencies  
```

---

## Metrics Processed
`sync_bbref_stats.py`
- **Fantasy Points (FP)**: Calculated as `PTS + TRB + AST + STL + BLK - TOV - PF`.
- **Fantasy Points Per Game (FPPG)**: Average fantasy points per game (`FP / G`).
- **Fantasy Points Per Minute (FPPM)**: Average fantasy points per minute (`FP / MP`).
- **Minutes Per Game (MPG)**: Average minutes played per game (`MP / G`).
- **Fantasy Point Rating (FPR)**: A combined metric that helps gauge overall fantasy value (`FP² / (G * MP)`) (`FPPG * FPPM`).

---

## Contributing
We welcome contributions to improve this project. Here’s how you can help:

1. **Fork the repository**.
2. **Create a new branch** for your feature or bug fix (`git checkout -b feature-name`).
3. **Commit your changes** (`git commit -am 'Add new feature'`).
4. **Push to the branch** (`git push origin feature-name`).
5. **Create a new pull request** to merge your changes.

Please make sure your code passes all tests and adheres to the project’s coding standards before submitting a pull request.

---

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
