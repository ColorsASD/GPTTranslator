"""Valódi Chromium mikrofonengedély, szintetikus eszközzel és hálózat nélkül."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


class BrowserVoiceMediaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # A fake-device kapcsolót a legelső WebEngine-profil előtt kell átadni.
        # A fake-ui kapcsoló megkerülné a program engedélykérőjét, ezért nincs jelen.
        root = Path(__file__).resolve().parents[1]
        code = (
            "import sys; "
            f"sys.path.insert(0, {str(root)!r}); "
            f"sys.path.insert(0, {str(root / 'tests')!r}); "
            "from test_browser_voice_media import probe_browser_voice_media; "
            "probe_browser_voice_media()"
        )
        environment = os.environ.copy()
        environment["QT_QPA_PLATFORM"] = "offscreen"
        environment["QTWEBENGINE_CHROMIUM_FLAGS"] = (
            "--use-fake-device-for-media-stream --disable-gpu --disable-software-rasterizer"
        )
        process = subprocess.run(
            [sys.executable, "-c", code], cwd=root, env=environment,
            capture_output=True, text=True, encoding="utf-8", timeout=45,
        )
        if process.returncode:
            raise AssertionError(f"Az offline hangteszt elbukott:\n{process.stdout}\n{process.stderr}")
        cls.result = json.loads(process.stdout.strip().splitlines()[-1])

    def test_native_microphone_request_uses_app_dialog_and_grants_fake_audio(self):
        result = self.result["grant"]
        self.assertTrue(result["secure_context"], result)
        self.assertTrue(result["trusted_click"], result)
        self.assertEqual(result["permission_types"], ["MediaAudioCapture"], result)
        self.assertTrue(result["dialog_shown"], result)
        self.assertEqual(result["audio_tracks"], 1, result)
        self.assertEqual(result["state"], "granted", result)
        self.assertFalse(self.result["network_allowed"])
        self.assertTrue(self.result["synthetic_device_only"])

    def test_hidden_voice_stays_active_without_rendering_and_stops_to_frozen(self):
        result = self.result["grant"]
        self.assertEqual(result["hidden_capture"]["lifecycle"], "Active", result)
        self.assertEqual(result["hidden_capture"]["recommended"], "Active", result)
        self.assertFalse(result["hidden_capture"]["visible"], result)
        self.assertFalse(result["hidden_capture"]["updates_enabled"], result)
        self.assertFalse(result["hidden_capture"]["refresh_timer_running"], result)
        self.assertEqual(result["hidden_stopped"]["lifecycle"], "Frozen", result)
        self.assertFalse(result["hidden_stopped"]["visible"], result)
        self.assertFalse(result["hidden_stopped"]["updates_enabled"], result)
        self.assertFalse(result["hidden_stopped"]["refresh_timer_running"], result)

    def test_deny_settles_request_without_stream(self):
        result = self.result["deny"]
        self.assertTrue(result["dialog_shown"], result)
        self.assertEqual(result["permission_types"], ["MediaAudioCapture"], result)
        self.assertEqual(result["state"], "denied", result)
        # Qt 6.11 a megtagadott médiakérést INVALID_STATE-ként zárja le;
        # a Chromium ezt AbortError-ra fordítja. Mindkét kód rendezett tiltás.
        self.assertIn(result["error"], {"AbortError", "NotAllowedError"}, result)
        self.assertEqual(result["audio_tracks"], 0, result)

    def test_foreign_origin_is_denied_without_app_permission_dialog(self):
        result = self.result["foreign"]
        self.assertEqual(result["permission_types"], ["MediaAudioCapture"], result)
        self.assertFalse(result["dialog_shown"], result)
        self.assertEqual(result["state"], "denied", result)
        self.assertIn(result["error"], {"AbortError", "NotAllowedError"}, result)
        self.assertEqual(result["audio_tracks"], 0, result)


def probe_browser_voice_media():
    """Külön folyamat: privát memóriaoldal és kizárólag szintetikus hangforrás."""
    import tempfile
    import time
    from contextlib import ExitStack
    from unittest.mock import Mock, patch

    from PySide6.QtCore import QCoreApplication, QEvent, QEventLoop, QPoint, QTimer, Qt, QUrl
    from PySide6.QtTest import QTest
    from PySide6.QtWebEngineCore import QWebEngineScript, QWebEngineUrlRequestInterceptor
    from PySide6.QtWidgets import QApplication, QPushButton

    from gpttranslator.main_window import MainWindow
    from gpttranslator.settings_store import SettingsStore

    flags = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "").split()
    assert "--use-fake-device-for-media-stream" in flags, "A valódi mikrofon nem használható."
    assert "--use-fake-ui-for-media-stream" not in flags, "A program engedélykérője nem kerülhető meg."
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)

    class BlockVoiceNetwork(QWebEngineUrlRequestInterceptor):
        def interceptRequest(self, request):
            # A setHtml fődokumentuma data:; minden távoli kérés tiltott.
            if request.requestUrl().scheme() not in {"data", "blob", "about"}:
                request.block(True)

    def settle(predicate, *, timeout_ms=5000, description="offline állapot"):
        end = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < end:
            app.processEvents()
            if predicate():
                return
            QTest.qWait(15)
        raise AssertionError(f"Nem érkezett meg: {description}.")

    def javascript(page, code):
        loop = QEventLoop()
        timer = QTimer()
        timer.setSingleShot(True)
        values = []

        def finished(value):
            values.append(value)
            loop.quit()

        timer.timeout.connect(loop.quit)
        page.runJavaScript(code, QWebEngineScript.ScriptWorldId.MainWorld, finished)
        timer.start(5000)
        if not values:
            loop.exec()
        timer.stop()
        assert values, "Az offline JavaScript-visszahívás nem érkezett meg."
        return values[0]

    fixture = """<!doctype html><html><head><meta charset="utf-8"><link rel="icon" href="data:,"></head>
      <body style="margin:0;background:#171717;color:white">
      <button id="voice" style="position:absolute;left:24px;top:24px;width:240px;height:56px">Hang indítása</button>
      <script>
      window.voiceResult={state:'idle',audio_tracks:0,secure_context:window.isSecureContext,trusted_click:false};
      document.getElementById('voice').addEventListener('click', async event=>{
        window.voiceResult.trusted_click=event.isTrusted;
        window.voiceResult.state='pending';
        try {
          window.syntheticStream=await navigator.mediaDevices.getUserMedia({audio:true});
          window.voiceResult.audio_tracks=window.syntheticStream.getAudioTracks().length;
          window.voiceResult.state='granted';
        } catch(error) {
          window.voiceResult.error=error.name;
          window.voiceResult.state='denied';
        }
      });
      </script></body></html>"""

    def snapshot(window):
        return {
            "lifecycle": window.page.lifecycleState().name,
            "recommended": window.page.recommendedState().name,
            "visible": window.page.isVisible(),
            "updates_enabled": window.browser.updatesEnabled(),
            "refresh_timer_running": window.browser_refresh_timer.isActive(),
        }

    results = {"network_allowed": False, "synthetic_device_only": True}
    for scenario in ("grant", "deny", "foreign"):
        with ExitStack() as stack:
            directory = stack.enter_context(tempfile.TemporaryDirectory(ignore_cleanup_errors=True))
            for name in (
                "open_chatgpt", "_register_hotkeys", "_unregister_hotkeys",
                "_install_keyboard_hook", "_uninstall_keyboard_hook", "_install_mouse_hook", "_uninstall_mouse_hook",
                "_build_tray_icon", "_refresh_system_keep_awake", "_restore_system_sleep_state",
                "_apply_native_window_theme", "_ensure_automation_ready",
            ):
                stack.enter_context(patch.object(MainWindow, name))
            stack.enter_context(patch.object(MainWindow, "_current_clipboard_signature", return_value=""))
            store = SettingsStore(root_dir=Path(directory))
            settings = store.load_settings()
            settings.monitoring_enabled = False
            settings.ocr_text_from_clipboard_image = False
            settings.keep_chatgpt_in_background = True
            store.save_settings(settings)
            window = MainWindow(store=store, clipboard=Mock(), private_browser=True, open_on_start=False)
            for name in (
                "browser_keepalive_timer", "system_keepawake_timer", "browser_refresh_timer",
                "diagnostics_timer", "interaction_watchdog_timer", "response_followup_timer",
            ):
                getattr(window, name).stop()
            blocker = BlockVoiceNetwork(window.profile)
            window.profile.setUrlRequestInterceptor(blocker)
            window.resize(1280, 800)
            window.show()
            window._show_browser()
            app.processEvents()
            permissions = []
            window.page.permissionRequested.connect(lambda permission: permissions.append(permission.permissionType().name))
            try:
                loaded = []
                window.page.loadFinished.connect(loaded.append)
                origin = "https://foreign.invalid/" if scenario == "foreign" else "https://chatgpt.com/"
                window.page.setHtml(fixture, QUrl(origin))
                settle(lambda: bool(loaded), description="a memóriaoldal betöltése")
                assert loaded == [True], loaded
                QTest.qWait(100)
                controllers = [value for value in vars(window).values() if type(value).__name__ == "BrowserMicrophonePermissions"]
                assert len(controllers) == 1, "A valódi főablaknak saját mikrofonengedély-kezelő kell."
                controller = controllers[0]
                target = window.browser.focusProxy() or window.browser
                QTest.mouseClick(target, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(100, 50))
                dialog_shown = False
                if scenario != "foreign":
                    settle(lambda: controller.dialog is not None and controller.dialog.isVisible(), description="a magyar mikrofonengedély-ablak")
                    dialog_shown = True
                    title = "Engedélyezés" if scenario == "grant" else "Tiltás"
                    buttons = [button for button in controller.dialog.findChildren(QPushButton) if button.text() == title]
                    assert len(buttons) == 1, (title, [button.text() for button in controller.dialog.findChildren(QPushButton)])
                    QTest.mouseClick(buttons[0], Qt.MouseButton.LeftButton)
                settle(lambda: javascript(window.page, "window.voiceResult.state") in {"granted", "denied"}, description="a getUserMedia ígéretének lezárása")
                result = json.loads(javascript(window.page, "JSON.stringify(window.voiceResult)"))
                result.update({"permission_types": permissions, "dialog_shown": dialog_shown})
                if scenario == "grant":
                    window._hide_to_tray(show_message=False)
                    settle(lambda: not window.page.isVisible(), description="a hanghívás láthatatlan állapota")
                    QTest.qWait(100)
                    result["hidden_capture"] = snapshot(window)
                    javascript(window.page, "window.syntheticStream.getTracks().forEach(track=>track.stop());")
                    settle(lambda: window.page.lifecycleState().name == "Frozen", description="a leállított hanghívás fagyasztása")
                    result["hidden_stopped"] = snapshot(window)
                else:
                    assert controller.dialog is None or not controller.dialog.isVisible(), "A megtagadott kérés ablaka nem maradhat nyitva."
                results[scenario] = result
            finally:
                window.exit_requested = True
                window.close()
                for widget in (window.browser, window.page, window.browser_background_host, window.translation_overlay, window.quick_chat_overlay):
                    widget.deleteLater()
                QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
                window.profile.deleteLater()
                window.deleteLater()
                QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
                app.processEvents()
    print(json.dumps(results, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
