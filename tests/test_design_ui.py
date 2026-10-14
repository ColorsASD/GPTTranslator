"""A referenciafelület működési regressziói, izolált profillal és hálózat nélkül."""
from __future__ import annotations

import os
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent, QPoint, QRect, Qt
from PySide6.QtGui import QAction, QFont, QFontDatabase
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from gamer_translator import main_window as module
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
        self.window._show_home()
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
                webview_gpu_acceleration_enabled=False, type_out_hotkey_enabled=False,
                type_out_hotkey="Ctrl+Alt+F8", screen_clip_hotkey_enabled=False,
                screen_clip_hotkey="Ctrl+Alt+F9", quick_chat_hotkey_enabled=False,
                quick_chat_hotkey="Ctrl+Alt+F10", overlay_opacity_percent=17,
                overlay_duration_seconds=73, page_ready_timeout_ms=43000,
            ),
            AppSettings(
                monitoring_enabled=True, keep_chatgpt_in_background=True,
                game_mode_enabled=False, prompt_template="Második próba, minden kapcsoló aktív.",
                copy_response_to_clipboard=True, ocr_text_from_clipboard_image=True,
                webview_gpu_acceleration_enabled=True, type_out_hotkey_enabled=True,
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

    def test_home_chat_send_button_sends_raw_text_once(self):
        with patch.object(self.window, "_send_home_prompt") as send, patch.object(
            self.window, "_process_quick_chat_translation"
        ) as translate:
            self.window.chat_tab_button.click()
            self.window.home_input.setText("  Miben különbözik a két fegyver?  ")
            self.window.home_send_button.click()
            send.assert_called_once_with("Miben különbözik a két fegyver?")
            translate.assert_not_called()

    def test_home_work_enter_uses_the_existing_translation_path(self):
        with patch.object(self.window, "_send_home_prompt") as send, patch.object(
            self.window, "_process_quick_chat_translation"
        ) as translate:
            self.window.work_tab_button.click()
            self.window.home_input.setText("  Cover me, I am reloading!  ")
            QTest.keyClick(self.window.home_input, Qt.Key.Key_Return)
            translate.assert_called_once_with("Cover me, I am reloading!")
            send.assert_not_called()

    def test_successful_work_delivery_opens_the_browser_before_translation_and_clears_text(self):
        self.window.work_tab_button.click()
        self.window.home_input.setText("Cover me, I am reloading!")

        def complete_translation(_text):
            self.assertFalse(self.window.home_panel.isVisible())
            self.assertTrue(self.window.browser.isVisible())
            self.assertFalse(self.window.home_send_button.isEnabled())
            self.window.latest_translation_request_id = "work-success"
            self.window.translation_result_request_id = "work-success"
            self.window.translation_result_complete = True

        with patch.object(self.window, "_process_quick_chat_translation", side_effect=complete_translation) as translate:
            self.window.home_send_button.click()
        translate.assert_called_once_with("Cover me, I am reloading!")
        self.assertEqual(self.window.home_input.text(), "")
        self.assertFalse(self.window.home_panel.isVisible())
        self.assertTrue(self.window.home_send_button.isEnabled())

    def test_failed_or_stale_work_result_keeps_the_source_text_for_retry(self):
        for completed, result_id in ((False, "work-current"), (True, "work-previous")):
            with self.subTest(completed=completed, result=result_id):
                self.window._show_home()
                self.window.work_tab_button.click()
                self.window.home_input.setText("Ezt a forrásszöveget őrizd meg.")

                def unsuccessful_translation(_text):
                    self.window.latest_translation_request_id = "work-current"
                    self.window.translation_result_request_id = result_id
                    self.window.translation_result_complete = completed

                with patch.object(self.window, "_process_quick_chat_translation", side_effect=unsuccessful_translation):
                    self.window.home_send_button.click()
                self.assertEqual(self.window.home_input.text(), "Ezt a forrásszöveget őrizd meg.")
                self.assertTrue(self.window.home_send_button.isEnabled())
                self.window._show_home()
                self.assertEqual(self.window.home_input.text(), "Ezt a forrásszöveget őrizd meg.")

    def test_empty_home_input_never_sends_in_either_mode(self):
        with patch.object(self.window, "_send_home_prompt") as send, patch.object(
            self.window, "_process_quick_chat_translation"
        ) as translate:
            for tab in (self.window.chat_tab_button, self.window.work_tab_button):
                tab.click()
                self.window.home_input.setText("   ")
                self.window.home_send_button.click()
                QTest.keyClick(self.window.home_input, Qt.Key.Key_Return)
            send.assert_not_called()
            translate.assert_not_called()

    def test_suggestion_cards_prepare_translation_or_fill_an_unsent_question(self):
        self.assertEqual(len(self.window.suggestion_cards), 4)
        with patch.object(self.window, "_send_home_prompt") as send, patch.object(
            self.window, "_process_quick_chat_translation"
        ) as translate:
            texts = []
            for index, card in enumerate(self.window.suggestion_cards):
                with self.subTest(index=index):
                    self.window.home_input.clear()
                    card.click()
                    self._settle()
                    self.assertEqual(self.window._home_mode, "work" if index == 0 else "chat")
                    self.assertTrue(self.window.home_input.hasFocus())
                    if index == 0:
                        self.assertEqual(self.window.home_input.text(), "")
                        self.assertIn("fordítandó", self.window.home_input.placeholderText())
                    else:
                        self.assertTrue(self.window.home_input.text().strip())
                        texts.append(self.window.home_input.text())
            self.assertEqual(len(set(texts)), 3)
            send.assert_not_called()
            translate.assert_not_called()

    def test_busy_home_submission_keeps_text_and_does_not_start_another_operation(self):
        with patch.object(self.window, "_send_home_prompt") as send, patch.object(
            self.window, "_process_quick_chat_translation"
        ) as translate:
            for tab in (self.window.chat_tab_button, self.window.work_tab_button):
                tab.click()
                for busy_attribute in ("browser_interaction_active", "clipboard_translation_in_progress"):
                    with self.subTest(mode=self.window._home_mode, busy=busy_attribute):
                        self.window.home_input.setText("  Ezt még el szeretném küldeni.  ")
                        setattr(self.window, busy_attribute, True)
                        try:
                            self.window.home_send_button.click()
                            QTest.keyClick(self.window.home_input, Qt.Key.Key_Return)
                            self.assertEqual(self.window.home_input.text(), "  Ezt még el szeretném küldeni.  ")
                            self.assertTrue(self.window.home_panel.isVisible())
                            self.assertIn("Már fut", self.window.top_status_label.text())
                        finally:
                            setattr(self.window, busy_attribute, False)
            send.assert_not_called()
            translate.assert_not_called()

    def test_failed_home_delivery_keeps_the_input_and_the_home_page(self):
        self.window.chat_tab_button.click()
        self.window.home_input.setText("A sikertelenül küldött kérdésem.")
        with patch.object(self.window, "_ensure_chatgpt_page_loaded"), patch.object(
            self.window, "_ensure_automation_ready"
        ), patch.object(self.window, "_execute_delivery", side_effect=RuntimeError("Szimulált küldési hiba.")), patch.object(
            self.window, "_show_browser"
        ) as show_browser:
            self.window.home_send_button.click()
            self._settle()
        show_browser.assert_not_called()
        self.assertEqual(self.window.home_input.text(), "A sikertelenül küldött kérdésem.")
        self.assertTrue(self.window.home_panel.isVisible())
        self.assertTrue(self.window.home_send_button.isEnabled())
        self.assertFalse(self.window.browser_interaction_active)
        self.assertIn("Szimulált küldési hiba.", self.window.top_status_label.text())

    def test_attachment_menu_action_invokes_the_existing_capture_path(self):
        action = QAction("Képkivágás fordítása", self.window)
        menu = Mock()
        menu.addAction.return_value = action
        menu.exec.side_effect = lambda _position: action.trigger()
        capture = Mock()

        # A natív QMenu.exec helyett a menü adaptere választ, de a QAction valódi Qt jelet küld.
        with patch.object(self.window, "_trigger_screen_clip_hotkey", new=lambda: capture()), patch.object(
            module, "QMenu", return_value=menu
        ):
            self.window.home_attach_button.click()
        menu.addAction.assert_called_once_with("Képkivágás fordítása")
        menu.exec.assert_called_once()
        capture.assert_called_once_with()

    def test_general_home_delivery_does_not_add_translation_instructions(self):
        with patch.object(self.window, "_ensure_chatgpt_page_loaded"), patch.object(
            self.window, "_ensure_automation_ready"
        ), patch.object(self.window, "_execute_delivery", return_value={}) as deliver:
            self.window._send_home_prompt("Adj három stratégiai tippet.")
        deliver.assert_called_once()
        payload = deliver.call_args.args[0]
        self.assertEqual(payload["prompt"], "Adj három stratégiai tippet.")
        self.assertTrue(payload["autoSubmit"])
        self.assertFalse(payload["waitForResponse"])

    def test_settings_close_returns_to_the_previous_content(self):
        for initial_view in ("home", "browser"):
            with self.subTest(view=initial_view):
                if initial_view == "home":
                    self.window._show_home()
                else:
                    self.window._show_browser()
                self.window.menu_button.click()
                self._settle()
                self.assertTrue(self.window.drawer_open)
                self.assertTrue(self.window.drawer_panel.isVisible())
                self.window.close_drawer_button.click()
                self._settle()
                self.assertFalse(self.window.drawer_open)
                self.assertFalse(self.window.drawer_panel.isVisible())
                self.assertEqual(self.window.home_panel.isVisible(), initial_view == "home")

    def test_tab_focus_never_enters_a_covered_browser_and_returns_when_opened(self):
        for section in ("home", "settings"):
            with self.subTest(section=section):
                if section == "home":
                    self.window._show_home()
                    self.window.home_input.setFocus()
                else:
                    # A beállítások az aktív böngésző fölött nyílnak meg.
                    self.window._show_browser()
                    self.window._set_drawer_open(True)
                    self.window.close_drawer_button.setFocus()
                self._settle()
                for step in range(70):
                    target = self.app.focusWidget() or self.window
                    QTest.keyClick(target, Qt.Key.Key_Tab)
                    self.app.processEvents()
                    focused = self.app.focusWidget()
                    self.assertIsNotNone(focused, f"{section}, Tab-lépés: {step}")
                    self.assertFalse(
                        focused is self.window.browser or self.window.browser.isAncestorOf(focused),
                        f"A fedett böngésző fókuszt kapott: {section}, Tab-lépés: {step}",
                    )
        self.window._show_browser()
        self._settle()
        focused = self.app.focusWidget()
        self.assertIsNotNone(focused)
        self.assertTrue(focused is self.window.browser or self.window.browser.isAncestorOf(focused))

    def test_every_sidebar_button_dispatches_its_section(self):
        self.assertEqual(set(self.window.nav_buttons), {"home", "history", "discover", "profile", "settings"})
        with patch.object(self.window, "_navigate_shell") as navigate:
            for section, button in self.window.nav_buttons.items():
                with self.subTest(section=section):
                    navigate.reset_mock()
                    button.click()
                    navigate.assert_called_once_with(section)

    def test_sidebar_navigation_has_working_destinations(self):
        self.window.nav_buttons["settings"].click()
        self._settle()
        self.assertTrue(self.window.drawer_open)
        self.window.nav_buttons["home"].click()
        self._settle()
        self.assertFalse(self.window.drawer_open)
        self.assertTrue(self.window.home_panel.isVisible())
        for section in ("history", "profile"):
            with self.subTest(section=section):
                self.window.open_chatgpt.reset_mock()
                self.window.nav_buttons[section].click()
                self._settle()
                self.window.open_chatgpt.assert_called_once()
                self.assertFalse(self.window.home_panel.isVisible())
        self.window.nav_buttons["discover"].click()
        self._settle()
        self.assertTrue(self.window.home_panel.isVisible())
        self.assertFalse(self.window.drawer_open)

    def test_voice_control_opens_the_real_chatgpt_page(self):
        self.window.open_chatgpt.reset_mock()
        self.window.home_voice_button.click()
        self._settle()
        self.window.open_chatgpt.assert_called_once()
        self.assertFalse(self.window.home_panel.isVisible())

    def test_minimum_window_keeps_primary_actions_accessible(self):
        self.window.resize(1080, 720)
        self.window._show_home()
        self._settle()
        for widget in (
            self.window.home_input, self.window.home_send_button,
            self.window.home_attach_button, self.window.home_voice_button,
            *self.window.suggestion_cards,
        ):
            self._assert_inside(widget, self.window.home_panel)
        for button in self.window.nav_buttons.values():
            self._assert_inside(button, self.window.centralWidget())
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
            self.window.prompt_template, self.window.screen_clip_hotkey,
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
