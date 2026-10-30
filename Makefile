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
#   make                    # default: pull stats, positions, contracts
# ============================================================

.DEFAULT_GOAL := default
PYTHON ?= python3

# -------------------------
# Contracts
# -------------------------
# Manage player contract data
pull-contracts:
	python3 scripts/pull_contracts.py

push-contracts:
	python3 scripts/push_contracts.py

update-contracts:
	python3 scripts/pull_contracts.py && python3 scripts/push_contracts.py

# -------------------------
# Contract Types
# -------------------------
# Manage Spotrac contract type data (RFA, UFA, 2-way, etc.)
pull-types:
	python3 scripts/pull_types.py

push-types:
	python3 scripts/push_types.py

update-types:
	python3 scripts/pull_types.py && python3 scripts/push_types.py

# -------------------------
# Stats
# -------------------------
# Manage Basketball-Reference player stats
pull-stats:
	python3 scripts/pull_stats.py

push-stats:
	python3 scripts/push_stats.py

update-stats:
	python3 scripts/pull_stats.py && python3 scripts/push_stats.py

# -------------------------
# Positions
# -------------------------
# Manage Sports.ws position data
pull-positions:
	python3 scripts/pull_positions.py

push-positions:
	python3 scripts/push_positions.py

update-positions:
	python3 scripts/pull_positions.py && python3 scripts/push_positions.py

# -------------------------
# Desktop app
# -------------------------
run-app:
	PYTHONPATH=src:. $(PYTHON) -m dmcb.app

build-gui:
	$(PYTHON) -m PyInstaller --noconfirm --windowed --name DMCB --paths src --paths . src/dmcb/app.py

build-macos-installer: build-gui
	hdiutil create -volname "DMCB Commissioner" -srcfolder dist/DMCB.app -ov -format UDZO dist/DMCB-macos.dmg

build-windows-installer: build-gui
	ISCC packaging/windows.iss

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
# If no target is specified, pull stats, positions, and contracts data by default
default: update-stats pull-positions pull-contracts
