"""A ChatGPT mikrofonengedélyének natív, nem blokkoló kezelése."""
from __future__ import annotations

from urllib.parse import urlparse

from PySide6.QtCore import QObject, Qt, QUrl
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEnginePermission
from PySide6.QtWidgets import QMessageBox, QWidget

from .defaults import APP_NAME, CHATGPT_HOSTS
from .design_widgets import icon
from .diagnostics import log_event


def _chatgpt_origin(url: QUrl) -> tuple[str, str, int] | None:
    try:
        if not url.isValid():
            return None
        parsed = urlparse(url.toString())
        if (parsed.scheme != "https" or parsed.hostname not in CHATGPT_HOSTS
                or parsed.port not in (None, 443)
                or parsed.username is not None or parsed.password is not None):
            return None
        return ("https", parsed.hostname, 443)
    except (ValueError, RuntimeError):
        return None


class BrowserMicrophonePermissions(QObject):
    """Egy engedélykérő ablak, az aktuális főlap azonos eredetéhez kötve."""

    def __init__(self, page: QWebEnginePage, window: QWidget) -> None:
        super().__init__(window)
        self.page, self.window = page, window
        self.dialog: QMessageBox | None = None
        self._pending: list[QWebEnginePermission] = []
        page.permissionRequested.connect(self.handle_request)
        page.loadStarted.connect(self.cancel_pending)
        page.renderProcessTerminated.connect(lambda *_: self.cancel_pending())

    @staticmethod
    def _valid(permission: QWebEnginePermission) -> bool:
        try:
            return permission.isValid()
        except (RuntimeError, AttributeError, TypeError):
            return False

    def _may_allow(self, permission: QWebEnginePermission) -> bool:
        if not self._valid(permission) or getattr(self.window, "operations_cancelled", False):
            return False
        try:
            origin = _chatgpt_origin(permission.origin())
            return (permission.permissionType() == QWebEnginePermission.PermissionType.MediaAudioCapture
                    and origin is not None and origin == _chatgpt_origin(self.page.url()))
        except RuntimeError:
            return False

    def _resolve(self, permission: QWebEnginePermission, allowed: bool) -> None:
        if not self._valid(permission):
            return
        try:
            permission.grant() if allowed else permission.deny()
            log_event("browser.permission_decided", kind="microphone" if allowed else "web_permission",
                      accepted=allowed)
        except RuntimeError:
            log_event("browser.permission_invalidated", reason="page_changed")

    def handle_request(self, permission: QWebEnginePermission) -> None:
        if not self._valid(permission):
            return
        if not self._may_allow(permission):
            self._resolve(permission, False)
            return
        self._pending.append(permission)
        if self.dialog is not None:
            return
        dialog = QMessageBox(self.window)
        dialog.setObjectName("microphonePermissionDialog")
        dialog.setWindowTitle(APP_NAME)
        dialog.setTextFormat(Qt.TextFormat.PlainText)
        dialog.setIconPixmap(icon("microphone").pixmap(40, 40))
        dialog.setText("Engedélyezed a ChatGPT számára a mikrofon használatát?")
        dialog.setInformativeText("A mikrofon a hangbeszélgetéshez szükséges. Csak a ChatGPT aktuális oldalának adsz hozzáférést.")
        dialog.addButton("Engedélyezés", QMessageBox.ButtonRole.AcceptRole)
        denied = dialog.addButton("Tiltás", QMessageBox.ButtonRole.RejectRole)
        dialog.setDefaultButton(denied)
        dialog.setEscapeButton(denied)
        dialog.setWindowModality(Qt.WindowModality.WindowModal)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.setStyleSheet("""
            QMessageBox { background: #212121; color: #ececec; }
            QMessageBox QLabel { color: #ececec; }
            QMessageBox QPushButton { background: #303030; color: #ececec;
                border: 1px solid #484848; border-radius: 8px; padding: 9px 16px; min-width: 94px; }
            QMessageBox QPushButton:hover { background: #3c3c3c; }
            QMessageBox QPushButton:focus { border: 1px solid #b2b2b2; }
        """)
        self.dialog = dialog
        dialog.finished.connect(lambda _result: self._finish(dialog))
        log_event("browser.permission_requested", kind="microphone")
        dialog.open()

    def _finish(self, dialog: QMessageBox) -> None:
        if dialog is not self.dialog:
            return
        accepted = (dialog.clickedButton() is not None
                    and dialog.buttonRole(dialog.clickedButton()) == QMessageBox.ButtonRole.AcceptRole)
        self.dialog = None
        pending, self._pending = self._pending, []
        for permission in pending:
            self._resolve(permission, accepted and self._may_allow(permission))

    def cancel_pending(self) -> None:
        dialog, self.dialog = self.dialog, None
        pending, self._pending = self._pending, []
        for permission in pending:
            self._resolve(permission, False)
        if dialog is not None:
            dialog.reject()
            dialog.deleteLater()
