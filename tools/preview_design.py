"""A natív felület képei külön profillal, hálózat és rendszerhook nélkül."""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QCoreApplication, QEvent, QUrl
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from gamer_translator.main_window import MainWindow
from gamer_translator.settings_store import SettingsStore


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("dist/design-preview"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    # Az offscreen platform nem tölti be automatikusan a Windows betűkészleteit.
    font_dir = Path(os.environ.get("SystemRoot", "C:/Windows")) / "Fonts"
    for name in ("segoeui.ttf", "segoeuib.ttf", "segoeuis.ttf"):
        QFontDatabase.addApplicationFont(str(font_dir / name))
    app.setFont(QFont("Segoe UI", 10))
    with ExitStack() as stack:
        temporary = stack.enter_context(tempfile.TemporaryDirectory(ignore_cleanup_errors=True))
        for method in (
            "_register_hotkeys", "_unregister_hotkeys", "_uninstall_keyboard_hook",
            "_uninstall_mouse_hook", "_build_tray_icon", "_refresh_system_keep_awake",
            "_restore_system_sleep_state", "_apply_native_window_theme",
        ):
            stack.enter_context(patch.object(MainWindow, method))
        stack.enter_context(patch.object(MainWindow, "_current_clipboard_signature", return_value=""))
        window = MainWindow(store=SettingsStore(root_dir=Path(temporary)), clipboard=Mock(),
                            private_browser=True, open_on_start=False)
        window.show()
        window._update_browser_origin_label(QUrl("https://chatgpt.com/"))
        window._set_live_status("Indulásra kész.")
        for width, height, suffix in ((1672, 900, "desktop"), (1080, 720, "compact")):
            window.resize(width, height)
            app.processEvents()
            window._show_home()
            app.processEvents()
            window.grab().save(str(args.output / f"home-{suffix}.png"))
            window._set_drawer_open(True)
            app.processEvents()
            window.grab().save(str(args.output / f"settings-{suffix}.png"))
            print(f"{suffix}: {window.width()}x{window.height()}, panel: "
                  f"{window.content_surface.width()}x{window.content_surface.height()}")
        window.exit_requested = True
        window.close()
        for widget in (window.browser, window.page, window.browser_background_host,
                       window.translation_overlay, window.quick_chat_overlay):
            widget.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        window.profile.deleteLater()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
