"""A ChatGPT kezdőnézet és a beállítások regressziói, izolált profillal és hálózat nélkül."""
from __future__ import annotations

import os
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent, QPoint, QRect, Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from gamer_translator.main_window import MainWindow
from gamer_translator.settings_store import AppSettings, SettingsStore


class DesignInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.original_font = QFont(cls.app.font())
        font_directory = Path(os.environ.get("SystemRoot", "C:/Windows")) / "Fonts"
        cls.added_fonts = []
        # Az offscreen platformon is a valódi Windows betűméretek határozzák meg a minimumszélességeket.
        for name in ("segoeui.ttf", "segoeuib.ttf", "segoeuis.ttf"):
            font_id = QFontDatabase.addApplicationFont(str(font_directory / name))
            if font_id >= 0:
                cls.added_fonts.append(font_id)
        cls.app.setFont(QFont("Segoe UI", 10))

    @classmethod
    def tearDownClass(cls):
        cls.app.setFont(cls.original_font)
        for font_id in cls.added_fonts:
            QFontDatabase.removeApplicationFont(font_id)

    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        directory = self.stack.enter_context(tempfile.TemporaryDirectory(ignore_cleanup_errors=True))
        self.store = SettingsStore(root_dir=Path(directory))
        for name in (
            "open_chatgpt", "_register_hotkeys", "_unregister_hotkeys",
            "_install_keyboard_hook", "_uninstall_keyboard_hook",
            "_install_mouse_hook", "_uninstall_mouse_hook",
            "_build_tray_icon", "_refresh_system_keep_awake",
            "_restore_system_sleep_state", "_apply_native_window_theme",
            "_restart_application",
        ):
            self.stack.enter_context(patch.object(MainWindow, name))
        self.stack.enter_context(patch.object(MainWindow, "_current_clipboard_signature", return_value=""))
        self.clipboard = Mock()
        self.window = MainWindow(
            store=self.store, clipboard=self.clipboard,
            private_browser=True, open_on_start=False,
        )
        self.addCleanup(self._dispose_window)
        for name in (
            "browser_keepalive_timer", "system_keepawake_timer", "browser_refresh_timer",
            "diagnostics_timer", "interaction_watchdog_timer", "response_followup_timer",
        ):
            getattr(self.window, name).stop()
        for name in ("drawer_animation", "backdrop_animation"):
            animation = getattr(self.window, name, None)
            if animation is not None:
                animation.setDuration(0)
        self.window.show()
        self.app.processEvents()

    def _dispose_window(self):
        window = self.window
        window.exit_requested = True
        window.close()
        for widget in (
            window.browser, window.page, window.browser_background_host,
            window.translation_overlay, window.quick_chat_overlay,
        ):
            widget.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        window.profile.deleteLater()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def _settle(self):
        self.app.processEvents()
        QTest.qWait(1)
        self.app.processEvents()

    def _assert_inside(self, widget, parent):
        self.assertTrue(widget.isVisible(), widget.objectName() or type(widget).__name__)
        rectangle = QRect(widget.mapTo(parent, QPoint(0, 0)), widget.size())
        self.assertTrue(parent.rect().contains(rectangle), f"{widget.objectName()}: {rectangle} / {parent.rect()}")

    def test_settings_roundtrip_preserves_every_existing_option(self):
        examples = (
            AppSettings(
                monitoring_enabled=False, keep_chatgpt_in_background=False,
                game_mode_enabled=True, prompt_template="Egyéni magyar kézi prompt.",
                copy_response_to_clipboard=False, ocr_text_from_clipboard_image=False,
                webview_gpu_acceleration_enabled=False, nvidia_mouse_lag_fix_enabled=False,
                type_out_hotkey_enabled=False,
                type_out_hotkey="Ctrl+Alt+F8", screen_clip_hotkey_enabled=False,
                screen_clip_hotkey="Ctrl+Alt+F9", quick_chat_hotkey_enabled=False,
                quick_chat_hotkey="Ctrl+Alt+F10", overlay_opacity_percent=17,
                overlay_duration_seconds=73, page_ready_timeout_ms=43000,
            ),
            AppSettings(
                monitoring_enabled=True, keep_chatgpt_in_background=True,
                game_mode_enabled=False, prompt_template="Második próba, minden kapcsoló aktív.",
                copy_response_to_clipboard=True, ocr_text_from_clipboard_image=True,
                webview_gpu_acceleration_enabled=True, nvidia_mouse_lag_fix_enabled=True,
                type_out_hotkey_enabled=True,
                type_out_hotkey="Alt+V", screen_clip_hotkey_enabled=True,
                screen_clip_hotkey="Alt+C", quick_chat_hotkey_enabled=True,
                quick_chat_hotkey="Alt+X", overlay_opacity_percent=91,
                overlay_duration_seconds=119, page_ready_timeout_ms=110000,
            ),
        )
        for expected in examples:
            with self.subTest(active=expected.monitoring_enabled):
                self.window._apply_settings_to_form(expected)
                self.assertEqual(self.window._read_settings_from_form(), expected)
                self.window.save_settings_button.click()
                self._settle()
                self.assertEqual(SettingsStore(root_dir=self.store.root_dir).load_settings(), expected)

    def test_visible_setting_controls_change_the_saved_values(self):
        self.window.toggle_drawer()
        self._settle()
        initial = self.window.monitoring_enabled.isChecked()
        self.window.monitoring_enabled.click()
        self.window.prompt_template.setPlainText("Az új felületből mentett prompt.")
        self.window.type_out_hotkey.set_hotkey_value("Ctrl+Alt+F8")
        self.window.overlay_opacity_slider.setValue(63)
        self.window.overlay_duration_seconds.setValue(47)
        self.window.save_settings_button.click()
        saved = SettingsStore(root_dir=self.store.root_dir).load_settings()
        self.assertEqual(saved.monitoring_enabled, not initial)
        self.assertEqual(saved.prompt_template, "Az új felületből mentett prompt.")
        self.assertEqual(saved.type_out_hotkey, "Ctrl+Alt+F8")
        self.assertEqual(saved.overlay_opacity_percent, 63)
        self.assertEqual(saved.overlay_duration_seconds, 47)
        self.assertEqual(self.window.overlay_opacity_value_label.text(), "63%")

    def test_nvidia_fix_change_is_saved_before_restart_and_defaults_restore_it(self):
        self.window.nvidia_mouse_lag_fix_enabled.setChecked(False)
        self.window._restart_application.side_effect = lambda: self.assertFalse(
            SettingsStore(root_dir=self.store.root_dir).load_settings().nvidia_mouse_lag_fix_enabled
        )
        self.window.save_settings_button.click()
        self.window._restart_application.assert_called_once_with()
        self.window._restart_application.reset_mock()
        self.window._restart_application.side_effect = lambda: self.assertTrue(
            SettingsStore(root_dir=self.store.root_dir).load_settings().nvidia_mouse_lag_fix_enabled
        )
        self.window.reset_defaults_button.click()
        self.assertTrue(self.window.nvidia_mouse_lag_fix_enabled.isChecked())
        self.window._restart_application.assert_called_once_with()

    def test_unchanged_nvidia_fix_does_not_restart_on_save(self):
        self.window.save_settings_button.click()
        self.window._restart_application.assert_not_called()

    def test_user_restart_starts_a_new_driver_configuration_cycle(self):
        executable = self.store.root_dir / "Gamer Translator.exe"
        executable.touch()
        with patch("gamer_translator.main_window.sys.frozen", True, create=True), \
                patch("gamer_translator.main_window.sys.argv", [str(executable), "--nvidia-compat-restarted"]):
            self.assertEqual(self.window._build_restart_command(), [str(executable.resolve())])

    def test_initial_content_is_the_full_width_chatgpt_browser(self):
        self.assertFalse(self.window.drawer_open)
        self.assertFalse(self.window.drawer_panel.isVisible())
        self.assertTrue(self.window.browser.isVisible())
        self.assertIs(self.window.browser.parentWidget(), self.window.content_surface)
        self.assertEqual(self.window.content_layout.indexOf(self.window.browser), 0)
        self._assert_inside(self.window.browser, self.window.content_surface)
        margins = self.window.content_layout.contentsMargins()
        content_rect = self.window.content_surface.contentsRect()
        self.assertEqual(self.window.browser.x(), content_rect.x() + margins.left())
        self.assertEqual(
            self.window.browser.width(),
            content_rect.width() - margins.left() - margins.right(),
        )
        # A fő tartalomsor egyetlen eleme a webnézet gazdája; nincs oldalsávnyi üres hely.
        body = self.window.content_surface.parentWidget()
        self.assertEqual(body.layout().count(), 1)
        self.assertIs(body.layout().itemAt(0).widget(), self.window.content_surface)
        body_margins = body.layout().contentsMargins()
        self.assertEqual(self.window.content_surface.x(), body_margins.left())
        self.assertEqual(
            self.window.content_surface.width(),
            body.width() - body_margins.left() - body_margins.right(),
        )
        self.assertTrue(self.window.profile.isOffTheRecord())
        self.window.open_chatgpt.assert_not_called()

    def test_removed_navigation_and_custom_home_controls_are_not_created(self):
        for attribute in (
            "sidebar", "nav_buttons", "home_panel", "home_composer", "home_input",
            "home_send_button", "home_attach_button", "home_voice_button",
            "suggestion_cards", "chat_tab_button", "work_tab_button",
        ):
            with self.subTest(attribute=attribute):
                self.assertFalse(hasattr(self.window, attribute))

    def test_origin_is_internal_and_does_not_occupy_the_visible_layout(self):
        self.assertTrue(self.window.current_url_label.isHidden())
        self.assertFalse(self.window.current_url_label.isVisible())
        self.assertIs(self.window.current_url_label.parentWidget(), self.window.centralWidget())
        self.assertEqual(self.window.centralWidget().layout().indexOf(self.window.current_url_label), -1)
        self.window.menu_button.click()
        self._settle()
        self.assertTrue(self.window.current_url_label.isHidden())
        self.window.close_drawer_button.click()
        self._settle()
        self.assertTrue(self.window.current_url_label.isHidden())

    def test_chatgpt_header_button_returns_to_browser_and_uses_existing_open_action(self):
        self.window.menu_button.click()
        self._settle()
        self.assertTrue(self.window.drawer_open)
        self.window.open_chatgpt.reset_mock()
        self.window.open_chatgpt_button.click()
        self._settle()
        self.window.open_chatgpt.assert_called_once_with(show_error_dialog=True)
        self.assertFalse(self.window.drawer_open)
        self.assertFalse(self.window.drawer_panel.isVisible())
        self.assertTrue(self.window.browser.isVisible())
        focused = self.app.focusWidget()
        self.assertIsNotNone(focused)
        self.assertTrue(focused is self.window.browser or self.window.browser.isAncestorOf(focused))

    def test_settings_close_and_escape_return_to_browser(self):
        for close_with_escape in (False, True):
            with self.subTest(escape=close_with_escape):
                self.window.menu_button.click()
                self._settle()
                self.assertTrue(self.window.drawer_open)
                self.assertTrue(self.window.drawer_panel.isVisible())
                if close_with_escape:
                    QTest.keyClick(self.window.close_drawer_button, Qt.Key.Key_Escape)
                else:
                    self.window.close_drawer_button.click()
                self._settle()
                self.assertFalse(self.window.drawer_open)
                self.assertFalse(self.window.drawer_panel.isVisible())
                self.assertTrue(self.window.browser.isVisible())
                self.assertEqual(self.window.browser.focusPolicy(), Qt.FocusPolicy.StrongFocus)

    def test_tab_focus_never_enters_a_covered_browser_and_returns_when_opened(self):
        self.window._set_drawer_open(True)
        self.window.close_drawer_button.setFocus()
        self._settle()
        self.assertEqual(self.window.browser.focusPolicy(), Qt.FocusPolicy.NoFocus)
        proxy = self.window.browser.focusProxy()
        if proxy is not None:
            self.assertEqual(proxy.focusPolicy(), Qt.FocusPolicy.NoFocus)
        for step in range(70):
            target = self.app.focusWidget() or self.window
            QTest.keyClick(target, Qt.Key.Key_Tab)
            self.app.processEvents()
            focused = self.app.focusWidget()
            self.assertIsNotNone(focused, f"Tab-lépés: {step}")
            self.assertFalse(
                focused is self.window.browser or self.window.browser.isAncestorOf(focused),
                f"A fedett böngésző fókuszt kapott, Tab-lépés: {step}",
            )
        self.window._show_browser()
        self._settle()
        self.assertEqual(self.window.browser.focusPolicy(), Qt.FocusPolicy.StrongFocus)
        focused = self.app.focusWidget()
        self.assertIsNotNone(focused)
        self.assertTrue(focused is self.window.browser or self.window.browser.isAncestorOf(focused))

    def test_background_browser_returns_to_full_width_content_without_a_home_overlay(self):
        for settings_open in (False, True):
            with self.subTest(settings=settings_open):
                self.window._set_drawer_open(settings_open)
                self.window.hide()
                self._settle()
                self.assertTrue(self.window.browser_background_mode)
                self.assertIs(self.window.browser.parentWidget(), self.window.browser_background_host)
                self.window.show()
                self._settle()
                self.assertFalse(self.window.browser_background_mode)
                self.assertFalse(self.window.browser_background_host.isVisible())
                self.assertIs(self.window.browser.parentWidget(), self.window.content_surface)
                self.assertEqual(self.window.content_layout.indexOf(self.window.browser), 0)
                self.assertEqual(self.window.drawer_panel.isVisible(), settings_open)
                if settings_open:
                    self.assertEqual(self.window.browser.focusPolicy(), Qt.FocusPolicy.NoFocus)
                    self.window.close_drawer_button.click()
                    self._settle()
                self.assertTrue(self.window.browser.isVisible())
                self.assertEqual(self.window.browser.focusPolicy(), Qt.FocusPolicy.StrongFocus)
                self._assert_inside(self.window.browser, self.window.content_surface)

    def test_minimum_window_keeps_header_actions_and_settings_accessible(self):
        self.window.resize(1080, 720)
        self._settle()
        self._assert_inside(self.window.browser, self.window.content_surface)
        for control in (
            self.window.open_chatgpt_button, self.window.menu_button,
            self.window.send_prompt_now_button,
        ):
            self._assert_inside(control, self.window.top_bar)
        self.window.toggle_drawer()
        self._settle()
        self._assert_inside(self.window.settings_footer, self.window.drawer_panel)
        self._assert_inside(self.window.save_settings_button, self.window.settings_footer)
        self._assert_inside(self.window.reset_defaults_button, self.window.settings_footer)
        for card in (
            self.window.general_settings_card, self.window.hotkey_settings_card,
            self.window.overlay_settings_card,
        ):
            self.window.drawer_scroll.ensureWidgetVisible(card)
            self._settle()
            rectangle = QRect(card.mapTo(self.window.drawer_scroll.viewport(), QPoint(0, 0)), card.size())
            self.assertTrue(self.window.drawer_scroll.viewport().rect().intersects(rectangle))

    def test_compact_settings_need_no_horizontal_scroll_and_fields_are_fully_reachable(self):
        self.window.resize(1080, 720)
        self.window._set_drawer_open(True)
        self._settle()
        scroll = self.window.drawer_scroll
        self.assertEqual(scroll.horizontalScrollBar().maximum(), 0)
        for field in (
            self.window.prompt_template, self.window.nvidia_mouse_lag_fix_enabled,
            self.window.screen_clip_hotkey,
            self.window.type_out_hotkey, self.window.quick_chat_hotkey,
            self.window.overlay_opacity_slider, self.window.overlay_duration_seconds,
        ):
            with self.subTest(field=field.objectName() or type(field).__name__):
                # Minden célmező elérhetőségét ugyanabból a kiinduló pozícióból ellenőrizzük.
                scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().minimum())
                scroll.ensureWidgetVisible(field)
                self._settle()
                self._assert_inside(field, scroll.viewport())
                self.assertEqual(scroll.horizontalScrollBar().maximum(), 0)


if __name__ == "__main__":
    unittest.main()
