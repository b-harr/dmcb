# dmcb

## Project Summary: NBA Fantasy Basketball Stats Automation
This project is focused on automating the process of fetching, processing, and exporting NBA player statistics from Basketball-Reference for use in a fantasy basketball league hosted on Sports.ws. The processed data includes custom fantasy metrics and is synchronized with a Google Sheets document for easy sharing and analysis.

# bbref_stats_sync

A Python script to scrape player statistics from Basketball-Reference, process the data for fantasy basketball analysis, and sync the results to a Google Sheet.

---

## Features
- Scrapes the latest player statistics from Basketball-Reference.
- Cleans, processes, and calculates advanced metrics (e.g., Fantasy Points, FPPG, FPPM).
- Outputs a CSV file for local storage.
- Automatically updates a Google Sheet with the processed data.

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
python3 scripts/sync_bbref_stats.py
```

---

## Project Structure

```
dmcb/  
├── .env                            # Environment variables (excluded via .gitignore)  
├── .gitignore                      # Git ignore rules  
├── README.md                       # Project documentation  
├── config.py                       # Shared configuration file  
├── data/                           # Directory for storing output data  
│   ├── bbref_stats.csv             # Basketball Reference statistics data  
│   ├── contract_types.csv          # Spotrac contract type data by player  
│   ├── spotrac_contracts.csv       # Spotrac contract data by NBA team  
│   └── sportsws_positions.csv      # Sports.ws default positions  
├── logs/                           # Directory for log files  
│   └── scripts.log                 # Log file for all scripts  
├── requirements.txt                # Python dependencies  
├── scripts/                        # Directory for individual Python scripts  
│   ├── sync_bbref_stats.py         # Syncs Basketball Reference stats to DMCB Google Sheets  
│   ├── get_spotrac_contracts.py    # Scrapes Spotrac contracts to a local CSV  
│   ├── sync_contract_types.py      # Syncs contract types to Sheets  
│   └── sync_sportsws_positions.py  # Syncs Sports.ws player positions to Sheets  
├── utils/                          # Directory for utility modules  
│   ├── __init__.py                 # Makes utils a package  
│   ├── data_fetcher.py             # Fetches data and parses html  
│   ├── data_processor.py           # Processes DMCB fantasy stats  
│   ├── google_sheets.py            # Authenticates and writes to Google Sheets  
│   └── utils.py                    # Shared utility functions to format text  
└── tests/                          # Directory for unit tests  
    ├── __init__.py                 # Makes tests a package  
    └── test_utils.py               # Tests for utility functions  
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
