# DMCB Commissioner Application

## Status and scope

This document records the confirmed requirements, a proposed roadmap, and a
refined implementation prompt. It is not approval to begin implementation:
first resolve the remaining questions at the end of the prompt and wait for
the commissioner's go-ahead.

## Existing project context

The repository is a Python data-sync toolkit with shared scraping,
normalization, and Google Sheets helpers in `scripts/utils.py`; separate pull
and push scripts for contracts, contract types, player statistics, and
positions; CSV datasets in `data/`; Makefile workflows; and focused tests.

- Spotrac contract scraping already supports an NBA team slug and currently
  scrapes the repository's set of 30 NBA teams. The helper extracts player
  identity, NBA team, position, age, and up to five season values.
- Google Sheets access uses a local service-account JSON file. Existing
  workflows read the `Owned` and `Contracts` tabs. Owner extraction is
  currently positional rather than based on verified header names, but
  using verified header names would be preferred.
- The current Spotrac player-detail public helper emits the requested stable
  fields: `Player`, `Player Link`, `Player Key`, `Signed Using`, and `Drafted`.
  Its lower-level parser discovers additional fields from the page, but the
  public helper discards those. Used data in .cache/players/ to recommend a
  list of fields contained by a significant number of players to warrant
  inclusion.
- Sports.ws positions and Basketball-Reference statistics already have
  separate pull workflows and CSVs. The existing stats pull chooses its season
  in code and computes additional generic fantasy-point metrics; these should
  not be represented as Sports.ws scoring.
- Pull and push commands are separate, but combined update commands also write
  to Google Sheets.

The existing root [README](../README.md) documents setup and workflows. The
league rules and current 16 fantasy franchises are in [docs/README.md](./README.md).

## Confirmed requirements

- **NBA team scope:** Select one NBA team, multiple NBA teams, or all **30
  current NBA teams**. This selection is NBA teams, not the 16 fantasy
  franchises.
- **Fantasy Owner:** Associate player records with the DMCB fantasy Owner
  found on the Google Sheets `Owned` tab.
- **Spotrac team-contract record:** Preserve a structured record with
  `Player`, `Player Link`, `Player Key`, `Team`, `Team Link`, `Position`,
  `Age`, and every available contract-season value. The final displayed and
  exported dataframe is limited to five contract-season columns. Proposed
  default: retain the five most recent available seasons in the final
  dataframe, while preserving all available years in the underlying record.
- **Spotrac player-detail record:** Use a stable record/dataframe schema of
  exactly `Player`, `Player Link`, `Player Key`, `Signed Using`, and `Drafted`.
  Keep missing source values explicit. Do not silently add arbitrary fields
  to this public schema.
- **Google Sheets:** The app must read from and write to Sheets. Writes must
  be explicit and user-triggered, with the destination and affected data
  reviewed before changes are applied; scraping or comparison alone must not
  overwrite data.
- **Interface:** Start with a desktop application. Keep data and business
  logic separate from the UI so a web interface can be added later without
  replacing the data layer.
- **Sources:** Continue to use public Spotrac contract data, Sports.ws default
  positions, and Basketball-Reference statistics. CSVs must identify the
  source of their fields.
- **Platform:** Support macOS first and cross-platform use where practical.

## Proposed roadmap

1. **Resolve remaining data and UX decisions**
   - Verify `Contracts` as the contract comparison/write tab and determine
     header names, destination ranges, and how to preserve formulas or
     unrelated cells.
   - Agree on player matching, duplicate handling, comparison statuses, write
     confirmation, stats seasons/fields, and desktop distribution.
2. **Define schemas and service boundaries**
   - Formalize structured Spotrac records, the five-season output projection,
     the player-detail schema, source attribution, and CSV serialization.
   - Separate source clients, Google Sheets read/write operations, comparison
     logic, and UI so a future web UI can reuse the same services.
3. **Implement and test data workflows**
   - Add selectable NBA team and single/batch player retrieval.
   - Join `Owned` data to Spotrac records using normalized player identity;
     report unmatched or ambiguous matches instead of guessing.
   - Compare agreed contract seasons and distinguish changed, missing,
     unmatched, and unchanged values.
   - Add guarded, explicit Google Sheets writes and focused tests for failures,
     duplicates, matching, normalization, and export schemas.
4. **Build the desktop experience**
   - Provide source configuration/status, team and player selection,
     progress and actionable errors, discrepancy review, CSV export, and a
     preview/confirmation step before Sheets writes.
   - Use a modular UI/data architecture that allows a future web UI.
5. **Validate and document**
   - Run focused tests and relevant project checks.
   - Document installation/launch, credentials, permissions, source
     limitations, CSV schemas, and supported platforms.

## Refined implementation prompt

