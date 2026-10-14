"""Az első layout után a webnézet széle és a beállításréteg a teljes felületet követi."""
from __future__ import annotations

import os
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWebEngineCore import QWebEngineUrlRequestInterceptor
from PySide6.QtWidgets import QApplication

from gamer_translator.main_window import MainWindow
from gamer_translator.settings_store import SettingsStore


class BlockStartupNetwork(QWebEngineUrlRequestInterceptor):
    def interceptRequest(self, request):
        if request.requestUrl().scheme() not in {"about", "data", "blob"}:
            request.block(True)


class StartupGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        directory = self.stack.enter_context(tempfile.TemporaryDirectory(ignore_cleanup_errors=True))
        for name in (
            "open_chatgpt", "_register_hotkeys", "_unregister_hotkeys",
            "_install_keyboard_hook", "_uninstall_keyboard_hook", "_install_mouse_hook", "_uninstall_mouse_hook",
            "_build_tray_icon", "_refresh_system_keep_awake", "_restore_system_sleep_state",
            "_apply_native_window_theme", "_ensure_automation_ready",
        ):
            self.stack.enter_context(patch.object(MainWindow, name))
        self.stack.enter_context(patch.object(MainWindow, "_current_clipboard_signature", return_value=""))
        store = SettingsStore(root_dir=Path(directory))
        settings = store.load_settings()
        settings.monitoring_enabled = False
        settings.ocr_text_from_clipboard_image = False
        store.save_settings(settings)
        self.window = MainWindow(store=store, clipboard=Mock(), private_browser=True, open_on_start=False)
        for name in (
            "browser_keepalive_timer", "system_keepawake_timer", "browser_refresh_timer",
            "diagnostics_timer", "interaction_watchdog_timer", "response_followup_timer",
        ):
            getattr(self.window, name).stop()
        self.blocker = BlockStartupNetwork(self.window.profile)
        self.window.profile.setUrlRequestInterceptor(self.blocker)
        self.addCleanup(self._dispose_window)

    def _dispose_window(self):
        window = self.window
        window.exit_requested = True
        window.close()
        for widget in (window.browser, window.page, window.browser_background_host, window.translation_overlay, window.quick_chat_overlay):
            widget.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        window.profile.deleteLater()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def _first_show(self):
        # Nincs kézi resize, ismételt _show_browser, tálcázás vagy relayout.
        # Csak a normál első megjelenítés és a Qt layout-eseményei futnak.
        self.window.show()
        for _ in range(3):
            self.app.processEvents()

    def _assert_overlays_cover_content(self):
        window = self.window
        expected = window.content_surface.rect()
        self.assertEqual(window.content_edge.geometry(), expected, "A webnézet széle kezdeti gyermekméreten maradt.")
        self.assertEqual(window.drawer_panel.geometry(), expected, "A beállításréteg nem követi a szülő felületét.")
        self.assertTrue(window.content_edge.isVisible())
        self.assertIs(window.content_edge.parentWidget(), window.content_surface)
        self.assertIs(window.browser.parentWidget(), window.content_surface)
        self.assertTrue(expected.contains(window.browser.geometry()))
        self.assertLessEqual(expected.width() - window.browser.width(), 4)
        self.assertLessEqual(expected.height() - window.browser.height(), 4)

    def test_first_show_has_full_content_edge_without_restore_workaround(self):
        self._first_show()
        self.assertGreater(self.window.content_surface.width(), 640)
        self.assertGreater(self.window.content_surface.height(), 480)
        self._assert_overlays_cover_content()

    def test_parent_layout_change_updates_edge_without_main_window_resize(self):
        self._first_show()
        window = self.window
        original_window_rect = window.rect()
        original_surface_rect = window.content_surface.rect()
        # A fejléc layoutjának magassága változik; a főablak nem kap resize-ot.
        window.top_bar.setFixedHeight(window.top_bar.height() + 37)
        for _ in range(3):
            self.app.processEvents()
        self.assertEqual(window.rect(), original_window_rect)
        self.assertNotEqual(window.content_surface.rect(), original_surface_rect)
        self._assert_overlays_cover_content()


if __name__ == "__main__":
    unittest.main()
