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
# A külön előnézeti folyamat nem használja az offscreen platformon nem elérhető GPU-t.
preview_flags = [
    flag for flag in os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "").split()
    if flag not in ("--enable-gpu-rasterization", "--enable-zero-copy")
]
preview_flags.extend(("--disable-gpu", "--disable-gpu-compositing"))
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = " ".join(dict.fromkeys(preview_flags))
os.environ.setdefault("QT_OPENGL", "software")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QCoreApplication, QEvent, QEventLoop, QTimer, QUrl
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineCore import QWebEngineUrlRequestInterceptor

from gamer_translator.main_window import MainWindow
from gamer_translator.settings_store import SettingsStore


OFFLINE_BROWSER_HTML = """<!doctype html>
<html lang="hu"><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<title>Offline felületi előnézet</title>
<style>
html, body { margin: 0; height: 100%; background: #212121; color: #ececec; }
body { display: grid; place-items: center; font-family: 'Segoe UI', sans-serif; }
main { max-width: 620px; padding: 32px; text-align: center; }
h1 { margin: 0 0 16px; font-size: 24px; font-weight: 600; }
p { margin: 0; color: #b2b2b2; line-height: 1.6; font-size: 16px; }
</style></head><body><main>
<h1>ChatGPT nézet helye – offline felületi előnézet</h1>
<p>Az alkalmazás itt jeleníti meg a chatgpt.com oldalt.
Ez a helyi előnézet csak a felület elrendezését mutatja; nem nyit élő weboldalt.</p>
</main></body></html>"""


class OfflineRequestInterceptor(QWebEngineUrlRequestInterceptor):
    def interceptRequest(self, info) -> None:  # type: ignore[override]
        if info.requestUrl().scheme() not in ("about", "data", "qrc"):
            info.block(True)


def wait_for_paint() -> None:
    loop = QEventLoop()
    QTimer.singleShot(200, loop.quit)
    loop.exec()


def load_offline_browser(window: MainWindow) -> None:
    loop = QEventLoop()
    result: list[bool] = []

    def finished(ok: bool) -> None:
        result.append(ok)
        loop.quit()

    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    window.browser.loadFinished.connect(finished)
    window.browser.setHtml(OFFLINE_BROWSER_HTML, QUrl("about:blank"))
    timer.start(5000)
    loop.exec()
    timer.stop()
    window.browser.loadFinished.disconnect(finished)
    if not result or not result[-1]:
        raise RuntimeError("Az offline felületi előnézet nem töltődött be.")
    wait_for_paint()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("dist/browser-home-preview"))
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
            "_handle_load_started", "_handle_load_finished",
        ):
            stack.enter_context(patch.object(MainWindow, method))
        stack.enter_context(patch.object(MainWindow, "_current_clipboard_signature", return_value=""))
        window = MainWindow(store=SettingsStore(root_dir=Path(temporary)), clipboard=Mock(),
                            private_browser=True, open_on_start=False)
        interceptor = OfflineRequestInterceptor(window.profile)
        window.profile.setUrlRequestInterceptor(interceptor)
        window.show()
        load_offline_browser(window)
        window._set_live_status("Offline felületi előnézet.")
        for width, height, suffix in ((1672, 900, "desktop"), (1080, 720, "compact")):
            window.resize(width, height)
            app.processEvents()
            window._show_browser()
            app.processEvents()
            wait_for_paint()
            window.grab().save(str(args.output / f"browser-{suffix}.png"))
            window._set_drawer_open(True)
            app.processEvents()
            wait_for_paint()
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
