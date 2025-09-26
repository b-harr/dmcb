# Makefile for DMCB project
# Shortcuts for running scripts in pull (CSV) or push (Sheets) mode

# -------------------------
# Contracts
# -------------------------
pull-contracts:
	python3 scripts/get_contracts.py --update-csv --no-update-sheets

push-contracts:
	python3 scripts/get_contracts.py --no-update-csv --update-sheets

# -------------------------
# Contract Types
# -------------------------
pull-types:
	python3 scripts/get_contract_types.py --update-csv --no-update-sheets

push-types:
	python3 scripts/get_contract_types.py --no-update-csv --update-sheets

# -------------------------
# Stats
# -------------------------
pull-stats:
	python3 scripts/get_stats.py --update-csv --no-update-sheets

push-stats:
	python3 scripts/get_stats.py --no-update-csv --update-sheets

# -------------------------
# Positions
# -------------------------
pull-positions:
	python3 scripts/get_positions.py --update-csv --no-update-sheets

push-positions:
	python3 scripts/get_positions.py --no-update-csv --update-sheets

# -------------------------
# Groups
# -------------------------
pull-all: pull-contracts pull-types pull-stats pull-positions

push-all: push-contracts push-types push-stats push-positions

# -------------------------
# Default
# -------------------------
default: pull-contracts
