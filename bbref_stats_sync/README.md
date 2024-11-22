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
cd bbref_stats_sync
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
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
python3 bbref_stats_sync.py
```

---

## Project Structure

```
bbref_stats_sync/
├── bbref_stats_sync.py        # Main script
├── config.py                  # Configuration management
├── utils.py                   # Helper functions
├── data_fetcher.py            # Data scraping logic
├── data_processor.py          # Data processing and calculations
├── google_sheets.py           # Google Sheets API integration
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (not tracked in Git)
├── python/
│   ├── data/                  # Directory for output data files
│   └── logs/                  # Directory for logs
└── tests/                     # Unit tests
```

---

## Metrics Processed
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