```text
Act as a senior software engineer working in my existing dmcb/ repository.
Build a commissioner-facing application for my 16-team fantasy basketball
league. The league runs on Sports.ws and uses efficiency rather than points or
categories. NBA contract data comes from public Spotrac data.

Do not implement anything yet. First inspect the repository and summarize its
architecture, reusable source integrations, current Google Sheets workflows,
CSV schemas, tests, and relevant constraints. Then ask me the unresolved
questions listed below and wait for my answers and explicit approval before
editing application code, changing dependencies, or installing packages.

Preserve and extend the existing Python scripts and workflows where practical.
Do not replace the project wholesale. Start with a desktop app for macOS, but
keep source integrations and business logic independent of the UI so a web
app can be added later. Recommend a cross-platform desktop approach and
explain packaging tradeoffs before choosing implementation details.

Requirements:

1. NBA team contract retrieval
   - Let me select one NBA team, multiple NBA teams, or all 30 current NBA
     teams. Do not confuse these with the league's 16 fantasy franchises.
   - Retrieve each selected team's Spotrac player contract data.
   - Represent each player/team contract record with these fields:
     `Player`, `Player Link`, `Player Key`, `Team`, `Team Link`, `Position`,
     `Age`, and every available contract-season value.
   - Preserve all available contract years in the structured source record.
     Limit the final displayed/exported dataframe to five season columns, using
     the five most recent available seasons unless I direct otherwise.
   - Export selected results to CSV.

2. Fantasy Owner association
   - Connect to Google Sheets using a local service-account JSON credentials
     file and the configured workbook.
   - Read the fantasy Owner from the `Owned` tab and associate it with the
     appropriate player records.
   - Use stable player identity keys where possible. Flag unmatched or
     ambiguous matches; never silently assign the wrong owner.
   - Never expose or export credentials.

3. Contract comparison and Sheets updates
   - Compare newly retrieved Spotrac values with the existing contract values
     in Google Sheets. Use the existing `Contracts` tab as the proposed
     baseline, but verify the tab, columns, and write behavior with me before
     implementation.
   - Show old and new values and the affected season(s). Clearly distinguish
     changed, missing, unmatched, ambiguous, and unchanged records. Do not
     silently treat a missing value as zero or as a confirmed contract change.
   - Support writing data to Google Sheets only through a deliberate
     user-triggered action. Before writing, show the target tab/range and a
     preview of affected values, require confirmation, and report success or
     failure. A scrape, comparison, or CSV export must not write to Sheets.
   - Export discrepancies to CSV, including player identity, Owner when
     matched, NBA team, season, old value, new value, status, and source.

4. Spotrac player details
   - Retrieve one player's details or a batch of players.
   - Use this stable schema: `Player`, `Player Link`, `Player Key`,
     `Signed Using`, and `Drafted`.
   - Keep `Signed Using` and `Drafted` as source values in a structured
     dictionary/record with those exact keys; define how missing values are
     represented. The existing parser internally sees other labels but the
     public helper currently emits these five fields. Do not silently expand
     the exported schema. Determine from current code and representative
     records whether we should add any explicitly selected fields later.
   - Export player details to CSV with clearly specified null/serialization
     behavior.

5. Positions and statistics
   - Retrieve default player positions from Sports.ws.
   - Retrieve player statistics from Basketball-Reference. Make season
     selection, available fields, and source clear in the UI and export.
   - Keep generic derived fantasy metrics distinct from Sports.ws scoring;
     do not claim they reproduce Sports.ws efficiency scoring unless that is
     verified and requested.

6. Reliability, security, and compatibility
   - Keep credentials and local configuration out of source control and CSV
     outputs.
   - Report authentication, source, parsing, matching, and write failures
     explicitly. Never silently substitute fabricated or stale data.
   - Respect source terms, rate limits, and access restrictions. Do not bypass
     anti-bot controls.
   - Preserve existing CLI commands and CSV workflows unless an intentional
     change is approved. Add focused tests and update directly relevant
     documentation.

Before implementation, clarify:
1. Is the existing `Contracts` tab the authoritative source for comparison
   values and the intended write destination? What exact headers/columns and
   season fields should be used? The `Owned` tab supplies Owner; please confirm
   how its player and owner columns are labeled if that is not self-evident
   from the workbook.
2. Should comparison use the five most recent seasons by default? Should
   numeric currency values be normalized (for example, `$1,000,000` and
   `1000000` treated as equal)? How should Spotrac's status strings, blanks,
   missing seasons, traded players, and duplicate names be classified?
3. For Sheets writes, which tab/ranges should be writable, should writes
   update existing rows or replace a managed table, and should there be a
   backup/undo mechanism? Always preview changes and require explicit
   confirmation.
4. For Basketball-Reference, which season(s) should be available/selected and
   which fields should be included? Should existing derived columns be
   retained, omitted, or separately selected?
5. The stable Spotrac player-detail schema is the five fields above. After
   inspecting the existing parser and representative records, do you want to
   keep exactly those fields or add any named source fields?
6. For the desktop app, is running Python acceptable, or do you require a
   packaged installer/double-clickable app? Which operating systems beyond
   macOS should be supported?

Use reasonable defaults for minor details, but do not assume answers to these
material questions. After I answer and approve implementation, proceed in
small testable steps: reuse project patterns, add/update focused tests, run
the smallest relevant validation, and report changes, launch instructions,
and limitations.
```

## Remaining decisions before implementation

1. Confirm `Contracts` tab as comparison/write target, its columns, and the
   `Owned` tab's player/Owner headers.
2. Confirm comparison normalization/status behavior and whether five most
   recent years is the correct default.
3. Define write destinations, update semantics, and whether backup/undo is
   needed.
4. Specify Basketball-Reference seasons, fields, and derived metric behavior.
5. Confirm whether the five-field player-detail schema is final or identify
   additional named fields after reviewing representative source records.
6. Confirm packaging requirements and cross-platform targets.
