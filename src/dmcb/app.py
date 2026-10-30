from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from dmcb.ui.main_window import MainWindow


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    application = QApplication(sys.argv)
    application.setApplicationName("DMCB Commissioner")
    asset_root = Path(
        getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2])
    )
    application.setWindowIcon(
        QIcon(str(asset_root / "icon.iconset" / "icon_512x512.png"))
    )
    window = MainWindow()
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())