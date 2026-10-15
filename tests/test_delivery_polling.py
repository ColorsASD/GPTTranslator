"""Natív visszahívási és poll-versenyhelyzetek, valódi Qt időzítőkkel.

Nincs éles böngészőprofil, hálózat, vágólap vagy billentyűküldés.
"""
from __future__ import annotations

import json
import os
import re
import unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtWidgets import QApplication

from gpttranslator import main_window as module
from gpttranslator.main_window import BrowserEventLoopError, BrowserJavaScriptTimeout, BrowserOperationCancelled, MainWindow
import test_webengine as webengine


def delivery_window(run_javascript):
    return SimpleNamespace(
        settings=SimpleNamespace(page_ready_timeout_ms=1000),
        active_translation_request_id="1" * 32,
        _stop_response_followup_polling=Mock(), _ensure_automation_ready=Mock(),
        _touch_browser_interaction_heartbeat=Mock(), _wait_with_events=Mock(),
        _start_response_followup_polling=Mock(), _run_javascript=run_javascript,
    )


class DeliveryPollingTests(unittest.TestCase):
    def test_late_poll_callback_keeps_completed_result_for_retry_and_launches_once(self):
        calls = []
        result_bucket = {"ok": True, "assistantResponseText": "Új válasz"}
        timed_out = False

        def run(script, *, timeout_ms):
            nonlocal result_bucket, timed_out
            calls.append(script)
            if "const resultValue" in script:
                response = json.dumps({"result": json.dumps(result_bucket) if result_bucket else None})
                # A renderer végrehajtotta a pollt, csak a natív callback késett.
                # A korábbi törlő poll ebben a pillanatban elveszítette a választ.
                if "delete resultBucket" in script:
                    result_bucket = None
                if not timed_out:
                    timed_out = True
                    raise BrowserJavaScriptTimeout("Késő callback")
                return response
            return True

        window = delivery_window(run)
        with patch.object(module, "log_event") as log:
            result = MainWindow._execute_delivery(window, {"prompt": "Teszt", "responseTimeoutMs": 1000})
        self.assertEqual(result["assistantResponseText"], "Új válasz")
        self.assertEqual(sum("window.__gptTranslatorDeliver(" in call for call in calls), 1)
        self.assertEqual(sum("const resultValue" in call for call in calls), 2)
        self.assertIn("delivery.poll_retry", [call.args[0] for call in log.call_args_list])
        self.assertIn("delivery.poll_recovered", [call.args[0] for call in log.call_args_list])
        self.assertIn("if (!true", calls[-1])  # A kész JS műveletet nem kell megszakítani.

    def test_repeated_state_does_not_repeat_progress_or_diagnostic_events(self):
        progress = json.dumps({"seq": 1, "kind": "assistant_response", "text": "Friss", "complete": True})
        diagnostics = [{"seq": 1, "event": "response_ready", "fields": {"text_length": 5}}]
        pending = json.dumps({"result": None, "progress": progress, "diagnostics": diagnostics})
        completed = json.dumps({"result": json.dumps({"ok": True}), "progress": progress, "diagnostics": diagnostics})
        run = Mock(side_effect=[True, pending, pending, completed, True])
        handler = Mock()
        window = delivery_window(run)
        with patch.object(module, "log_event") as log:
            MainWindow._execute_delivery(window, {"prompt": "Teszt"}, progress_handler=handler)
        handler.assert_called_once()
        self.assertEqual(sum(call.args[0] == "page.response_ready" for call in log.call_args_list), 1)
        self.assertEqual(window.last_delivery_diagnostic_sequence, 1)
        for call in run.call_args_list[1:-1]:
            self.assertNotIn("delete resultBucket", call.args[0])
            self.assertNotIn("= [];", call.args[0])

    def test_total_poll_timeout_cancels_only_its_own_remote_operation(self):
        clock = [0.0]
        calls = []

        def run(script, *, timeout_ms):
            calls.append(script)
            if "const resultValue" in script:
                clock[0] += 0.025
                raise BrowserJavaScriptTimeout("Késő callback")
            return True

        window = delivery_window(run)
        window._wait_with_events = lambda delay: clock.__setitem__(0, clock[0] + delay / 1000)
        with patch.object(module.time, "monotonic", side_effect=lambda: clock[0]), \
                patch.object(module, "AUTOMATION_SELF_HEAL_TIMEOUT_BUFFER_MS", 60), \
                patch.object(module, "log_event") as log:
            with self.assertRaisesRegex(RuntimeError, "nem fejeződött be"):
                MainWindow._execute_delivery(window, {"prompt": "Teszt", "pageReadyTimeoutMs": 1, "responseTimeoutMs": 0})
        launch_id = re.search(r'"deliveryCallId": "([0-9a-f]{32})"', calls[0]).group(1)
        self.assertIn(f'__gptTranslatorCancelDelivery("{launch_id}")', calls[-1])
        self.assertIn("if (!false", calls[-1])
        self.assertEqual(sum("window.__gptTranslatorDeliver(" in call for call in calls), 1)
        self.assertIn("delivery.timeout", [call.args[0] for call in log.call_args_list])
        self.assertEqual(window.active_delivery_call_id, "")

    def test_launch_timeout_polls_original_operation_without_relaunch_or_cancellation(self):
        completed = json.dumps({"result": json.dumps({"ok": True, "assistantResponseText": "Kész"})})
        run = Mock(side_effect=[BrowserJavaScriptTimeout("Késő launch callback"), completed, True])
        window = delivery_window(run)
        with patch.object(module, "log_event") as log:
            result = MainWindow._execute_delivery(window, {"prompt": "Teszt"})
        self.assertEqual(result["assistantResponseText"], "Kész")
        self.assertEqual(run.call_count, 3)
        launch, poll, cleanup = [call.args[0] for call in run.call_args_list]
        launch_id = re.search(r'"deliveryCallId": "([0-9a-f]{32})"', launch).group(1)
        self.assertIn("window.__gptTranslatorDeliver(", launch)
        self.assertEqual(sum("window.__gptTranslatorDeliver(" in call.args[0] for call in run.call_args_list), 1)
        self.assertIn(f'const resultValue = resultBucket["{launch_id}"]', poll)
        self.assertIn("__gptTranslatorCancelDelivery", cleanup)
        self.assertIn("if (!true", cleanup)  # A kész saját hívás már nem törlendő.
        self.assertIn("result?.cancelled !== true", launch)
        self.assertIn("__gptTranslatorIsDeliveryCancelled", launch)
        self.assertIn("delivery.launch_pending", [call.args[0] for call in log.call_args_list])
        self.assertEqual(window.active_delivery_call_id, "")

    def test_other_launch_failure_still_cancels_without_polling(self):
        run = Mock(side_effect=[RuntimeError("Megváltozott oldal"), True])
        window = delivery_window(run)
        with self.assertRaisesRegex(RuntimeError, "Megváltozott oldal"):
            MainWindow._execute_delivery(window, {"prompt": "Teszt"})
        self.assertEqual(run.call_count, 2)
        self.assertIn("if (!false", run.call_args.args[0])
        self.assertEqual(window.active_delivery_call_id, "")

    def test_image_poll_refreshes_both_heartbeats_and_preserves_owned_lock(self):
        window = delivery_window(Mock(side_effect=[True, json.dumps({"result": json.dumps({"ok": True})}), True]))
        window.clipboard_translation_in_progress = True
        window._touch_clipboard_translation_heartbeat = Mock()
        MainWindow._execute_delivery(window, {"prompt": "Teszt"})
        window._touch_browser_interaction_heartbeat.assert_called_once()
        window._touch_clipboard_translation_heartbeat.assert_called_once()
        self.assertEqual(window.active_delivery_call_id, "")

    def test_watchdog_does_not_release_an_active_delivery_after_gui_delay(self):
        window = SimpleNamespace(
            active_delivery_call_id="1" * 32,
            browser_interaction_active=True, clipboard_translation_in_progress=True,
            page_loading=False, browser_interaction_heartbeat_monotonic=1.0,
            clipboard_translation_heartbeat_monotonic=1.0,
            _hide_translation_overlay=Mock(), _stop_response_followup_polling=Mock(),
            _sync_browser_host_mode=Mock(), _sync_browser_runtime_state=Mock(), _set_live_status=Mock(),
        )
        with patch.object(module.time, "monotonic", return_value=100.0), patch.object(module, "log_event") as log:
            MainWindow._recover_stuck_interaction_flags(window)
            self.assertTrue(window.browser_interaction_active)
            self.assertTrue(window.clipboard_translation_in_progress)
            window._hide_translation_overlay.assert_not_called()
            log.assert_not_called()
            # A saját finally után már az árva állapot helyreállítása érvényes.
            window.active_delivery_call_id = ""
            MainWindow._recover_stuck_interaction_flags(window)
            self.assertFalse(window.browser_interaction_active)
            self.assertFalse(window.clipboard_translation_in_progress)
            self.assertEqual(log.call_args.args[0], "browser.watchdog_recovered")

    def test_other_browser_failure_is_not_silently_retried(self):
        run = Mock(side_effect=[True, RuntimeError("Az oldal címe megváltozott"), True])
        with self.assertRaisesRegex(RuntimeError, "címe megváltozott"):
            MainWindow._execute_delivery(delivery_window(run), {"prompt": "Teszt"})
        self.assertEqual(run.call_count, 3)
        self.assertIn("if (!false", run.call_args.args[0])

    def test_interrupted_native_event_loop_cannot_spin_renderer_poll_retries(self):
        run = Mock(side_effect=[True, BrowserEventLoopError("Megszakadt eseményhurok"), True])
        with patch.object(module, "log_event") as log:
            with self.assertRaises(BrowserEventLoopError):
                MainWindow._execute_delivery(delivery_window(run), {"prompt": "Teszt"})
        self.assertEqual(run.call_count, 3)  # Indítás, egy poll, saját művelet törlése.
        self.assertNotIn("delivery.poll_retry", [call.args[0] for call in log.call_args_list])

    def test_image_recovery_preparation_preserves_full_response_wait(self):
        clock = [0.0]
        polls = []
        preparation_seconds = 320.0
        response_timeout_seconds = 60.0

        def run(script, *, timeout_ms):
            if "const resultValue" not in script:
                return True
            polls.append(timeout_ms)
            if len(polls) == 1:
                # Az elakadt csatolások helyreállítása és újrapróbálása
                # túlnyúlik a korábbi teljes natív küldési határidőn.
                clock[0] = preparation_seconds
                return json.dumps({"result": None})
            clock[0] = preparation_seconds + response_timeout_seconds - 0.001
            return json.dumps({"result": json.dumps({"ok": True, "assistantResponseText": "Kész"})})

        window = delivery_window(run)
        window._wait_with_events = lambda delay: clock.__setitem__(0, clock[0] + delay / 1000)
        with patch.object(module.time, "monotonic", side_effect=lambda: clock[0]):
            result = MainWindow._execute_delivery(window, {
                "prompt": "Teszt", "imageDataUrl": "data:image/png;base64,teszt", "autoSubmit": True,
                "pageReadyTimeoutMs": 25000, "responseTimeoutMs": 60000,
            })
        self.assertEqual(result["assistantResponseText"], "Kész")
        self.assertEqual(len(polls), 2)
        self.assertEqual(window.active_delivery_call_id, "")

    def test_text_and_unsubmitted_image_keep_the_existing_native_deadline(self):
        for image_data, auto_submit in (("", True), ("data:image/png;base64,teszt", False)):
            with self.subTest(has_image=bool(image_data), auto_submit=auto_submit):
                clock = [0.0]
                polls = []

                def run(script, *, timeout_ms):
                    if "const resultValue" in script:
                        polls.append(timeout_ms)
                        clock[0] = 156.0
                        return json.dumps({"result": None})
                    return True

                window = delivery_window(run)
                window._wait_with_events = lambda delay: clock.__setitem__(0, clock[0] + delay / 1000)
                with patch.object(module.time, "monotonic", side_effect=lambda: clock[0]), \
                        patch.object(module, "log_event") as log:
                    with self.assertRaisesRegex(RuntimeError, "nem fejeződött be"):
                        MainWindow._execute_delivery(window, {
                            "prompt": "Teszt", "imageDataUrl": image_data, "autoSubmit": auto_submit,
                            "pageReadyTimeoutMs": 25000, "responseTimeoutMs": 60000,
                        })
                self.assertEqual(len(polls), 1)
                timeout_event = next(call for call in log.call_args_list if call.args[0] == "delivery.timeout")
                self.assertEqual(timeout_event.kwargs["timeout_ms"], 155000)

    def test_response_timeout_preserves_remote_followup_and_diagnostic_cursor(self):
        diagnostics = [{"seq": 8, "event": "response_timeout", "fields": {"timeout_ms": 1000}}]
        pending = {"ok": False, "responsePending": True, "followUpProgressCallId": "followup", "error": "Válasz késik"}
        state = json.dumps({"result": json.dumps(pending), "diagnostics": diagnostics})
        run = Mock(side_effect=[True, state, True])
        window = delivery_window(run)
        handler = Mock()
        with self.assertRaisesRegex(RuntimeError, "Válasz késik"):
            MainWindow._execute_delivery(window, {"prompt": "Teszt"}, progress_handler=handler)
        window._start_response_followup_polling.assert_called_once_with("followup", handler)
        self.assertEqual(window.last_delivery_diagnostic_sequence, 8)
        self.assertIn("if (!true", run.call_args.args[0])


class JavaScriptCallbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_late_callback_after_timeout_cannot_complete_the_next_call(self):
        callbacks = []
        browser = Mock()
        browser.url.return_value = QUrl("https://chatgpt.com/")

        def run(script, world, callback):
            callbacks.append(callback)
            if len(callbacks) == 2:
                # Előbb a lejárt hívás eredménye érkezik; az új hívás vár tovább.
                QTimer.singleShot(1, lambda: callbacks[0]("Régi eredmény"))
                QTimer.singleShot(20, lambda: callback("Új eredmény"))

        browser.page.return_value.runJavaScript.side_effect = run
        window = SimpleNamespace(
            browser=browser, browser_interaction_active=False, clipboard_translation_in_progress=False,
            _is_chatgpt_url=lambda value: MainWindow._is_chatgpt_url(None, value),
        )
        with patch.object(module, "log_event") as log:
            with self.assertRaises(BrowserJavaScriptTimeout):
                MainWindow._run_javascript(window, "42", timeout_ms=10)
            self.assertEqual(MainWindow._run_javascript(window, "43", timeout_ms=1000), "Új eredmény")
        self.assertEqual(sum(call.args[0] == "browser.javascript_timeout" for call in log.call_args_list), 1)

    def test_cancelled_wait_ignores_late_callback(self):
        class CancellationSignals(QObject):
            cancelled = Signal()

        signals = CancellationSignals()
        callback = []
        browser = Mock()
        browser.url.return_value = QUrl("https://chatgpt.com/")
        browser.page.return_value.runJavaScript.side_effect = lambda script, world, cb: callback.append(cb)
        window = SimpleNamespace(
            browser=browser, browser_interaction_active=False, clipboard_translation_in_progress=False,
            operations_cancelled=False, browser_operations_cancelled=signals.cancelled,
            _is_chatgpt_url=lambda value: MainWindow._is_chatgpt_url(None, value),
        )
        def cancel():
            window.operations_cancelled = True
            signals.cancelled.emit()

        QTimer.singleShot(10, cancel)
        with patch.object(module, "log_event") as log:
            with self.assertRaises(BrowserOperationCancelled):
                MainWindow._run_javascript(window, "42", timeout_ms=1000)
        log.assert_not_called()
        # A visszahívás nem nyúlhat már a lezárt/destruktorra váró Qt eseményhurokhoz.
        callback[0]("Elkésett eredmény")
        callback[0]("Ismételt elkésett eredmény")

    def test_early_event_loop_exit_is_not_reported_as_a_renderer_timeout(self):
        callbacks = []
        browser = Mock()
        browser.url.return_value = QUrl("https://chatgpt.com/")
        browser.page.return_value.runJavaScript.side_effect = lambda script, world, cb: callbacks.append(cb)
        window = SimpleNamespace(
            browser=browser, browser_interaction_active=False, clipboard_translation_in_progress=False,
            _is_chatgpt_url=lambda value: MainWindow._is_chatgpt_url(None, value),
        )
        loop = SimpleNamespace(exec=Mock(return_value=0), isRunning=lambda: False)
        with patch.object(module, "QEventLoop", return_value=loop), patch.object(module, "log_event") as log:
            with self.assertRaises(BrowserEventLoopError):
                MainWindow._run_javascript(window, "42", timeout_ms=5000)
        self.assertEqual([call.args[0] for call in log.call_args_list], ["browser.event_loop_failed"])
        self.assertEqual(log.call_args.kwargs["reason"], "loop_interrupted")
        # A megszakított művelet visszahívása már lezárt állapotot lát.
        callbacks[0]("Elkésett eredmény")

    def test_exit_request_cancels_before_close_event_and_never_launches_javascript(self):
        browser = Mock()
        window = SimpleNamespace(browser=browser, operations_cancelled=False, exit_requested=True)
        with self.assertRaises(BrowserOperationCancelled):
            MainWindow._run_javascript(window, "42", timeout_ms=5000)
        browser.assert_not_called()
        browser.page.assert_not_called()

    def test_exit_request_during_wait_is_cancellation_without_renderer_timeout(self):
        class CancellationSignals(QObject):
            cancelled = Signal()

        signals = CancellationSignals()
        browser = Mock()
        browser.url.return_value = QUrl("https://chatgpt.com/")
        window = SimpleNamespace(
            browser=browser, browser_interaction_active=False, clipboard_translation_in_progress=False,
            operations_cancelled=False, exit_requested=False, browser_operations_cancelled=signals.cancelled,
            _is_chatgpt_url=lambda value: MainWindow._is_chatgpt_url(None, value),
        )

        def exit_before_close_event():
            window.exit_requested = True
            signals.cancelled.emit()

        QTimer.singleShot(10, exit_before_close_event)
        with patch.object(module, "log_event") as log:
            with self.assertRaises(BrowserOperationCancelled):
                MainWindow._run_javascript(window, "42", timeout_ms=5000)
        log.assert_not_called()

    def test_worker_thread_is_rejected_before_accessing_the_gui_browser(self):
        browser = Mock()
        window = SimpleNamespace(browser=browser)
        with ThreadPoolExecutor(max_workers=1) as executor, patch.object(module, "log_event") as log:
            future = executor.submit(MainWindow._run_javascript, window, "42", timeout_ms=5000)
            with self.assertRaises(BrowserEventLoopError):
                future.result(timeout=2)
        browser.url.assert_not_called()
        browser.page.assert_not_called()
        self.assertEqual(log.call_args.kwargs["reason"], "wrong_thread")

    def test_interrupted_frame_wait_stops_its_timer_and_cannot_poll_in_a_busy_loop(self):
        loop = SimpleNamespace(exec=Mock(return_value=0), quit=Mock())
        timer = QTimer()
        with patch.object(module, "QEventLoop", return_value=loop), \
                patch.object(module, "QTimer", return_value=timer), patch.object(module, "log_event") as log:
            with self.assertRaises(BrowserEventLoopError):
                MainWindow._wait_with_events(SimpleNamespace(), 20)
        self.assertFalse(timer.isActive())
        self.assertEqual(log.call_args.kwargs["reason"], "loop_interrupted")


class OfflinePollingIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        webengine.WebEngineStagingTests.setUpClass()

    def test_delayed_native_poll_callback_keeps_real_image_delivery_result(self):
        fixture = webengine.WebEngineStagingTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        fixture.load_fixture()
        harness = fixture.harness
        callback_delayed = [False]
        polls = []
        launches = []

        def run_javascript(script, world, callback):
            if '"deliveryCallId": "' in script:
                launches.append(script)
            if "const resultValue" in script:
                polls.append(script)
                if not callback_delayed[0]:
                    callback_delayed[0] = True
                    fixture.page.runJavaScript(
                        script, world,
                        lambda value: QTimer.singleShot(100, lambda: callback(value)),
                    )
                    return
            fixture.page.runJavaScript(script, world, callback)

        proxy_page = SimpleNamespace(runJavaScript=run_javascript)
        harness.browser = SimpleNamespace(url=fixture.page.url, page=lambda: proxy_page)

        def native_run(script, *, timeout_ms):
            # A renderer ténylegesen futtatja a pollt, de az első natív visszahívás
            # csak a saját időkorlátja után érkezik meg. A kézbesítést nem indítjuk újra.
            if "const resultValue" in script and not callback_delayed[0]:
                timeout_ms = 20
            return MainWindow._run_javascript(harness, script, timeout_ms=timeout_ms)

        harness._run_javascript = native_run
        png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII="
        with patch.object(module, "log_event") as log:
            result = fixture.deliver(
                imageDataUrl=f"data:image/png;base64,{png}", imageMimeType="image/png", imageFilename="offline.png",
            )
        harness._wait_with_events(130)
        self.assertEqual(result["assistantResponseText"], "Offline fordítás elkészült.")
        self.assertEqual(fixture.raw_javascript("document.body.dataset.submitCount"), "1")
        self.assertEqual(len(launches), 1)
        self.assertGreaterEqual(len(polls), 2)
        self.assertIn("delivery.poll_recovered", [call.args[0] for call in log.call_args_list])
        self.assertEqual(harness.active_delivery_call_id, "")
        self.assertEqual(fixture.page.errors, [])
        self.assertEqual(fixture.blocker.blocked, [])

    def test_delayed_native_launch_callback_keeps_submitted_image_running(self):
        fixture = webengine.WebEngineStagingTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        fixture.load_fixture()
        harness = fixture.harness
        launches = []
        polls = []
        launch_callback_received = []

        def run_javascript(script, world, callback):
            if '"deliveryCallId": "' in script:
                launches.append(script)

                def delayed_result(value):
                    def deliver_late_callback():
                        launch_callback_received.append(True)
                        callback(value)
                    QTimer.singleShot(150, deliver_late_callback)

                # A renderer elindítja az eredeti képes kérést; csak a natív
                # indítási visszaigazolása késik a helyi határidőn túlra.
                fixture.page.runJavaScript(script, world, delayed_result)
                return
            if "const resultValue" in script:
                polls.append(script)
            fixture.page.runJavaScript(script, world, callback)

        proxy_page = SimpleNamespace(runJavaScript=run_javascript)
        harness.browser = SimpleNamespace(url=fixture.page.url, page=lambda: proxy_page)

        def native_run(script, *, timeout_ms):
            if '"deliveryCallId": "' in script:
                timeout_ms = 20
            return MainWindow._run_javascript(harness, script, timeout_ms=timeout_ms)

        harness._run_javascript = native_run
        png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII="
        with patch.object(module, "log_event") as log:
            result = fixture.deliver(
                imageDataUrl=f"data:image/png;base64,{png}", imageMimeType="image/png", imageFilename="offline.png",
            )
        harness._wait_with_events(180)
        self.assertEqual(result["assistantResponseText"], "Offline fordítás elkészült.")
        self.assertEqual(fixture.raw_javascript("document.body.dataset.submitCount"), "1")
        self.assertEqual(len(launches), 1)
        self.assertTrue(polls)
        launch_id = re.search(r'"deliveryCallId": "([0-9a-f]{32})"', launches[0]).group(1)
        for poll in polls:
            self.assertIn(f'const resultValue = resultBucket["{launch_id}"]', poll)
        self.assertEqual(launch_callback_received, [True])
        self.assertIn("delivery.launch_pending", [call.args[0] for call in log.call_args_list])
        self.assertEqual(harness.active_delivery_call_id, "")
        self.assertEqual(fixture.page.errors, [])
        self.assertEqual(fixture.blocker.blocked, [])


if __name__ == "__main__":
    unittest.main()
