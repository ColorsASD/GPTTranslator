"""A natív felület képei külön profillal, hálózat és rendszerhook nélkül."""
from __future__ import annotations

import argparse
import json
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

from PySide6.QtCore import QCoreApplication, QEvent, QEventLoop, QPoint, QRect, QRectF, QTimer, Qt, QUrl
from PySide6.QtGui import QColor, QFont, QFontDatabase, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineCore import QWebEngineUrlRequestInterceptor

from gamer_translator.main_window import MainWindow, QuickChatOverlay
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


def render_quick_chat(app: QApplication, output: Path) -> None:
    overlay = QuickChatOverlay()
    results = []
    # Kizárólag saját, szintetikus háttér: nem készül asztal- vagy játékfelvétel.
    with patch.object(overlay, "_hide_if_inactive"):
        for width, height, suffix, state in (
            (1672, 900, "desktop", "empty"),
            (1080, 720, "compact", "text"),
            (800, 450, "small", "text"),
            (600, 600, "narrow", "text"),
            (1080, 720, "busy", "busy"),
            (800, 450, "error", "error"),
            (640, 360, "short", "text"),
            (640, 360, "short-error", "error"),
        ):
            overlay.hide()
            overlay.resize(width, height)
            background = QPixmap(width // 2, height // 2)
            painter = QPainter(background)
            gradient = QLinearGradient(0, 0, background.width(), background.height())
            gradient.setColorAt(0, QColor("#555555"))
            gradient.setColorAt(1, QColor("#242424"))
            painter.fillRect(background.rect(), gradient)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#383838"))
            painter.drawRoundedRect(QRectF(20, 20, width * .11, height * .43), 12, 12)
            painter.setBrush(QColor("#484848"))
            painter.drawRoundedRect(QRectF(width * .15, 20, width * .32, height * .15), 12, 12)
            painter.end()
            overlay.background_label.setPixmap(background)
            overlay.text_input.setPlainText(
                "" if state == "empty" else
                "Szia! A következő körben maradjunk együtt.\nÉn figyelem a bejáratot, te fedezd a lépcsőt."
            )
            overlay.set_busy(state == "busy", "Fordítás folyamatban..." if state == "busy" else "")
            if state == "error":
                overlay.show_error("Írj be legalább egy sort a gyors chat elküldéséhez.")
            overlay.show()
            overlay.text_input.setFocus()
            app.processEvents()
            wait_for_paint()
            if overlay.size().width() != width or overlay.size().height() != height:
                raise AssertionError(f"A gyors chat túlnőtt az előnézeten: {suffix}")
            if not overlay.rect().contains(overlay.panel.geometry()):
                raise AssertionError(f"A gyors chat panelje kilóg: {suffix}")
            for widget in (overlay.title_label, overlay.hint_label, overlay.text_input,
                           overlay.cancel_button, overlay.submit_button, overlay.status_label):
                if not widget.isVisible():
                    continue
                rectangle = QRect(widget.mapTo(overlay.panel, QPoint(0, 0)), widget.size())
                if not overlay.panel.rect().contains(rectangle):
                    raise AssertionError(f"A gyors chat vezérlője kilóg: {suffix}, {widget.objectName()}")
            rows = [overlay.panel_layout.itemAt(index).widget()
                    for index in range(overlay.panel_layout.count())]
            rows = [widget for widget in rows if widget.isVisible()]
            for index, widget in enumerate(rows):
                for other in rows[index + 1:]:
                    if widget.geometry().intersects(other.geometry()):
                        raise AssertionError(f"A gyors chat sorai átfedik egymást: {suffix}")
            if overlay.submit_button.height() < overlay.submit_button.minimumSizeHint().height():
                raise AssertionError(f"A gyors chat küldésgombja összenyomódott: {suffix}")
            overlay.grab().save(str(output / f"quick-chat-{suffix}.png"))
            if suffix == "compact":
                overlay.panel.grab().save(str(output / "quick-chat-panel.png"))
            results.append({"size": [width, height], "state": state,
                            "panel": list(overlay.panel.geometry().getRect()),
                            "controls_inside": True, "rows_without_overlap": True,
                            "submit_button_full_height": True})
            print(f"quick-chat-{suffix}: {width}x{height}, panel: "
                  f"{overlay.panel.width()}x{overlay.panel.height()}")
        overlay.hide()
    overlay.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    (output / "quick-chat-layouts.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("dist/browser-home-preview"))
    parser.add_argument("--quick-chat-only", action="store_true", help="Csak a gyors chat saját, helyi előnézetei.")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    # Az offscreen platform nem tölti be automatikusan a Windows betűkészleteit.
    font_dir = Path(os.environ.get("SystemRoot", "C:/Windows")) / "Fonts"
    for name in ("segoeui.ttf", "segoeuib.ttf", "segoeuis.ttf"):
        QFontDatabase.addApplicationFont(str(font_dir / name))
    app.setFont(QFont("Segoe UI", 10))
    if args.quick_chat_only:
        render_quick_chat(app, args.output)
        print(args.output.resolve())
        return
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
    render_quick_chat(app, args.output)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
