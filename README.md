# DMCB Data Sync

Python scripts for collecting NBA player, contract, and position data and syncing CSV datasets with the DMCB Google Sheets workbook. Scraping and publishing are separate steps: `pull-*` commands update local CSV files, `push-*` commands publish those files, and `update-*` commands run both in sequence.

## Data Workflows

| Dataset | Pull command | Local output | Push command | Google Sheets tab |
| --- | --- | --- | --- | --- |
| Team contracts | `make pull-contracts` | `data/spotrac_contracts.csv`, `data/owned_contracts.csv`, `data/dmcb_owners.csv` | `make push-contracts` | `Contracts` |
| Contract types | `make pull-types` | `data/contract_types.csv` | `make push-types` | `Contract Types` |
| Player stats | `make pull-stats` | `data/bbref_stats.csv` | `make push-stats` | `Stats` |
| Player positions | `make pull-positions` | `data/sportsws_positions.csv` | `make push-positions` | `Positions` |

The contract workflow reads the `Owned` and `Contracts` tabs while pulling, to refresh and merge owner information. The stats pull currently requests the 2026 Basketball-Reference totals. Its derived columns include `FP`, `FPPG`, `FPPM`, `MPG`, and `FPR`.

## Commissioner Application

Requirements and a proposed implementation roadmap for a commissioner-facing
application are documented in [docs/application-requirements.md](docs/application-requirements.md),
including the refined implementation prompt, confirmed requirements, roadmap,
and remaining decisions. No application implementation is implied by that
document.

## Setup

Use Python 3.11 or newer and install the dependencies in a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

For Google Sheets access, create a service account, download its JSON key, and share the workbook with the service account email. Store the key outside the repository, then create a root-level `.env` file:

```env
GOOGLE_SHEETS_CREDENTIALS=/absolute/path/to/service-account.json
GOOGLE_SHEETS_URL=https://docs.google.com/spreadsheets/d/your-spreadsheet-id/edit
```

The workbook must contain the `Contracts`, `Owned`, `Contract Types`, `Stats`, and `Positions` tabs used by the scripts. `pull-contracts` needs access to both `Owned` and `Contracts`; push commands need access to their destination tab.

## Commands

Run one dataset workflow:

```bash
make update-contracts
make update-types
make update-stats
make update-positions
```

Run all pull steps, all push steps, or all pull-and-push workflows:

```bash
make pull-all
make push-all
make update-all
```

The default `make` target runs `update-stats`, `pull-positions`, and `pull-contracts`; it does not run the contract-type workflow. Individual scripts can also be run with `python scripts/pull_types.py` or `python scripts/push_types.py`.

Logs are written under `.logs/`. Scraped datasets and archived source snapshots are stored under `data/`.

## Repository Layout

```text
dmcb/
├── data/
│   ├── archive/
│   ├── bbref_stats.csv
│   ├── contract_types.csv
│   ├── dmcb_owners.csv
│   ├── owned_contracts.csv
│   ├── sportsws_positions.csv
│   └── spotrac_contracts.csv
├── scripts/
│   ├── pull_contracts.py       Scrape contracts and merge owner data
│   ├── pull_positions.py       Scrape and merge player positions
│   ├── pull_stats.py           Scrape player stats and calculate fantasy metrics
│   ├── pull_types.py           Scrape contract types
│   ├── push_contracts.py       Publish contracts
│   ├── push_positions.py       Publish positions
│   ├── push_stats.py           Publish stats
│   ├── push_types.py           Publish contract types
│   └── utils.py                Shared scraping, formatting, and Sheets utilities
├── tests/                      Focused tests for scraping and data helpers
├── Makefile                    Pull, push, and update workflows
└── requirements.txt            Python dependencies
```

Local configuration and generated directories such as `.env`, `.venv/`, `.cache/`, and `.logs/` are not shown. Keep Google service-account credentials local and out of version control.
