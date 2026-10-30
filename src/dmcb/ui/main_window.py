from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

import pandas as pd
from PySide6.QtCore import QSettings, QThread, Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from dmcb.config import AppConfig
from dmcb.models.records import OWNER_SOURCE
from dmcb.services import basketball_reference, reconciliation, sheets, spotrac, sportsws
from scripts.utils import make_title_case

LOGGER = logging.getLogger(__name__)


class Job(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, work: Callable[[], object]):
        super().__init__()
        self.work = work

    def run(self) -> None:
        try:
            self.succeeded.emit(self.work())
        except Exception as error:
            LOGGER.exception("Background application task failed")
            self.failed.emit(str(error))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DMCB Commissioner")
        self.resize(1250, 800)
        self.config = AppConfig.from_environment()
        self.settings = QSettings("DMCB", "Commissioner")
        self.current_job: Job | None = None
        self.contracts: pd.DataFrame | None = None
        self.all_contracts: pd.DataFrame | None = None
        self.comparisons: pd.DataFrame | None = None
        self.selected_team_slugs: list[str] = []
        self.owners = pd.DataFrame()
        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)
        self.tabs = QTabWidget()
        self.contract_tab = self._build_contract_tab()
        self.details_tab = self._build_details_tab()
        self.league_data_tab = self._build_league_data_tab()
        self.settings_tab = self._build_settings_tab()
        self.tabs.addTab(self.contract_tab, "Contracts")
        self.tabs.addTab(self.details_tab, "Player Details")
        self.tabs.addTab(self.league_data_tab, "Positions & Stats")
        self.tabs.addTab(self.settings_tab, "Settings")
        layout.addWidget(self.tabs)
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        self.setCentralWidget(central)

    def _build_contract_tab(self) -> QWidget:
        tab = QWidget()
        outer = QVBoxLayout(tab)
        controls = QHBoxLayout()
        self.team_list = QListWidget()
        self.team_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        for team in spotrac.available_teams():
            item = QListWidgetItem(make_title_case(team))
            item.setData(Qt.ItemDataRole.UserRole, team)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.team_list.addItem(item)
        controls.addWidget(self.team_list, 1)

        buttons = QVBoxLayout()
        select_all = QPushButton("Select all 30")
        select_all.clicked.connect(self._select_all_teams)
        clear_selection = QPushButton("Clear selection")
        clear_selection.clicked.connect(self._clear_team_selection)
        fetch = QPushButton("Fetch Spotrac contracts")
        fetch.clicked.connect(self._fetch_contracts)
        compare = QPushButton("Load Sheets & compare")
        compare.clicked.connect(self._compare_contracts)
        self.export_contracts_button = QPushButton("Export contracts CSV")
        self.export_contracts_button.clicked.connect(self._export_contracts)
        self.export_discrepancies_button = QPushButton("Export discrepancies CSV")
        self.export_discrepancies_button.clicked.connect(self._export_discrepancies)
        self.write_button = QPushButton("Review & write to Contracts")
        self.write_button.clicked.connect(self._prepare_sheet_write)
        for button in (
            select_all,
            clear_selection,
            fetch,
            compare,
            self.export_contracts_button,
            self.export_discrepancies_button,
            self.write_button,
        ):
            buttons.addWidget(button)
        buttons.addStretch(1)
        controls.addLayout(buttons, 2)
        outer.addLayout(controls)

        self.contract_views = QTabWidget()
        self.contract_table = self._new_table()
        self.comparison_table = self._new_table()
        self.contract_views.addTab(self.contract_table, "Spotrac contracts")
        self.contract_views.addTab(self.comparison_table, "Contract comparison")
        outer.addWidget(self.contract_views, 1)
        return tab

    def _build_details_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("Enter one Spotrac player URL per line:"))
        self.player_urls = QTextEdit()
        self.player_urls.setPlaceholderText("https://www.spotrac.com/nba/player/_/id/...")
        layout.addWidget(self.player_urls)
        controls = QHBoxLayout()
        fetch = QPushButton("Fetch player details")
        fetch.clicked.connect(self._fetch_player_details)
        export = QPushButton("Export player details CSV")
        export.clicked.connect(
            lambda: self._export_frame(self.details_table, "spotrac_player_details.csv")
        )
        controls.addWidget(fetch)
        controls.addWidget(export)
        controls.addStretch(1)
        layout.addLayout(controls)
        self.details_table = self._new_table()
        layout.addWidget(self.details_table, 1)
        return tab

    def _build_league_data_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        controls = QHBoxLayout()
        positions = QPushButton("Fetch Sports.ws positions")
        positions.clicked.connect(self._fetch_positions)
        controls.addWidget(positions)
        controls.addWidget(QLabel("Basketball-Reference season end year:"))
        self.stats_year = QComboBox()
        latest_year = basketball_reference.latest_available_season()
        self.stats_year.addItems(
            [str(year) for year in range(latest_year, 1946, -1)]
        )
        controls.addWidget(self.stats_year)
        stats = QPushButton("Fetch stats")
        stats.clicked.connect(self._fetch_stats)
        controls.addWidget(stats)
        export = QPushButton("Export displayed data CSV")
        export.clicked.connect(self._export_league_data)
        controls.addWidget(export)
        controls.addStretch(1)
        layout.addLayout(controls)
        self.league_data_table = self._new_table()
        layout.addWidget(self.league_data_table, 1)
        self.league_data_frame = pd.DataFrame()
        return tab

    def _build_settings_tab(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)
        credentials_row = QHBoxLayout()
        self.credentials_path = QLineEdit(
            str(self.settings.value("credentials_path", self.config.credentials_path))
        )
        self.credentials_path.setEchoMode(QLineEdit.EchoMode.Normal)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse_credentials)
        credentials_row.addWidget(self.credentials_path, 1)
        credentials_row.addWidget(browse)
        form.addRow("Service-account JSON:", credentials_row)
        self.spreadsheet_url = QLineEdit(
            str(self.settings.value("spreadsheet_url", self.config.spreadsheet_url))
        )
        form.addRow("Google Sheets URL:", self.spreadsheet_url)
        save_settings = QPushButton("Save settings")
        save_settings.clicked.connect(self._save_settings)
        form.addRow(save_settings)
        form.addRow(
            QLabel(
                "Credentials are read from this local path and are never shown in "
                "exports. The app stores only the path and workbook URL in local "
                "application settings; keep the key outside the repository."
            )
        )
        return tab

    @staticmethod
    def _new_table() -> QTableWidget:
        table = QTableWidget()
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(True)
        return table

    def _selected_teams(self) -> list[str]:
        return [
            str(self.team_list.item(index).data(Qt.ItemDataRole.UserRole))
            for index in range(self.team_list.count())
            if self.team_list.item(index).checkState() == Qt.CheckState.Checked
        ]

    def _select_all_teams(self) -> None:
        for index in range(self.team_list.count()):
            self.team_list.item(index).setCheckState(Qt.CheckState.Checked)

    def _clear_team_selection(self) -> None:
        for index in range(self.team_list.count()):
            self.team_list.item(index).setCheckState(Qt.CheckState.Unchecked)

    def _run_job(
        self,
        label: str,
        work: Callable[[], object],
        on_success: Callable[[object], None],
    ) -> None:
        if self.current_job is not None and self.current_job.isRunning():
            self.status_label.setText("A task is already running; wait for it to finish.")
            return
        self.status_label.setText(f"{label}…")
        job = Job(work)
        self.current_job = job
        job.succeeded.connect(on_success)
        job.failed.connect(self._show_error)
        job.start()

    def _show_error(self, message: str) -> None:
        self.status_label.setText("Task failed")
        QMessageBox.critical(self, "DMCB task failed", message)

    def _fetch_contracts(self) -> None:
        selected = self._selected_teams()
        if not selected:
            self._show_error("Select at least one NBA team.")
            return
        self.selected_team_slugs = selected
        self._run_job(
            "Fetching Spotrac contracts",
            lambda: spotrac.scrape_contracts(selected),
            self._show_contracts,
        )

    def _show_contracts(self, result: object) -> None:
        self.all_contracts = result.all_years
        self.contracts = result.displayed
        self.comparisons = None
        self._populate_table(self.contract_table, self.contracts)
        self.contract_views.setCurrentWidget(self.contract_table)
        self.status_label.setText(
            f"Loaded {len(self.contracts)} player/team records; "
            f"{len(result.season_columns)} Spotrac seasons found."
        )

    def _compare_contracts(self) -> None:
        if self.contracts is None or self.all_contracts is None:
            self._show_error("Fetch Spotrac contracts before comparing.")
            return
        all_contracts = self.all_contracts
        selected_teams = self.selected_team_slugs
        credentials_path = self.credentials_path.text().strip()
        spreadsheet_url = self.spreadsheet_url.text().strip()

        def read_and_compare() -> tuple[pd.DataFrame, pd.DataFrame]:
            manager = sheets.GoogleSheetsService(credentials_path, spreadsheet_url)
            owners = manager.read_owners()
            _, existing = manager.read_contracts()
            comparisons = reconciliation.compare_contracts(
                all_contracts,
                existing,
                owners,
                selected_teams=selected_teams,
            )
            return owners, comparisons

        self._run_job("Reading Google Sheets and comparing", read_and_compare, self._show_comparison)

    def _show_comparison(self, result: object) -> None:
        owners, comparisons = result
        self.owners = owners
        self.comparisons = comparisons
        owner_lookup, _ = reconciliation.owner_index(owners)
        self.contracts = self.contracts.copy()
        self.contracts["Owner"] = self.contracts["Player Key"].map(owner_lookup).fillna("")
        self.contracts["Owner Match"] = self.contracts["Owner"]
        self.contracts["Owner Source"] = self.contracts["Owner"].map(
            lambda owner: OWNER_SOURCE if owner else ""
        )
        self._populate_table(self.contract_table, self.contracts)
        self._populate_table(self.comparison_table, comparisons, enable_sorting=False)
        self.contract_views.setCurrentWidget(self.comparison_table)
        discrepant = int(comparisons["Status"].ne("Unchanged").sum())
        self.status_label.setText(f"Comparison complete: {discrepant} discrepancy/status row(s).")

    def _prepare_sheet_write(self) -> None:
        if self.contracts is None:
            self._show_error("Fetch Spotrac contracts before writing.")
            return
        credentials_path = self.credentials_path.text().strip()
        spreadsheet_url = self.spreadsheet_url.text().strip()

        def make_plan() -> tuple[list[list[str]], object]:
            manager = sheets.GoogleSheetsService(credentials_path, spreadsheet_url)
            owners = manager.read_owners()
            raw_values, plan = manager.build_write_plan(self.contracts, owners)
            return raw_values, plan

        self._run_job("Preparing Sheets write preview", make_plan, self._confirm_sheet_write)

    def _confirm_sheet_write(self, result: object) -> None:
        raw_values, plan = result
        if plan.change_count == 0:
            skipped = (
                f" {len(plan.ambiguous_keys)} ambiguous Player Key(s) were skipped."
                if plan.ambiguous_keys
                else ""
            )
            self.status_label.setText(f"No Sheets changes to write.{skipped}")
            return
        headers = [str(value) for value in raw_values[0]] if raw_values else []
        dialog = QDialog(self)
        dialog.setWindowTitle("Review Google Sheets changes")
        dialog.resize(900, 600)
        dialog_layout = QVBoxLayout(dialog)
        ambiguous = (
            f"{len(plan.ambiguous_keys)} ambiguous Player Key(s) will be skipped: "
            + ", ".join(plan.ambiguous_keys[:10])
            if plan.ambiguous_keys
            else "No ambiguous Player Keys found."
        )
        dialog_layout.addWidget(
            QLabel(
                f"Target: Google Sheets → Contracts\n"
                f"Existing cells to update: {len(plan.updates)}; "
                f"new rows to append: {len(plan.append_rows)}.\n"
                f"{ambiguous}\n"
                "A timestamped local CSV backup will be saved before writing."
            )
        )
        preview = QTableWidget()
        preview.setColumnCount(4)
        preview.setHorizontalHeaderLabels(["Action", "Cell / field", "Before", "After"])
        preview.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        preview.setAlternatingRowColors(True)
        preview_rows: list[tuple[str, str, str, str]] = [
            ("Update", update.cell, update.old_value, update.value)
            for update in plan.updates
        ]
        if plan.append_start_row is None and plan.append_rows:
            self._show_error("The write plan is missing the new-row start position.")
            return
        for offset, row in enumerate(plan.append_rows):
            row_number = plan.append_start_row + offset
            for column_index, value in enumerate(row):
                if value:
                    header = headers[column_index] if column_index < len(headers) else f"Column {column_index + 1}"
                    preview_rows.append(
                        ("Append", f"{header} (row {row_number})", "", value)
                    )
        preview.setRowCount(len(preview_rows))
        for row_number, values in enumerate(preview_rows):
            for column_number, value in enumerate(values):
                preview.setItem(row_number, column_number, QTableWidgetItem(value))
        preview.resizeColumnsToContents()
        preview.setSortingEnabled(True)
        dialog_layout.addWidget(preview, 1)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.No
        )
        buttons.button(QDialogButtonBox.StandardButton.Yes).setText("Write changes")
        buttons.button(QDialogButtonBox.StandardButton.No).setText("Cancel")
        buttons.button(QDialogButtonBox.StandardButton.No).setDefault(True)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        dialog_layout.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self.status_label.setText("Sheets write cancelled.")
            return

        def back_up_and_write() -> Path:
            backup = sheets.GoogleSheetsService.save_backup(
                raw_values, AppConfig.backup_directory()
            )
            sheets.GoogleSheetsService(credentials_path, spreadsheet_url).apply_write_plan(
                plan, expected_sheet_values=raw_values
            )
            return backup

        self._run_job("Backing up and writing to Sheets", back_up_and_write, self._write_complete)

    def _write_complete(self, result: object) -> None:
        self.status_label.setText(f"Sheets updated. Backup saved to {result}")
        QMessageBox.information(self, "Sheets updated", f"Backup saved to:\n{result}")

    def _fetch_player_details(self) -> None:
        urls = self.player_urls.toPlainText().splitlines()
        self._run_job(
            "Fetching Spotrac player details",
            lambda: spotrac.scrape_player_details(urls),
            lambda frame: self._show_frame(self.details_table, frame),
        )

    def _fetch_positions(self) -> None:
        self._run_job(
            "Fetching Sports.ws positions",
            sportsws.get_positions,
            self._show_league_data,
        )

    def _fetch_stats(self) -> None:
        year = int(self.stats_year.currentText())
        self._run_job(
            f"Fetching Basketball-Reference {year} stats",
            lambda: basketball_reference.get_stats(year),
            self._show_league_data,
        )

    def _show_league_data(self, frame: object) -> None:
        self.league_data_frame = frame
        self._show_frame(self.league_data_table, frame)
        source = frame["Data Source"].iloc[0] if not frame.empty else "source"
        self.status_label.setText(f"Loaded {len(frame)} records from {source}.")

    def _show_frame(self, table: QTableWidget, frame: pd.DataFrame) -> None:
        self._populate_table(table, frame)
        self.status_label.setText(f"Loaded {len(frame)} records.")

    def _browse_credentials(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select Google service-account JSON",
            str(Path.home()),
            "JSON files (*.json)",
        )
        if filename:
            self.credentials_path.setText(filename)

    def _save_settings(self) -> None:
        self.settings.setValue("credentials_path", self.credentials_path.text().strip())
        self.settings.setValue("spreadsheet_url", self.spreadsheet_url.text().strip())
        self.settings.sync()
        if self.settings.status() != QSettings.Status.NoError:
            self._show_error("Could not save local application settings.")
            return
        self.status_label.setText("Settings saved locally.")

    def _export_contracts(self) -> None:
        if self.contracts is None:
            self._show_error("Fetch contracts before exporting.")
            return
        self._export_frame_data(self.contracts, "spotrac_contracts.csv")

    def _export_discrepancies(self) -> None:
        if self.comparisons is None:
            self._show_error("Compare contracts with Google Sheets before exporting.")
            return
        discrepancies = self.comparisons[self.comparisons["Status"].ne("Unchanged")]
        self._export_frame_data(discrepancies, "contract_discrepancies.csv")

    def _export_league_data(self) -> None:
        if self.league_data_frame.empty:
            self._show_error("Fetch positions or statistics before exporting.")
            return
        self._export_frame_data(self.league_data_frame, "league_data.csv")

    def _export_frame(self, table: QTableWidget, default_name: str) -> None:
        frame = self._frame_from_table(table)
        if frame.empty:
            self._show_error("There is no displayed data to export.")
            return
        self._export_frame_data(frame, default_name)

    def _export_frame_data(self, frame: pd.DataFrame, default_name: str) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export CSV",
            str(Path.home() / default_name),
            "CSV files (*.csv)",
        )
        if not filename:
            return
        destination = Path(filename)
        if destination.suffix.lower() != ".csv":
            destination = destination.with_suffix(".csv")
        try:
            frame.to_csv(destination, index=False, encoding="utf-8")
        except OSError as error:
            self._show_error(f"Could not save CSV to {destination}: {error}")
            return
        self.status_label.setText(f"CSV exported to {destination}")

    @staticmethod
    def _frame_from_table(table: QTableWidget) -> pd.DataFrame:
        headers = [
            table.horizontalHeaderItem(column).text()
            for column in range(table.columnCount())
        ]
        rows = [
            [
                table.item(row, column).text() if table.item(row, column) else ""
                for column in range(table.columnCount())
            ]
            for row in range(table.rowCount())
        ]
        return pd.DataFrame(rows, columns=headers)

    @staticmethod
    def _populate_table(
        table: QTableWidget, frame: pd.DataFrame, enable_sorting: bool = True
    ) -> None:
        table.setSortingEnabled(False)
        table.clear()
        table.setColumnCount(len(frame.columns))
        table.setRowCount(len(frame))
        table.setHorizontalHeaderLabels([str(column) for column in frame.columns])
        for row_number, values in enumerate(frame.itertuples(index=False, name=None)):
            for column_number, value in enumerate(values):
                text = "" if pd.isna(value) else str(value)
                table.setItem(row_number, column_number, QTableWidgetItem(text))
        table.resizeColumnsToContents()
        table.setSortingEnabled(enable_sorting)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.current_job is not None and self.current_job.isRunning():
            self.status_label.setText("Waiting for the current task to finish…")
            self.current_job.wait()
        event.accept()
