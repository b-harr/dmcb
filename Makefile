# ============================================================
# Makefile for DMCB Project
#
# This Makefile provides shortcuts for running our Python
# scripts in three different modes:
#
#   pull-*   : Update local CSV files only (download / sync data).
#   push-*   : Push existing CSV data to Google Sheets.
#   update-* : Update CSVs AND push them to Google Sheets in one step.
#
# Group commands (pull-all, push-all, update-all) run multiple scripts
# in batch mode.
#
# Usage examples:
#   make pull-contracts     # update contracts.csv only
#   make push-stats         # push stats to Sheets only
#   make update-positions   # update CSV and push to Sheets
#   make pull-all           # refresh all CSVs locally
#   make push-all           # push all CSVs to Sheets
#   make update-all         # refresh and push everything
#   make                    # default: pull-contracts
# ============================================================

# -------------------------
# Contracts
# -------------------------
# Manage player contract data
pull-contracts:
	python3 scripts/get_contracts.py --update-csv --no-update-sheets

push-contracts:
	python3 scripts/get_contracts.py --no-update-csv --update-sheets

update-contracts:
	python3 scripts/get_contracts.py --update-csv --update-sheets

# -------------------------
# Contract Types
# -------------------------
# Manage Spotrac contract type data (RFA, UFA, 2-way, etc.)
pull-types:
	python3 scripts/get_contract_types.py --update-csv --no-update-sheets

push-types:
	python3 scripts/get_contract_types.py --no-update-csv --update-sheets

update-types:
	python3 scripts/get_contract_types.py --update-csv --update-sheets

# -------------------------
# Stats
# -------------------------
# Manage Basketball-Reference player stats
pull-stats:
	python3 scripts/get_stats.py --update-csv --no-update-sheets

push-stats:
	python3 scripts/get_stats.py --no-update-csv --update-sheets

update-stats:
	python3 scripts/get_stats.py --update-csv --update-sheets

# -------------------------
# Positions
# -------------------------
# Manage Sports.ws position data
pull-positions:
	python3 scripts/get_positions.py --update-csv --no-update-sheets

push-positions:
	python3 scripts/get_positions.py --no-update-csv --update-sheets

update-positions:
	python3 scripts/get_positions.py --update-csv --update-sheets

# -------------------------
# Groups
# -------------------------
# Run multiple sync operations at once
pull-all: pull-contracts pull-types pull-stats pull-positions

push-all: push-contracts push-types push-stats push-positions

update-all: update-contracts update-types update-stats update-positions

# -------------------------
# Default
# -------------------------
# If no target is specified, pull contract data by default
default: pull-stats pull-positions pull-contracts
