"""A böngésző mikrofonengedélyeinek offline, felhasználói döntésre épülő regressziói."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent, QObject, Qt, QTimer, QUrl, Signal
from PySide6.QtTest import QTest
from PySide6.QtWebEngineCore import QWebEnginePermission
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from gamer_translator.browser_permissions import BrowserMicrophonePermissions


class FakePermission:
    def __init__(
        self, origin="https://chatgpt.com/", *,
        kind=QWebEnginePermission.PermissionType.MediaAudioCapture, valid=True,
    ):
        self.request_origin = QUrl(origin)
        self.kind = kind
        self.valid = valid
        self.grants = 0
        self.denials = 0

    def isValid(self):
        return self.valid

    def origin(self):
        return self.request_origin

    def permissionType(self):
        return self.kind

    def grant(self):
        self.grants += 1

    def deny(self):
        self.denials += 1


class FakePage(QObject):
    permissionRequested = Signal(object)
    loadStarted = Signal()
    renderProcessTerminated = Signal(object, int)

    def __init__(self):
        super().__init__()
        self.current_url = QUrl("https://chatgpt.com/c/offline-beszelgetes")

    def url(self):
        return self.current_url


class BrowserPermissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = QWidget()
        self.window.resize(800, 600)
        self.window.show()
        self.page = FakePage()
        self.controller = BrowserMicrophonePermissions(self.page, self.window)
        self.app.processEvents()

    def tearDown(self):
        self.controller.cancel_pending()
        self.window.close()
        self.controller.deleteLater()
        self.page.deleteLater()
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def request(self, permission):
        self.page.permissionRequested.emit(permission)
        self.app.processEvents()
        return self.controller.dialog

    def button(self, text):
        dialog = self.controller.dialog
        self.assertIsNotNone(dialog)
        matches = [button for button in dialog.buttons() if button.text() == text]
        self.assertEqual(len(matches), 1, [button.text() for button in dialog.buttons()])
        return matches[0]

    def answer(self, allow):
        self.button("Engedélyezés" if allow else "Tiltás").click()
        self.app.processEvents()

    def assert_denied_without_dialog(self, permission):
        self.assertIsNone(self.request(permission))
        self.assertEqual(permission.grants, 0)
        self.assertEqual(permission.denials, 1)

    def test_microphone_waits_for_explicit_asynchronous_hungarian_decision(self):
        permission = FakePermission()
        dialog = self.request(permission)
        self.assertIsInstance(dialog, QMessageBox)
        self.assertTrue(dialog.isVisible())
        self.assertIs(dialog.parentWidget(), self.window)
        self.assertEqual(dialog.buttonRole(self.button("Engedélyezés")), QMessageBox.ButtonRole.AcceptRole)
        self.assertEqual(dialog.buttonRole(self.button("Tiltás")), QMessageBox.ButtonRole.RejectRole)
        self.assertIs(dialog.defaultButton(), self.button("Tiltás"))
        processed = []
        QTimer.singleShot(0, lambda: processed.append(True))
        self.app.processEvents()
        self.assertEqual(processed, [True], "Az engedélykérés nem állíthatja meg az eseményhurkot.")
        self.assertEqual((permission.grants, permission.denials), (0, 0))
        self.answer(True)
        self.assertEqual((permission.grants, permission.denials), (1, 0))
        self.assertIsNone(self.controller.dialog)

    def test_refusal_allows_a_later_request_to_ask_again(self):
        refused = FakePermission()
        self.request(refused)
        self.answer(False)
        self.assertEqual((refused.grants, refused.denials), (0, 1))
        retried = FakePermission()
        self.assertIsNotNone(self.request(retried))
        self.answer(True)
        self.assertEqual((retried.grants, retried.denials), (1, 0))

    def test_closing_permission_dialog_denies_microphone(self):
        permission = FakePermission()
        dialog = self.request(permission)
        dialog.close()
        self.app.processEvents()
        self.assertEqual((permission.grants, permission.denials), (0, 1))
        self.assertIsNone(self.controller.dialog)

    def test_escape_denies_microphone(self):
        permission = FakePermission()
        dialog = self.request(permission)
        QTest.keyClick(dialog, Qt.Key.Key_Escape)
        self.app.processEvents()
        self.assertEqual((permission.grants, permission.denials), (0, 1))
        self.assertIsNone(self.controller.dialog)

    def test_simultaneous_same_origin_requests_share_one_decision(self):
        first = FakePermission()
        second = FakePermission("https://chatgpt.com:443/")
        dialog = self.request(first)
        self.assertIs(self.request(second), dialog)
        self.assertEqual((first.grants, second.grants), (0, 0))
        self.answer(True)
        self.assertEqual((first.grants, first.denials), (1, 0))
        self.assertEqual((second.grants, second.denials), (1, 0))

    def test_shared_refusal_denies_all_pending_requests(self):
        permissions = [FakePermission(), FakePermission()]
        for permission in permissions:
            self.request(permission)
        self.answer(False)
        self.assertEqual([(item.grants, item.denials) for item in permissions], [(0, 1), (0, 1)])

    def test_https_default_port_and_paths_are_the_same_origin(self):
        examples = (
            ("https://chatgpt.com:443/c/proba", "https://chatgpt.com/"),
            ("https://chatgpt.com/", "https://chatgpt.com:443/"),
            ("https://chat.openai.com/c/proba", "https://chat.openai.com/"),
        )
        for current, requested in examples:
            with self.subTest(current=current, requested=requested):
                self.page.current_url = QUrl(current)
                permission = FakePermission(requested)
                self.assertIsNotNone(self.request(permission))
                self.answer(True)
                self.assertEqual((permission.grants, permission.denials), (1, 0))

    def test_other_permission_types_are_denied_without_prompt(self):
        for kind in QWebEnginePermission.PermissionType:
            if kind == QWebEnginePermission.PermissionType.MediaAudioCapture:
                continue
            with self.subTest(kind=kind):
                self.assert_denied_without_dialog(FakePermission(kind=kind))

    def test_foreign_insecure_and_spoofed_request_origins_are_denied(self):
        origins = (
            "https://example.com/", "http://chatgpt.com/", "file:///chatgpt.com",
            "https://chatgpt.com:444/", "https://chatgpt.com.example.com/",
            "https://evil-chatgpt.com/", "https://chatgpt.com./",
            "https://username@chatgpt.com/", "https://username:password@chatgpt.com/",
            "https://chat.openai.com/", "about:blank", "", "data:text/plain,chatgpt.com",
        )
        for origin in origins:
            with self.subTest(origin=origin):
                self.assert_denied_without_dialog(FakePermission(origin))

    def test_current_page_must_have_matching_allowed_origin(self):
        for current in (
            "https://example.com/", "http://chatgpt.com/", "https://chat.openai.com/",
            "https://chatgpt.com:444/", "https://username@chatgpt.com/", "about:blank",
        ):
            with self.subTest(current=current):
                self.page.current_url = QUrl(current)
                self.assert_denied_without_dialog(FakePermission())

    def test_invalid_permission_objects_cannot_open_prompt_or_grant(self):
        permission = FakePermission(valid=False)
        self.assertIsNone(self.request(permission))
        self.assertEqual(permission.grants, 0)
        for malformed in (None, object()):
            with self.subTest(malformed=type(malformed).__name__):
                # A Qt signal az egyébként kiszökő Python kivételt stderrre írná és elnyelné.
                self.controller.handle_request(malformed)
                self.assertIsNone(self.controller.dialog)

    def test_destroyed_permission_wrapper_is_handled_without_grant(self):
        permission = FakePermission()
        with patch.object(permission, "isValid", side_effect=RuntimeError("Qt objektum megszűnt")):
            self.assertIsNone(self.request(permission))
        self.assertEqual(permission.grants, 0)

    def test_permission_invalidated_while_dialog_is_open_is_never_granted(self):
        permission = FakePermission()
        self.request(permission)
        permission.valid = False
        self.answer(True)
        self.assertEqual(permission.grants, 0)
        self.assertIsNone(self.controller.dialog)

    def test_page_origin_is_rechecked_when_allow_is_clicked(self):
        permission = FakePermission()
        self.request(permission)
        self.page.current_url = QUrl("https://example.com/masik-oldal")
        self.answer(True)
        self.assertEqual((permission.grants, permission.denials), (0, 1))
        self.assertIsNone(self.controller.dialog)

    def test_navigation_cancels_pending_requests_and_cannot_grant_late(self):
        permissions = [FakePermission(), FakePermission()]
        dialog = self.request(permissions[0])
        self.request(permissions[1])
        self.page.loadStarted.emit()
        self.assertIsNone(self.controller.dialog)
        dialog.finished.emit(0)
        self.app.processEvents()
        self.assertEqual([(item.grants, item.denials) for item in permissions], [(0, 1), (0, 1)])
        retried = FakePermission()
        self.assertIsNotNone(self.request(retried))
        self.answer(True)
        self.assertEqual(retried.grants, 1)

    def test_renderer_exit_cancels_microphone_prompt(self):
        permission = FakePermission()
        self.request(permission)
        self.page.renderProcessTerminated.emit(object(), 1)
        self.app.processEvents()
        self.assertEqual((permission.grants, permission.denials), (0, 1))
        self.assertIsNone(self.controller.dialog)

    def test_cancel_is_idempotent_and_denies_once(self):
        permission = FakePermission()
        self.request(permission)
        self.controller.cancel_pending()
        self.controller.cancel_pending()
        self.app.processEvents()
        self.assertEqual((permission.grants, permission.denials), (0, 1))
        self.assertIsNone(self.controller.dialog)

    def test_cancelled_window_cannot_grant_new_or_pending_microphone_request(self):
        self.window.operations_cancelled = True
        self.assert_denied_without_dialog(FakePermission())
        self.window.operations_cancelled = False
        permission = FakePermission()
        self.request(permission)
        self.window.operations_cancelled = True
        self.answer(True)
        self.assertEqual((permission.grants, permission.denials), (0, 1))

    def test_qt_request_invalidated_during_grant_does_not_leave_pending_dialog(self):
        permission = FakePermission()
        self.request(permission)
        with patch.object(permission, "grant", side_effect=RuntimeError("Qt kérés megszűnt")):
            self.answer(True)
        self.assertIsNone(self.controller.dialog)
        retried = FakePermission()
        self.assertIsNotNone(self.request(retried))
        self.answer(True)
        self.assertEqual(retried.grants, 1)

    def test_permission_logging_does_not_record_page_url_or_conversation_content(self):
        self.page.current_url = QUrl("https://chatgpt.com/c/bizalmas-hangbeszelgetes?prompt=titkos-szoveg")
        with patch("gamer_translator.browser_permissions.log_event") as logger:
            permission = FakePermission()
            self.request(permission)
            self.answer(True)
            self.assert_denied_without_dialog(FakePermission("https://kulso-oldal.example/privat"))
        self.assertGreaterEqual(logger.call_count, 2)
        rendered = repr(logger.call_args_list)
        for content in ("https://", "chatgpt.com", "bizalmas-hangbeszelgetes", "titkos-szoveg", "kulso-oldal.example"):
            self.assertNotIn(content, rendered)
        for call in logger.call_args_list:
            self.assertTrue(all(isinstance(value, (str, bool, int)) for value in call.kwargs.values()))


if __name__ == "__main__":
    unittest.main()
