from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class AppConfig:
    credentials_path: str
    spreadsheet_url: str

    @classmethod
    def from_environment(cls) -> "AppConfig":
        return cls(
            credentials_path=os.getenv("GOOGLE_SHEETS_CREDENTIALS", ""),
            spreadsheet_url=os.getenv("GOOGLE_SHEETS_URL", ""),
        )

    @staticmethod
    def backup_directory() -> Path:
        if sys.platform == "darwin":
            root = Path.home() / "Library" / "Application Support" / "DMCB"
        elif os.name == "nt":
            root = Path(os.getenv("LOCALAPPDATA", Path.home())) / "DMCB"
        else:
            root = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "dmcb"
        return root / "backups"
