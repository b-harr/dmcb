from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
import re
from typing import Any

import pandas as pd

from dmcb.models.records import CellUpdate, SheetWritePlan
from scripts.utils import make_player_key

SEASON_PATTERN = re.compile(r"^20\d{2}-\d{2}$")
COMPARISON_COLUMNS = [
    "Player",
    "Player Key",
    "Owner",
    "Team",
    "Season",
    "Existing Value",
    "Spotrac Value",
    "Status",
    "Owner Match",
    "Owner Source",
    "Existing Source",
    "Spotrac Source",
]


def _clean(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def normalized_contract_value(value: Any) -> tuple[str, str]:
    text = _clean(value)
    if not text or text.casefold() in {"na", "n/a", "none", "null", "nan", "-", "—"}:
        return ("missing", "")

    compact = text.replace("$", "").replace(",", "").replace(" ", "")
    try:
        amount = Decimal(compact)
    except InvalidOperation:
        return ("status", text.casefold())
    return ("amount", format(amount.normalize(), "f"))


def format_contract_value(value: Any) -> str:
    text = _clean(value)
    if not text:
        return ""
    kind, normalized = normalized_contract_value(text)
    if kind == "amount":
        return f"${normalized}"
    return text


def owner_index(owners: pd.DataFrame) -> tuple[dict[str, str], set[str]]:
    if owners.empty or "Player Key" not in owners or "Owner" not in owners:
        return {}, set()

    values: dict[str, set[str]] = defaultdict(set)
    for row in owners.to_dict("records"):
        key = _clean(row.get("Player Key"))
        owner = _clean(row.get("Owner"))
        if key and owner:
            values[key].add(owner)

    ambiguous = {key for key, names in values.items() if len(names) > 1}
    return {key: next(iter(names)) for key, names in values.items() if len(names) == 1}, ambiguous


def _to_records_by_key(frame: pd.DataFrame) -> tuple[dict[str, dict[str, Any]], set[str]]:
    if frame.empty:
        return {}, set()
    if "Player Key" not in frame:
        if "Player" not in frame:
            raise ValueError("Player data must contain a Player Key or Player column.")
        frame = frame.copy()
        frame["Player Key"] = frame["Player"].fillna("").map(make_player_key)

    counts = Counter(_clean(value) for value in frame["Player Key"] if _clean(value))
    duplicate_keys = {key for key, count in counts.items() if count > 1}
    records: dict[str, dict[str, Any]] = {}
    for row in frame.to_dict("records"):
        key = _clean(row.get("Player Key"))
        if key and key not in duplicate_keys:
            records[key] = row
    return records, duplicate_keys


def compare_contracts(
    spotrac: pd.DataFrame,
    existing: pd.DataFrame,
    owners: pd.DataFrame,
    selected_teams: list[str] | None = None,
) -> pd.DataFrame:
    if selected_teams and "Team" in existing:
        selected_names = {
            make_player_key(team.replace("-", " "))
            for team in selected_teams
        }
        existing = existing[
            existing["Team"].fillna("").map(make_player_key).isin(selected_names)
        ].copy()

    spotrac_by_key, duplicate_spotrac = _to_records_by_key(spotrac)
    existing_by_key, duplicate_existing = _to_records_by_key(existing)
    owner_by_key, duplicate_owners = owner_index(owners)

    season_sort = lambda column: int(str(column)[:4])
    spotrac_seasons = sorted(
        (column for column in spotrac.columns if SEASON_PATTERN.fullmatch(str(column))),
        key=season_sort,
    )
    existing_seasons = sorted(
        (column for column in existing.columns if SEASON_PATTERN.fullmatch(str(column))),
        key=season_sort,
    )
    seasons = (spotrac_seasons or existing_seasons)[:5]
    all_keys = sorted(
        set(spotrac_by_key)
        | set(existing_by_key)
        | duplicate_spotrac
        | duplicate_existing
    )
    comparisons: list[dict[str, Any]] = []
    for key in all_keys:
        new_row = spotrac_by_key.get(key, {})
        old_row = existing_by_key.get(key, {})
        player = _clean(new_row.get("Player")) or _clean(old_row.get("Player"))
        owner = owner_by_key.get(key, "")
        owner_match = owner
        team = _clean(new_row.get("Team")) or _clean(old_row.get("Team"))
        if key in duplicate_spotrac or key in duplicate_existing or key in duplicate_owners:
            status = "Ambiguous"
            seasons_to_report = seasons or [""]
            for season in seasons_to_report:
                comparisons.append(
                    _comparison_row(
                        player, key, owner, team, season, "", "", status, owner_match
                    )
                )
            continue

        if not new_row:
            seasons_to_report = seasons or [""]
            for season in seasons_to_report:
                comparisons.append(
                    _comparison_row(
                        player, key, owner, team, season,
                        _clean(old_row.get(season)), "", "Waived",
                        owner_match,
                    )
                )
            continue
        if not old_row:
            seasons_to_report = seasons or [""]
            for season in seasons_to_report:
                comparisons.append(
                    _comparison_row(
                        player, key, owner, team, season, "",
                        _clean(new_row.get(season)), "Signed",
                        owner_match,
                    )
                )
            continue

        latest_existing_season = max(
            (
                season_sort(season)
                for season in existing_seasons
                if normalized_contract_value(old_row.get(season))[0] != "missing"
            ),
            default=-1,
        )
        for season in seasons:
            old_value = _clean(old_row.get(season))
            new_value = _clean(new_row.get(season))
            old_normalized = normalized_contract_value(old_value)
            new_normalized = normalized_contract_value(new_value)
            if old_normalized[0] == "missing" and new_normalized[0] == "missing":
                status = "Unchanged"
            elif old_normalized[0] == "missing":
                status = (
                    "Extended"
                    if latest_existing_season >= 0
                    and season_sort(season) > latest_existing_season
                    else "Changed"
                )
            elif new_normalized[0] == "missing":
                status = "Changed"
            elif old_normalized == new_normalized:
                status = "Unchanged"
            else:
                status = "Changed"
            comparisons.append(
                _comparison_row(
                    player, key, owner, team, season, old_value, new_value, status,
                    owner_match,
                )
            )

    result = pd.DataFrame(comparisons, columns=COMPARISON_COLUMNS)
    result = result[result["Status"] != "Unchanged"]
    return result.sort_values(
        ["Player Key", "Season"], kind="stable", ignore_index=True
    )


def _comparison_row(
    player: str,
    key: str,
    owner: str,
    team: str,
    season: str,
    existing_value: str,
    spotrac_value: str,
    status: str,
    owner_match: str,
) -> dict[str, str]:
    return {
        "Player": player,
        "Player Key": key,
        "Owner": owner,
        "Team": team,
        "Season": season,
        "Existing Value": format_contract_value(existing_value),
        "Spotrac Value": format_contract_value(spotrac_value),
        "Status": status,
        "Owner Match": owner_match,
        "Owner Source": "Google Sheets: Owned" if owner else "",
        "Existing Source": "Google Sheets: Contracts",
        "Spotrac Source": "Spotrac",
    }


def _column_letter(index: int) -> str:
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def build_sheet_write_plan(
    spotrac: pd.DataFrame,
    raw_sheet_values: list[list[str]],
    owners: pd.DataFrame,
) -> SheetWritePlan:
    if not raw_sheet_values:
        raise ValueError("The Contracts worksheet is empty.")

    headers = [_clean(value) for value in raw_sheet_values[0]]
    if "Player Key" not in headers:
        raise ValueError("The Contracts worksheet must have a 'Player Key' header.")
    if "Owner" not in headers:
        raise ValueError("The Contracts worksheet must have an 'Owner' column.")

    key_column = headers.index("Player Key")
    owner_column = headers.index("Owner")
    expected_identity = [
        "Player",
        "Player Link",
        "Player Key",
        "Team",
        "Team Link",
        "Position",
        "Age",
    ]
    if headers[: len(expected_identity)] != expected_identity:
        raise ValueError(
            "The Contracts worksheet must keep Player through Age in columns A-G."
        )
    if owner_column != 12:
        raise ValueError("The Contracts worksheet Owner column must remain column M.")
    season_columns = [column for column in headers if SEASON_PATTERN.fullmatch(column)]
    if not season_columns:
        raise ValueError("The Contracts worksheet has no season columns.")

    existing_rows: dict[str, list[tuple[int, list[str]]]] = defaultdict(list)
    for row_number, raw_row in enumerate(raw_sheet_values[1:], start=2):
        values = list(raw_row) + [""] * max(0, len(headers) - len(raw_row))
        key = _clean(values[key_column])
        if not key:
            player_column = headers.index("Player") if "Player" in headers else None
            if player_column is not None:
                key = make_player_key(_clean(values[player_column]))
        if key:
            existing_rows[key].append((row_number, values))

    source_rows: dict[str, dict[str, Any]] = {}
    duplicate_source: set[str] = set()
    for row in spotrac.to_dict("records"):
        key = _clean(row.get("Player Key"))
        if not key:
            continue
        if key in source_rows:
            duplicate_source.add(key)
        source_rows[key] = row

    owner_by_key, ambiguous_owners = owner_index(owners)
    plan = SheetWritePlan()
    last_contract_row = max(
        (row_number for rows in existing_rows.values() for row_number, _ in rows),
        default=1,
    )
    for key in sorted(duplicate_source | ambiguous_owners):
        if key in source_rows or key in existing_rows:
            plan.ambiguous_keys.append(key)

    for key, source in source_rows.items():
        if key in duplicate_source or key in ambiguous_owners:
            continue
        matched_rows = existing_rows.get(key, [])
        if len(matched_rows) > 1:
            plan.ambiguous_keys.append(key)
            continue

        if matched_rows:
            row_number, current_values = matched_rows[0]
            for column_index, header in enumerate(headers):
                if column_index == owner_column or header not in source:
                    continue
                new_value = format_contract_value(source[header]) if header in season_columns else _clean(source[header])
                if not new_value:
                    continue
                old_value = _clean(current_values[column_index])
                if header in season_columns and normalized_contract_value(old_value) == normalized_contract_value(new_value):
                    continue
                if old_value == new_value:
                    continue
                plan.updates.append(
                    CellUpdate(
                        f"{_column_letter(column_index + 1)}{row_number}",
                        new_value,
                        old_value,
                    )
                )
            continue

        new_values = [""] * (owner_column + 1)
        for column_index, header in enumerate(headers[: owner_column + 1]):
            if header in source:
                value = source[header]
                new_values[column_index] = (
                    format_contract_value(value)
                    if header in season_columns
                    else _clean(value)
                )
        new_values[owner_column] = owner_by_key.get(key, "")
        plan.append_rows.append(new_values)

    if plan.append_rows:
        plan.append_start_row = last_contract_row + 1
    return plan