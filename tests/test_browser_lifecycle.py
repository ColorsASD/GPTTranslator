"""A háttérlap takarékos készenléte és a műveletek ébresztése, éles profil nélkül."""
from __future__ import annotations

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWidgets import QApplication

from gamer_translator import main_window as module
from gamer_translator.main_window import BrowserOperationCancelled, MainWindow
from gamer_translator.settings_store import AppSettings


ACTIVE = QWebEnginePage.LifecycleState.Active
FROZEN = QWebEnginePage.LifecycleState.Frozen


class BrowserPowerLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.events = []
        page = Mock()
        page.lifecycleState.return_value = ACTIVE
        page.isVisible.return_value = True
        page.recommendedState.return_value = FROZEN

        def lifecycle(state):
            # A Qt egy látható oldal fagyasztását elutasítja.
            if state == FROZEN and page.isVisible():
                raise AssertionError("A látható oldal nem fagyasztható.")
            page.lifecycleState.return_value = state
            self.events.append(("lifecycle", state))

        def visibility(visible):
            page.isVisible.return_value = visible
            self.events.append(("visibility", visible))

        page.setLifecycleState.side_effect = lifecycle
        page.setVisible.side_effect = visibility
        browser = Mock()
        browser.page.return_value = page
        browser.url.return_value = QUrl("https://chatgpt.com/")
        browser.isVisible.return_value = True
        browser.updatesEnabled.return_value = True
        browser.setUpdatesEnabled.side_effect = lambda value: setattr(browser.updatesEnabled, "return_value", value)
        browser.show.side_effect = lambda: setattr(browser.isVisible, "return_value", True)
        browser.hide.side_effect = lambda: setattr(browser.isVisible, "return_value", False)
        refresh_timer = Mock()
        refresh_timer.isActive.return_value = True
        refresh_timer.stop.side_effect = lambda: setattr(refresh_timer.isActive, "return_value", False)
        refresh_timer.start.side_effect = lambda: setattr(refresh_timer.isActive, "return_value", True)
        host = Mock()
        host.isVisible.return_value = True
        host.show.side_effect = lambda: setattr(host.isVisible, "return_value", True)
        host.hide.side_effect = lambda: setattr(host.isVisible, "return_value", False)

        self.window = SimpleNamespace(
            browser=browser, page=page, settings=AppSettings(), browser_background_host=host,
            browser_background_mode=True, browser_interaction_active=False, page_loading=False,
            clipboard_translation_in_progress=False, response_followup_progress_call_id="",
            response_followup_timer=Mock(), current_browser_refresh_interval_ms=250,
            browser_refresh_timer=refresh_timer, frame_pulse_dot=Mock(), frame_pulse_state=False,
            isVisible=Mock(return_value=False), isMinimized=Mock(return_value=False),
            _is_window_hidden_for_tray=Mock(return_value=True),
            _sync_browser_host_mode=Mock(), _sync_browser_placeholder=Mock(),
            _touch_browser_interaction_heartbeat=Mock(), _run_javascript=Mock(return_value=True),
            _is_chatgpt_url=lambda value: MainWindow._is_chatgpt_url(None, value),
            automation_script="offline automation", automation_ready=False,
            active_translation_request_id="1" * 32, latest_translation_request_id="1" * 32,
            last_translated_text="", _wait_for_page_load=Mock(),
        )
        for name in (
            "_sync_browser_runtime_state", "_target_browser_refresh_interval_ms",
            "_update_browser_refresh_timer", "_should_run_browser_keepalive",
            "_stop_response_followup_polling", "_start_response_followup_polling",
        ):
            setattr(self.window, name, getattr(MainWindow, name).__get__(self.window, SimpleNamespace))

    def assert_suspended(self):
        window = self.window
        self.assertEqual(window.page.lifecycleState(), FROZEN)
        self.assertFalse(window.page.isVisible())
        self.assertFalse(window.browser.updatesEnabled())
        self.assertFalse(window.browser.isVisible())
        self.assertFalse(window.browser_background_host.isVisible())
        self.assertFalse(window.browser_refresh_timer.isActive())

    def assert_active(self):
        window = self.window
        self.assertEqual(window.page.lifecycleState(), ACTIVE)
        self.assertTrue(window.page.isVisible())
        self.assertTrue(window.browser.updatesEnabled())
        self.assertTrue(window.browser.isVisible())

    def test_idle_background_suspends_in_both_game_modes(self):
        for game_mode in (False, True):
            with self.subTest(game_mode=game_mode):
                self.window.settings.game_mode_enabled = game_mode
                self.window._sync_browser_runtime_state()
                self.assert_suspended()
        self.assertLess(self.events.index(("visibility", False)), self.events.index(("lifecycle", FROZEN)))

    def test_hidden_media_stays_active_without_background_rendering_then_suspends(self):
        page = self.window.page
        page.recommendedState.return_value = ACTIVE
        self.window._sync_browser_runtime_state()
        self.assertEqual(page.lifecycleState(), ACTIVE)
        self.assertFalse(page.isVisible())
        self.assertFalse(self.window.browser.updatesEnabled())
        self.assertFalse(self.window.browser_background_host.isVisible())
        self.assertFalse(self.window.browser_refresh_timer.isActive())
        page.recommendedState.return_value = FROZEN
        self.window._sync_browser_runtime_state()
        self.assert_suspended()

    def test_media_recommendation_is_read_after_page_becomes_hidden(self):
        def recommendation():
            self.assertFalse(self.window.page.isVisible())
            return ACTIVE

        self.window.page.recommendedState.side_effect = recommendation
        self.window._sync_browser_runtime_state()
        self.assertEqual(self.window.page.lifecycleState(), ACTIVE)
        self.assertFalse(self.window.page.isVisible())

    def test_incoming_translation_wakes_and_completion_suspends(self):
        self.window._sync_browser_runtime_state()
        MainWindow._begin_browser_interaction(self.window)
        self.assert_active()
        self.assertTrue(self.window.browser_refresh_timer.isActive())
        self.window._run_javascript.side_effect = lambda *_args, **_kwargs: self.assert_active()
        self.window._run_javascript("offline delivery", timeout_ms=1000)
        MainWindow._end_browser_interaction(self.window)
        self.assert_suspended()

    def test_page_load_and_clipboard_processing_keep_hidden_page_active(self):
        for name in ("page_loading", "clipboard_translation_in_progress"):
            with self.subTest(work=name):
                setattr(self.window, name, True)
                self.window._sync_browser_runtime_state()
                self.assert_active()
                setattr(self.window, name, False)
                self.window._sync_browser_runtime_state()
                self.assert_suspended()

    def test_restore_to_foreground_resumes_without_manual_repaint_timer(self):
        self.window._sync_browser_runtime_state()
        self.window.browser_background_mode = False
        self.window.isVisible.return_value = True
        self.window._is_window_hidden_for_tray.return_value = False
        self.window._sync_browser_runtime_state()
        self.assert_active()
        self.assertFalse(self.window.browser_refresh_timer.isActive())
        MainWindow._refresh_browser_view(self.window)
        self.window.browser.update.assert_not_called()

    def test_idle_timeout_neither_pulses_nor_updates_background_surfaces(self):
        self.window._sync_browser_runtime_state()
        MainWindow._refresh_browser_view(self.window)
        self.window.frame_pulse_dot.setStyleSheet.assert_not_called()
        self.window.frame_pulse_dot.repaint.assert_not_called()
        self.window.browser.update.assert_not_called()
        self.window.browser_background_host.update.assert_not_called()

    def test_periodic_keepalive_cannot_wake_an_idle_frozen_page(self):
        self.window.settings.game_mode_enabled = False
        self.window._sync_browser_runtime_state()
        self.window._sync_browser_host_mode.reset_mock()
        MainWindow._perform_browser_keepalive(self.window)
        self.window._run_javascript.assert_not_called()
        self.window._sync_browser_host_mode.assert_not_called()
        self.assert_suspended()

    def test_automation_probe_and_injection_finish_before_hidden_page_freezes(self):
        observed = []
        results = iter((False, None, True))

        def javascript(*_args, **_kwargs):
            self.assert_active()
            # A JS-várakozás újrabelépő eseményhurka sem fagyaszthat közben.
            self.window._sync_browser_runtime_state()
            self.assert_active()
            observed.append("javascript")
            return next(results)

        self.window._sync_browser_runtime_state()
        self.window._run_javascript.side_effect = javascript
        MainWindow._ensure_automation_ready(self.window)
        self.assertEqual(observed, ["javascript"] * 3)
        self.assertTrue(self.window.automation_ready)
        self.assertFalse(self.window.browser_automation_initializing)
        self.assert_suspended()

    def test_failed_automation_initialization_returns_to_suspended_state(self):
        self.window._run_javascript.side_effect = RuntimeError("Offline próbahiba")
        with self.assertRaisesRegex(RuntimeError, "Offline"):
            MainWindow._ensure_automation_ready(self.window)
        self.assertFalse(self.window.browser_automation_initializing)
        self.assert_suspended()

    def test_response_followup_survives_delivery_end_and_cleans_before_freezing(self):
        MainWindow._begin_browser_interaction(self.window)
        self.window._start_response_followup_polling("offline-followup", Mock())
        MainWindow._end_browser_interaction(self.window)
        self.assert_active()
        self.assertTrue(self.window.browser_refresh_timer.isActive())

        def cleanup(*_args, **_kwargs):
            self.window._sync_browser_runtime_state()
            self.assert_active()
            self.events.append(("cleanup", True))
            return True

        self.window._run_javascript.side_effect = cleanup
        self.window._stop_response_followup_polling()
        self.assert_suspended()
        cleanup_index = self.events.index(("cleanup", True))
        self.assertEqual(self.events[-1], ("lifecycle", FROZEN))
        self.assertLess(cleanup_index, len(self.events) - 1)

    def test_final_followup_is_delivered_while_active_then_suspends(self):
        observed = []
        handler = lambda progress: observed.append(("delivered", self.window.page.lifecycleState(), progress["text"]))
        self.window._start_response_followup_polling("offline-followup", handler)
        progress = {"kind": "assistant_response", "text": "Végleges válasz", "done": True, "complete": True, "seq": 1}

        def javascript(script, **_kwargs):
            self.assert_active()
            if "return JSON.stringify" in script:
                return json.dumps({"progress": json.dumps(progress), "diagnostics": []})
            observed.append(("cleanup", self.window.page.lifecycleState()))
            return True

        self.window._run_javascript.side_effect = javascript
        MainWindow._poll_response_followup_progress(self.window)
        self.assertEqual(observed, [("delivered", ACTIVE, "Végleges válasz"), ("cleanup", ACTIVE)])
        self.assertEqual(self.window.response_followup_progress_call_id, "")
        self.assert_suspended()

    def test_followup_and_initialization_get_a_host_without_keepalive_setting(self):
        self.window.settings.keep_chatgpt_in_background = False
        self.assertFalse(MainWindow._should_use_background_browser_host(self.window))
        self.window.response_followup_progress_call_id = "offline-followup"
        self.assertTrue(MainWindow._should_use_background_browser_host(self.window))
        self.window.response_followup_progress_call_id = ""
        self.window.browser_automation_initializing = True
        self.assertTrue(MainWindow._should_use_background_browser_host(self.window))


