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
#   make                    # show available targets
# ============================================================

.DEFAULT_GOAL := help
PYTHON ?= python3
PYINSTALLER ?= $(PYTHON) -m PyInstaller
HDIUTIL ?= hdiutil
ISCC ?= ISCC

.PHONY: help pull-contracts push-contracts update-contracts
.PHONY: pull-types push-types update-types
.PHONY: pull-stats push-stats update-stats
.PHONY: pull-positions push-positions update-positions
.PHONY: run-app check-pyinstaller check-macos check-windows
.PHONY: build-gui build-macos-installer build-windows-installer
.PHONY: pull-all push-all update-all

.NOTPARALLEL: pull-all push-all update-all build-macos-installer build-windows-installer

# -------------------------
# Contracts
# -------------------------
# Manage player contract data
pull-contracts:
	$(PYTHON) scripts/pull_contracts.py

push-contracts:
	$(PYTHON) scripts/push_contracts.py

update-contracts:
	$(PYTHON) scripts/pull_contracts.py && $(PYTHON) scripts/push_contracts.py

# -------------------------
# Contract Types
# -------------------------
# Manage Spotrac contract type data (RFA, UFA, 2-way, etc.)
pull-types:
	$(PYTHON) scripts/pull_types.py

push-types:
	$(PYTHON) scripts/push_types.py

update-types:
	$(PYTHON) scripts/pull_types.py && $(PYTHON) scripts/push_types.py

# -------------------------
# Stats
# -------------------------
# Manage Basketball-Reference player stats
pull-stats:
	$(PYTHON) scripts/pull_stats.py

push-stats:
	$(PYTHON) scripts/push_stats.py

update-stats:
	$(PYTHON) scripts/pull_stats.py && $(PYTHON) scripts/push_stats.py

# -------------------------
# Positions
# -------------------------
# Manage Sports.ws position data
pull-positions:
	$(PYTHON) scripts/pull_positions.py

push-positions:
	$(PYTHON) scripts/push_positions.py

update-positions:
	$(PYTHON) scripts/pull_positions.py && $(PYTHON) scripts/push_positions.py

# -------------------------
# Desktop app
# -------------------------
run-app:
	PYTHONPATH=src:. $(PYTHON) -m dmcb.app

check-pyinstaller:
	@$(PYINSTALLER) --version >/dev/null 2>&1 || { \
		printf '%s\n' 'PyInstaller is unavailable. Install it with: $(PYTHON) -m pip install -e ".[build]"'; \
		exit 1; \
	}

check-macos:
	@test "$$(uname -s)" = "Darwin" || { \
		printf '%s\n' 'The macOS installer target must be run on macOS.'; \
		exit 1; \
	}
	@command -v "$(HDIUTIL)" >/dev/null 2>&1 || { \
		printf '%s\n' 'hdiutil was not found; it is required to create the macOS disk image.'; \
		exit 1; \
	}

check-windows:
ifeq ($(OS),Windows_NT)
	@command -v "$(ISCC)" >/dev/null 2>&1 || { \
		printf '%s\n' 'Inno Setup ISCC was not found; install Inno Setup or set ISCC to its compiler path.'; \
		exit 1; \
	}
else
	@printf '%s\n' 'The Windows installer target must be run on Windows.'; \
	exit 1
endif

build-gui: check-pyinstaller
	$(PYINSTALLER) --noconfirm "DMCB.spec"

build-macos-installer: check-macos build-gui
	"$(HDIUTIL)" create -volname "DMCB Commissioner" -srcfolder "dist/DMCB.app" -ov -format UDZO "dist/DMCB-macos.dmg"

build-windows-installer: check-windows build-gui
	"$(ISCC)" "packaging/windows.iss"

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
help:
	@printf '%s\n' \
		'DMCB project targets:' \
		'  pull-* / push-* / update-*   Sync an individual dataset' \
		'  pull-all / push-all / update-all' \
		'  run-app                       Launch the desktop app' \
		'  build-gui                     Build the desktop application' \
		'  build-macos-installer         Build the macOS disk image' \
		'  build-windows-installer       Build the Windows installer'
