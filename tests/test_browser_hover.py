"""Valódi Chromium egér-hover a saját ablakban, offline memóriaoldallal."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent, QEventLoop, QPoint, QTimer, QUrl
from PySide6.QtGui import QInputDevice
from PySide6.QtTest import QTest
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineScript, QWebEngineUrlRequestInterceptor
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication

from gamer_translator.main_window import MainWindow
from gamer_translator.settings_store import SettingsStore


HOVER_FIXTURE = """<!doctype html><html><head><meta charset="utf-8"><link rel="icon" href="data:,"><style>
body{margin:0;font:16px sans-serif;background:#171717;color:white}
#rail{position:absolute;left:0;top:0;width:70px;height:500px;background:#303030}
#home{position:absolute;left:10px;top:40px;width:48px;height:48px}
#cssTooltip{position:absolute;left:65px;top:44px;display:none;background:#555;padding:8px}
#home:hover + #cssTooltip{display:block}
#menu{position:absolute;left:72px;top:100px;display:none;background:#444;padding:8px}
</style></head><body><nav id="rail"><button id="home">⌂</button><span id="cssTooltip">Kezdőlap</span>
<div id="menu">Oldalmenü</div></nav><script>
window.hoverEvents={pointerenter:0,mouseenter:0,pointermove:0,mouseleave:0};
window.lastPointer={};
const home=document.getElementById('home'), menu=document.getElementById('menu');
for(const type of ['pointerenter','mouseenter','pointermove','mouseleave'])
 home.addEventListener(type,event=>{window.hoverEvents[type]++;if(type==='pointermove')window.lastPointer={trusted:event.isTrusted,type:event.pointerType}; if(type==='mouseenter')menu.style.display='block';if(type==='mouseleave')menu.style.display='none';});
window.hoverSnapshot=()=>({events:{...window.hoverEvents},cssHover:home.matches(':hover'),
 pointer:{...window.lastPointer},
 cssTooltip:getComputedStyle(document.getElementById('cssTooltip')).display,
 menu:getComputedStyle(menu).display,
 hoverMedia:matchMedia('(hover:hover)').matches,
 pointerFine:matchMedia('(pointer:fine)').matches});
</script></body></html>"""

# A desktop frontend csak precíz egérmutató esetén kínálja a hover-navigációt.
DESKTOP_HOVER_FIXTURE = HOVER_FIXTURE.replace(
    "#home:hover + #cssTooltip{display:block}",
    "@media(hover:hover) and (pointer:fine){#home:hover + #cssTooltip{display:block}}",
).replace(
    "if(type==='mouseenter')menu.style.display='block';",
    "if(type==='mouseenter' && matchMedia('(hover:hover) and (pointer:fine)').matches)menu.style.display='block';",
)


class BlockHoverNetwork(QWebEngineUrlRequestInterceptor):
    def interceptRequest(self, request):
        if request.requestUrl().scheme() not in {"data", "blob", "about"}:
            request.block(True)


class BrowserHoverTests(unittest.TestCase):
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
            "_build_tray_icon", "_refresh_system_keep_awake", "_restore_system_sleep_state", "_apply_native_window_theme",
        ):
            self.stack.enter_context(patch.object(MainWindow, name))
        self.stack.enter_context(patch.object(MainWindow, "_current_clipboard_signature", return_value=""))
        store = SettingsStore(root_dir=Path(directory))
        settings = store.load_settings()
        settings.game_mode_enabled = True
        store.save_settings(settings)
        self.window = MainWindow(store=store, clipboard=Mock(), private_browser=True, open_on_start=False)
        for name in ("browser_keepalive_timer", "system_keepawake_timer", "browser_refresh_timer", "diagnostics_timer", "interaction_watchdog_timer", "response_followup_timer"):
            getattr(self.window, name).stop()
        self.blocker = BlockHoverNetwork(self.window.profile)
        self.window.profile.setUrlRequestInterceptor(self.blocker)
        self.window.resize(1280, 800)
        self.window.show()
        self.window._show_browser()
        self.app.processEvents()
        self.addCleanup(self.dispose_window)

    def dispose_window(self):
        window = self.window
        window.exit_requested = True
        window.close()
        for widget in (window.browser, window.page, window.browser_background_host, window.translation_overlay, window.quick_chat_overlay):
            widget.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        window.profile.deleteLater()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def load_fixture(self, page, source=HOVER_FIXTURE):
        loop = QEventLoop()
        timer = QTimer()
        timer.setSingleShot(True)
        loaded = []
        def finished(ok):
            loaded.append(ok)
            loop.quit()
        page.loadFinished.connect(finished)
        timer.timeout.connect(loop.quit)
        page.setHtml(source, QUrl("https://chatgpt.com/"))
        timer.start(10000)
        loop.exec()
        timer.stop()
        page.loadFinished.disconnect(finished)
        self.assertEqual(loaded, [True])
        QTest.qWait(150)

    def javascript(self, page, code):
        loop = QEventLoop()
        timer = QTimer()
        timer.setSingleShot(True)
        result = []
        def finished(value):
            result.append(value)
            loop.quit()
        timer.timeout.connect(loop.quit)
        page.runJavaScript(code, QWebEngineScript.ScriptWorldId.MainWorld, finished)
        timer.start(5000)
        if not result:
            loop.exec()
        timer.stop()
        self.assertTrue(result, "Nem érkezett offline JavaScript-visszahívás.")
        return result[0]

    def hover_snapshot(self, view):
        # A Chromium saját Qt renderfelülete kap valódi Qt egérmozgást; nincs DOM-eseményszintézis.
        target = view.focusProxy() or view
        native = target.window().windowHandle()
        QTest.mouseMove(native, target.mapTo(target.window(), QPoint(300, 300)))
        QTest.qWait(50)
        QTest.mouseMove(native, target.mapTo(target.window(), QPoint(34, 64)))
        QTest.qWait(250)
        return json.loads(self.javascript(view.page(), "JSON.stringify(window.hoverSnapshot())"))

    def assert_hover_works(self, snapshot):
        self.assertTrue(snapshot["cssHover"], snapshot)
        self.assertEqual(snapshot["cssTooltip"], "block", snapshot)
        self.assertEqual(snapshot["menu"], "block", snapshot)
        self.assertEqual(snapshot["pointer"], {"trusted": True, "type": "mouse"}, snapshot)
        for name in ("pointerenter", "mouseenter", "pointermove"):
            self.assertGreater(snapshot["events"][name], 0, snapshot)

    def test_native_browser_delivers_css_and_javascript_hover(self):
        self.load_fixture(self.window.page)
        self.assert_hover_works(self.hover_snapshot(self.window.browser))

    def test_hover_after_settings_close(self):
        self.load_fixture(self.window.page)
        self.window.toggle_drawer()
        self.app.processEvents()
        self.window.close_drawer()
        self.app.processEvents()
        self.assert_hover_works(self.hover_snapshot(self.window.browser))

    def test_hover_after_background_host_return(self):
        self.load_fixture(self.window.page)
        self.window._activate_background_browser_host()
        self.app.processEvents()
        self.window._deactivate_background_browser_host()
        self.app.processEvents()
        QTest.qWait(150)
        self.assert_hover_works(self.hover_snapshot(self.window.browser))

    def test_bare_webengine_delivers_same_hover(self):
        profile = QWebEngineProfile(self.app)
        blocker = BlockHoverNetwork(profile)
        profile.setUrlRequestInterceptor(blocker)
        page = QWebEnginePage(profile)
        view = QWebEngineView()
        view.setPage(page)
        view.resize(1000, 650)
        view.show()
        self.app.processEvents()
        try:
            self.load_fixture(page)
            self.assert_hover_works(self.hover_snapshot(view))
        finally:
            view.close()
            view.deleteLater()
            page.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            profile.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


class BrowserHoverStartupTests(unittest.TestCase):
    def test_first_browser_reports_fine_pointer_and_desktop_hover_in_fresh_process(self):
        # A Chromium a profil létrehozásakor olvassa az eszközlistát; a teljes tesztcsomag
        # korábbi ablakai elfednék a hibát. A gyermekfolyamatnak új QApplication kell.
        root = Path(__file__).resolve().parents[1]
        code = (
            "import sys; "
            f"sys.path.insert(0, {str(root)!r}); "
            f"sys.path.insert(0, {str(root / 'tests')!r}); "
            "from test_browser_hover import startup_hover_probe; startup_hover_probe()"
        )
        child_environment = os.environ.copy()
        child_environment["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu --disable-software-rasterizer"
        process = subprocess.run(
            [sys.executable, "-c", code], cwd=root, env=child_environment,
            capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        result = json.loads(process.stdout.strip().splitlines()[-1])
        self.assertTrue(result["pointerFine"], result)
        self.assertTrue(result["anyPointerFine"], result)
        self.assertFalse(result["pointerNone"], result)
        self.assertTrue(result["hover"], result)
        BrowserHoverTests.assert_hover_works(self, result["snapshot"])


def startup_hover_probe():
    """Egy első profil induláskori eszköz- és media query pillanatképe."""
    BrowserHoverTests.setUpClass()
    initial_devices = [{"name": device.name(), "type": str(device.type())} for device in QInputDevice.devices()]
    case = BrowserHoverTests()
    case.setUp()
    try:
        case.load_fixture(case.window.page, DESKTOP_HOVER_FIXTURE)
        result = json.loads(case.javascript(case.window.page, """JSON.stringify({
          pointerFine:matchMedia('(pointer:fine)').matches,
          pointerNone:matchMedia('(pointer:none)').matches,
          anyPointerFine:matchMedia('(any-pointer:fine)').matches,
          hover:matchMedia('(hover:hover)').matches
        })"""))
        result["initialDevices"] = initial_devices
        result["snapshot"] = case.hover_snapshot(case.window.browser)
        print(json.dumps(result, ensure_ascii=True))
    finally:
        case.doCleanups()


if __name__ == "__main__":
    unittest.main()