class CancellationSignals(QObject):
    cancelled = Signal()


class DelayedBrowser(QObject):
    loadFinished = Signal(bool)

    def __init__(self, window, url):
        super().__init__()
        self.window = window
        self.current_url = QUrl(url)
        self.finished = False

    def url(self):
        return self.current_url

    def load(self, url):
        self.current_url = url
        QTimer.singleShot(10, self.finish)

    def reload(self):
        QTimer.singleShot(10, self.finish)

    def finish(self):
        self.finished = True
        self.window.page_loading = False
        self.loadFinished.emit(True)


class BrowserLoadCancellationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_navigation_waits_when_load_started_is_still_queued(self):
        for url, reload in (("about:blank", False), ("https://chatgpt.com/", True)):
            with self.subTest(url=url):
                window = SimpleNamespace(
                    settings=SimpleNamespace(page_ready_timeout_ms=100),
                    page_loading=False, browser_interaction_active=False,
                    clipboard_translation_in_progress=False, _set_live_status=Mock(),
                    _is_chatgpt_url=lambda u: MainWindow._is_chatgpt_url(None, u),
                )
                window.browser = DelayedBrowser(window, url)
                window._wait_for_page_load = lambda timeout: MainWindow._wait_for_page_load(window, timeout)
                MainWindow._ensure_chatgpt_page_loaded(window, reload_if_open=reload)
                self.assertTrue(window.browser.finished)
                self.assertFalse(window.page_loading)

    def test_close_cancels_pending_javascript_without_timeout_error(self):
        signal = CancellationSignals()
        browser = Mock()
        browser.url.return_value = QUrl("https://chatgpt.com/")
        window = SimpleNamespace(
            browser=browser, operations_cancelled=False,
            browser_operations_cancelled=signal.cancelled,
            browser_interaction_active=False, clipboard_translation_in_progress=False,
            _is_chatgpt_url=lambda u: MainWindow._is_chatgpt_url(None, u),
        )

        def cancel():
            window.operations_cancelled = True
            signal.cancelled.emit()

        QTimer.singleShot(10, cancel)
        with patch.object(module, "log_event") as log, self.assertRaises(BrowserOperationCancelled):
            MainWindow._run_javascript(window, "42", timeout_ms=2000)
        log.assert_not_called()
        self.assertTrue(window.operations_cancelled)

    def test_close_cancels_pending_navigation(self):
        signal = CancellationSignals()
        window = SimpleNamespace(
            page_loading=True, operations_cancelled=False,
            browser_operations_cancelled=signal.cancelled,
            browser_interaction_active=False, clipboard_translation_in_progress=False,
        )
        window.browser = DelayedBrowser(window, "https://chatgpt.com/")

        def cancel():
            window.operations_cancelled = True
            signal.cancelled.emit()

        QTimer.singleShot(10, cancel)
        with self.assertRaises(BrowserOperationCancelled):
            MainWindow._wait_for_page_load(window, 2000)

    def test_cancelled_operations_do_not_start_new_javascript(self):
        window = SimpleNamespace(operations_cancelled=True, browser=Mock())
        with self.assertRaises(BrowserOperationCancelled):
            MainWindow._run_javascript(window, "42", timeout_ms=2000)
        window.browser.page.assert_not_called()

    def test_cancelled_operations_do_not_start_navigation_or_reload(self):
        for url in ("about:blank", "https://chatgpt.com/"):
            with self.subTest(url=url):
                window = SimpleNamespace(operations_cancelled=True, browser=Mock())
                window.browser.url.return_value = QUrl(url)
                with self.assertRaises(BrowserOperationCancelled):
                    MainWindow._ensure_chatgpt_page_loaded(window, reload_if_open=True)
                window.browser.load.assert_not_called()
                window.browser.reload.assert_not_called()

    def test_close_during_load_finished_injection_is_cancellation(self):
        window = SimpleNamespace(
            operations_cancelled=False, page_loading=True, browser=Mock(),
            _update_browser_origin_label=Mock(), _set_live_status=Mock(),
            _sync_browser_runtime_state=Mock(),
            _ensure_automation_ready=Mock(side_effect=BrowserOperationCancelled()),
        )
        with patch.object(module, "log_event") as log, patch.object(module, "log_exception") as errors:
            MainWindow._handle_load_finished(window, True)
        errors.assert_not_called()
        window._set_live_status.assert_not_called()
        self.assertIn("browser.automation_cancelled", [call.args[0] for call in log.call_args_list])


if __name__ == "__main__":
    unittest.main()
