# DMCB Commissioner Application

## Project context

The repository is a Python data-sync toolkit with shared scraping,
normalization, and Google Sheets helpers in `scripts/utils.py`; separate pull
and push scripts for contracts, contract types, player statistics, and
positions; CSV datasets in `data/`; Makefile workflows; and focused tests.

- Spotrac scraping supports an NBA team slug and currently lists 30 NBA teams.
  Existing contract rows include player identity, NBA team, position, age,
  five season columns, and fantasy Owner.
- The Google Sheets `Owned` tab is the Owner source. The existing code assumes
  Owner is in column A and Player in column D. The `Contracts` tab is the
  comparison and write target. Existing local contract output has `Player`,
  `Player Link`, `Player Key`, `Team`, `Team Link`, `Position`, `Age`, season
  columns, and `Owner`; current season columns are 2026-27 through 2030-31.
- Existing Spotrac detail parsing discovers additional profile/contract
  labels. In 187 cached public player pages, Country, Contract Terms, GTD at
  Sign, Total GTD, and Signed Using appeared on all pages; Age appeared on
  186, College on 177, Average Salary on 151, Exp on 117, Agent(s) on 111,
  Drafted on 95, Free Agent on 69, and Maximum Value on 9.
- Sports.ws positions and Basketball-Reference statistics already have pull
  workflows. The stats workflow currently selects a season in code and adds
  derived fantasy metrics; those metrics are not a verified implementation of
  Sports.ws scoring.
- Existing pull and push commands are separate, though combined Makefile
  targets can write to Google Sheets.

See the root [README](../README.md) for existing setup/workflows and
[docs/README.md](./README.md) for league rules and the 16 fantasy franchises.

## Confirmed decisions

- Select one NBA team, multiple NBA teams, or all 30 current NBA teams.
- Read fantasy Owner from `Owned` using the confirmed existing mapping: column
  A is Owner and column D is Player. Match player identity using `Player Key`.
- Compare with and write to `Contracts`. Update matching rows in place by
  `Player Key`, update contract/data columns A-L, preserve Owner in column M
  and unrelated cells, append new keys only after a preview, and do not delete
  rows absent from a pull.
- Before writes, preview changes, require explicit confirmation, and save a
  timestamped local CSV backup of the affected sheet data.
- Compare numeric contract values as amounts but serialize currency in CSV
  without grouping commas (for example, `$1000000`). Keep source status strings
  distinct from numeric salaries. Missing values are not zero and must be
  reported rather than silently treated as a change.
- Preserve all available Spotrac season values in the source record. Limit the
  final contract dataframe to five season columns, using the five most recent
  available seasons.
- Use a stable Spotrac detail schema: `Player`, `Player Link`, `Player Key`,
  `Signed Using`, `Drafted`, `Country`, `Contract Terms`, `Age`, `College`,
  `Exp`, `Agent(s)`, and `Free Agent`. Fields not present on a player's page
  are blank/null; do not infer them.
- Retrieve default positions from Sports.ws. Show the latest available
  Basketball-Reference season by default, with other published seasons
  selectable. Future seasons' statistics are not available.
- Start with a PySide6 desktop app. Keep business logic independent of the UI
  for a future web interface.
- Target graphical installers for macOS and Windows and a CLI installation
  path for Linux.
- Keep credentials local and out of source control/exports. Do not write to
  Sheets without an explicit user action. Respect source terms, rate limits,
  and access restrictions; do not bypass anti-bot controls.

## Roadmap

1. Implement reusable typed source, reconciliation, Google Sheets, backup,
   and CSV-export services without breaking current script entry points.
2. Add focused tests for team/player selection, source normalization,
   comparisons, owner matching, write plans, backup behavior, and exports.
3. Build the PySide6 desktop workflows for contract retrieval, player details,
   positions/stats, comparison review, CSV export, and confirmed Sheets writes.
4. Add setup/launch documentation and package targets for macOS/Windows GUI
   distribution and Linux CLI installation.
5. Validate focused tests and supported packaging paths; clearly report any
   source access or platform limitations.

## Canonical implementation prompt

```text
Act as a senior software engineer working in my existing dmcb/ repository.
Build a commissioner-facing app for my 16-team fantasy basketball league. It
uses Sports.ws and efficiency scoring, with public NBA contract data from
Spotrac.

Preserve and extend the current Python scripts, CSV workflows, and tests;
do not replace the repository wholesale. Start with a PySide6 desktop app,
keeping UI code separate from reusable data/business services so a web
interface can be added later. Target graphical installers for macOS and
Windows and a CLI installation path for Linux.

Features:

1. Let me select one NBA team, multiple NBA teams, or all 30 current NBA
   teams. Retrieve each selected team's Spotrac contract records. Preserve
   `Player`, `Player Link`, `Player Key`, `Team`, `Team Link`, `Position`,
   `Age`, and every available contract season in the source record; limit the
   final dataframe and its CSV to the five most recent available seasons.
2. Read the fantasy Owner from the Google Sheets `Owned` tab, where column A
   is Owner and column D is Player. Join using normalized `Player Key`;
   identify unmatched, duplicate, or ambiguous records instead of guessing.
3. Compare Spotrac contracts with the `Contracts` tab. Compare numeric salary
   representations by amount, serialize them in CSV without grouping commas
   (e.g. `$1000000`), and treat Spotrac status text separately. Show old/new
   values and season, distinguish changed/missing/unmatched/ambiguous/
   unchanged, and never treat missing as zero.
4. Support explicit writes to `Contracts`: match existing rows by `Player
   Key`, update data columns A-L in place, preserve Owner in M and unrelated
   cells, append new player keys only after showing a preview, and never
   delete rows merely because they were absent from a scrape. Before each
   write, save a timestamped local CSV backup of the affected sheet data,
   show the target and before/after values, and require confirmation. Report
   failures clearly.
5. Retrieve Spotrac detail for one or many players with a stable schema:
   `Player`, `Player Link`, `Player Key`, `Signed Using`, `Drafted`, `Country`,
   `Contract Terms`, `Age`, `College`, `Exp`, `Agent(s)`, `Free Agent`.
   Keep absent source fields blank/null rather than inferring values.
6. Retrieve default player positions from Sports.ws. Retrieve
   Basketball-Reference stats, defaulting to the latest available season and
   allowing selection of other published seasons. Clearly label source fields.
   Do not present generic derived fantasy metrics as Sports.ws scoring.
7. Export selected contracts, player details, positions, statistics, and
   comparison results to CSV with clear source attribution and documented
   schemas.

Keep the service-account JSON file and configuration local, never commit or
export credentials, and report authentication/network/parsing/matching/write
errors explicitly. Respect data-source terms and rate limits; do not bypass
access controls or anti-bot restrictions. Preserve existing CLI behavior.
Add focused tests, update documentation, and validate the smallest relevant
commands. If a data source is inaccessible, fail visibly rather than
substituting stale or fabricated data.
```
