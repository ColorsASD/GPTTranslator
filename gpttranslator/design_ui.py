"""A GPTTranslator szürke fejléc- és beállítási felülete."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QCheckBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QMenu,
    QPlainTextEdit, QPushButton, QScrollArea, QSizePolicy, QSlider,
    QVBoxLayout, QWidget,
)

from .defaults import APP_NAME
from .design_widgets import AmbientPanel, ContentEdge, IconBadge, ToggleSwitch, icon


def label(text: str, name: str = "", *, wrap: bool = False) -> QLabel:
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(wrap)
    widget.setObjectName(name)
    return widget


def button(text: str, symbol: str, callback, name: str = "", width: int = 0) -> QPushButton:
    widget = QPushButton(text)
    if symbol:
        widget.setIcon(icon(symbol))
    widget.setIconSize(QSize(24, 24))
    widget.setObjectName(name)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    widget.clicked.connect(callback)
    if width:
        widget.setFixedWidth(width)
    return widget


def card(title: str, description: str, symbol: str) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("settingsCard")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(18, 10, 18, 10)
    layout.setSpacing(10)
    heading = QHBoxLayout()
    heading.setSpacing(14)
    heading.addWidget(IconBadge(symbol, size=52))
    text = QVBoxLayout()
    text.setSpacing(4)
    text.addWidget(label(title, "cardTitle"))
    text.addWidget(label(description, "secondaryText", wrap=True))
    heading.addLayout(text, 1)
    layout.addLayout(heading)
    return frame, layout


def checkbox_row(control: QCheckBox, description: str) -> QWidget:
    row = QWidget()
    layout = QVBoxLayout(row)
    layout.setContentsMargins(4, 0, 4, 0)
    layout.setSpacing(3)
    layout.addWidget(control)
    subtitle = label(description, "secondaryText", wrap=True)
    subtitle.setContentsMargins(49, 0, 0, 0)
    layout.addWidget(subtitle)
    return row


def build_ui(window) -> None:
    w = window
    w.monitoring_enabled = ToggleSwitch()
    w.monitoring_enabled.setAccessibleName("A program legyen aktív")
    w.chatgpt_url = QLineEdit(w)
    w.chatgpt_url.hide()
    w.page_ready_timeout_ms = w._build_spin_box(maximum=120000, step=1000)
    w.page_ready_timeout_ms.setMinimum(1000)
    w.page_ready_timeout_ms.setParent(w)
    w.page_ready_timeout_ms.hide()
    w.prompt_template = QPlainTextEdit()
    w.prompt_template.setPlaceholderText("Ide kerül a kézi prompt.")
    w.prompt_template.setMinimumHeight(120)
    w.prompt_template.setMaximumHeight(152)
    w.copy_response_to_clipboard = QCheckBox("A ChatGPT válasza kerüljön a vágólapra")
    w.ocr_text_from_clipboard_image = QCheckBox("Szöveg kiolvasása képről")
    w.webview_gpu_acceleration_enabled = QCheckBox("A ChatGPT nézet használja a GPU gyorsítást")
    w.nvidia_mouse_lag_fix_enabled = QCheckBox("NVIDIA egérakadás javítása")
    w.nvidia_mouse_lag_fix_enabled.setToolTip(
        "Induláskor automatikusan beállítja a program NVIDIA-profilját. "
        "A módosítás mentés után újraindítja a programot."
    )
    w.screen_clip_hotkey_enabled = QCheckBox("A Windows képkivágó nyíljon meg gyorsbillentyűvel")
    w.screen_clip_hotkey_enabled.setToolTip(
        "Csak a beállított képkivágási gyorsbillentyűvel készített kép kerül automatikusan fordításra."
    )
    w.type_out_hotkey_enabled = QCheckBox()
    w.type_out_hotkey_enabled.setAccessibleName("Begépelési gyorsbillentyű engedélyezése")
    w.quick_chat_hotkey_enabled = QCheckBox()
    w.quick_chat_hotkey_enabled.setAccessibleName("Gyors chat gyorsbillentyű engedélyezése")
    w.keep_chatgpt_in_background = QCheckBox("A ChatGPT maradjon háttérben, ne kapjon fókuszt")
    w.game_mode_enabled = QCheckBox("Játék mód csökkentse a háttérterhelést")
    w.screen_clip_hotkey = w._build_hotkey_edit()
    w.type_out_hotkey = w._build_hotkey_edit()
    w.quick_chat_hotkey = w._build_hotkey_edit()
    w.overlay_opacity_slider = QSlider(Qt.Orientation.Horizontal)
    w.overlay_opacity_slider.setRange(1, 100)
    w.overlay_opacity_slider.setPageStep(10)
    w.overlay_opacity_slider.valueChanged.connect(w._handle_overlay_opacity_slider_changed)
    w.overlay_opacity_value_label = label("10%")
    w.overlay_opacity_value_label.setFixedWidth(45)
    w.overlay_opacity_value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    w.overlay_duration_seconds = w._build_spin_box(maximum=120, step=1)
    w.overlay_duration_seconds.setMinimum(1)
    w.overlay_duration_seconds.setSuffix(" mp")
    w.status_label = label("Indulásra kész.", "secondaryText", wrap=True)
    w.last_run_label = label("Még nincs futási állapot.", "secondaryText", wrap=True)
    w.top_status_label = label("Indulásra kész.", "topStatusLabel")
    w.top_status_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
    w.current_url_label = label("", "originLabel")
    w.browser.urlChanged.connect(w._update_browser_origin_label)
    w.menu_button = button("Beállítások", "settings", w.toggle_drawer, "headerButton", 160)
    w.open_chatgpt_button = button("ChatGPT", "chatgpt", w._handle_open_chatgpt_button_clicked, "headerButton", 140)
    w.send_prompt_now_button = button("Prompt elküldése", "send", w.send_prompt_now, "accentHeaderButton", 218)
    w.send_prompt_now_button.setIcon(icon("send", color="#171717"))
    w.save_settings_button = button("Beállítások mentése", "download", w.save_settings, "primaryButton")
    w.save_settings_button.setIcon(icon("download", color="#171717"))
    w.reset_defaults_button = button("Alapértékek visszaállítása", "reset", w.reset_defaults)
    w.close_drawer_button = button("Bezárás", "close", w.close_drawer, width=148)
    w.open_logs_button = button("Naplómappa megnyitása", "document", w._open_log_directory)

    root = QWidget()
    root.setObjectName("rootSurface")
    root_layout = QVBoxLayout(root)
    root_layout.setContentsMargins(0, 0, 0, 0)
    root_layout.setSpacing(0)
    w.setCentralWidget(root)
    # A Windows saját címsora megtartja a natív átméretezést és ablakkezelést.
    w.window_title_label = label(APP_NAME, "windowTitleLabel")
    w.window_title_label.setParent(w)
    w.window_title_label.hide()
    w.window_icon_label = label("", "windowIconLabel")
    w.window_icon_label.setParent(w)
    w.window_icon_label.hide()
    w._load_title_icon()
    w.top_bar = QFrame()
    w.top_bar.setObjectName("topBar")
    w.top_bar.setFixedHeight(82)
    toolbar = QHBoxLayout(w.top_bar)
    toolbar.setContentsMargins(20, 13, 20, 13)
    toolbar.setSpacing(14)
    status = QFrame()
    status.setObjectName("topStatusFrame")
    status_row = QHBoxLayout(status)
    status_row.setContentsMargins(17, 0, 16, 0)
    status_row.setSpacing(13)
    status_row.addWidget(IconBadge("check", size=34))
    status_row.addWidget(w.top_status_label, 1)
    toolbar.addWidget(status, 1)
    toolbar.addWidget(w.open_chatgpt_button)
    toolbar.addWidget(w.menu_button)
    toolbar.addWidget(w.send_prompt_now_button)
    root_layout.addWidget(w.top_bar)
    # Az eredetjelző nem foglal külön sort; az automatizálás HTTPS-ellenőrzése megmarad.
    w.current_url_label.setParent(root)
    w.current_url_label.hide()
    body = QWidget()
    body_layout = QVBoxLayout(body)
    body_layout.setContentsMargins(18, 12, 18, 18)
    body_layout.setSpacing(0)
    w.content_surface = QFrame()
    w.content_surface.setObjectName("contentSurface")
    w.content_layout = QVBoxLayout(w.content_surface)
    w.content_layout.setContentsMargins(1, 1, 1, 1)
    w.content_layout.setSpacing(0)
    w.content_layout.addWidget(w.browser)
    w.browser.set_corner_radius(19)
    body_layout.addWidget(w.content_surface, 1)
    root_layout.addWidget(body, 1)
    w.browser_status_placeholder = QFrame(w.content_surface)
    w.browser_status_placeholder.hide()
    w.browser_status_title = label("")
    w.browser_status_body = label("")
    w.browser_status_hint = label("")
    # A meglévő életcikluskezelés ugyanazt a böngészőgazdát használja.
    w.frame_pulse_dot = QFrame(w.content_surface)
    w.frame_pulse_dot.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
    w.frame_pulse_dot.setFixedSize(1, 1)
    build_settings(w)
    w.content_edge = ContentEdge(w.content_surface)
    w.content_surface.installEventFilter(w)
    w._show_browser()


def build_settings(w) -> None:
    w.drawer_panel = AmbientPanel(w.content_surface, controller=False)
    w.drawer_panel.setObjectName("drawerPanel")
    w.drawer_panel.hide()
    layout = QVBoxLayout(w.drawer_panel)
    layout.setContentsMargins(16, 18, 16, 12)
    layout.setSpacing(14)
    header = QHBoxLayout()
    header.setSpacing(20)
    header.addWidget(IconBadge("settings", size=76))
    text = QVBoxLayout()
    text.setSpacing(4)
    text.addWidget(label("Beállítások", "settingsTitle"))
    text.addWidget(label("Szabd személyre a GPTTranslator működését.", "settingsSubtitle"))
    header.addLayout(text, 1)
    header.addWidget(w.close_drawer_button)
    layout.addLayout(header)
    w.drawer_scroll = QScrollArea()
    w.drawer_scroll.setWidgetResizable(True)
    w.drawer_scroll.setFrameShape(QFrame.Shape.NoFrame)
    content = QWidget()
    content.setObjectName("drawerContent")
    columns = QHBoxLayout(content)
    w.settings_columns = columns
    columns.setContentsMargins(0, 0, 0, 0)
    columns.setSpacing(14)
    w.general_settings_card, general = card(
        "Általános beállítások", "A program működésével kapcsolatos alapvető beállítások.", "settings"
    )
    general.setSpacing(8)
    active = QFrame()
    active.setObjectName("insetPanel")
    row = QHBoxLayout(active)
    row.setContentsMargins(16, 8, 16, 8)
    row.addWidget(IconBadge("gamepad", size=28))
    active_text = QVBoxLayout()
    active_text.setSpacing(3)
    active_text.addWidget(label("A program legyen aktív"))
    active_text.addWidget(label("A GPTTranslator fusson a háttérben.", "secondaryText"))
    row.addLayout(active_text, 1)
    row.addWidget(w.monitoring_enabled)
    general.addWidget(active)
    general.addWidget(label("Kézi prompt"))
    general.addWidget(w.prompt_template, 1)
    for control, description in (
        (w.copy_response_to_clipboard, "A fordítás eredménye automatikusan a vágólapra másolódik."),
        (w.ocr_text_from_clipboard_image, "OCR segítségével szöveg kinyerése a képekből."),
        (w.webview_gpu_acceleration_enabled, "Gyorsabb és folyamatosabb működés a támogatott rendszereken."),
        (w.nvidia_mouse_lag_fix_enabled, "A program saját NVIDIA-profiljában kikapcsolja a G-SYNC-et."),
        (w.screen_clip_hotkey_enabled, "A beépített Windows képkivágó megnyitása a képernyőképekhez."),
    ):
        general.addWidget(checkbox_row(control, description))
    columns.addWidget(w.general_settings_card, 1)
    right = QVBoxLayout()
    right.setSpacing(14)
    w.hotkey_settings_card, hotkeys = card(
        "Gyorsbillentyűk", "Állítsd be a leggyakrabban használt műveletek gyorsbillentyűit.", "keyboard"
    )
    inset = QFrame()
    inset.setObjectName("insetPanel")
    inset_layout = QVBoxLayout(inset)
    inset_layout.setContentsMargins(16, 6, 12, 6)
    inset_layout.setSpacing(0)
    for index, (title, description, edit, enabled) in enumerate((
        ("Képkivágási gyorsbillentyű", "A képernyőkép készítéséhez.", w.screen_clip_hotkey, None),
        ("Begépelési gyorsbillentyű", "A memóriába mentett fordítás begépelése.", w.type_out_hotkey, w.type_out_hotkey_enabled),
        ("Gyors chat gyorsbillentyű", "A gyors chat overlay megnyitása.", w.quick_chat_hotkey, w.quick_chat_hotkey_enabled),
    )):
        row = QHBoxLayout()
        row.setContentsMargins(0, 5, 0, 5)
        info = QVBoxLayout()
        info.setSpacing(4)
        info.addWidget(label(title))
        info.addWidget(label(description, "secondaryText", wrap=True))
        row.addLayout(info, 1)
        if enabled is not None:
            enabled.setToolTip(enabled.accessibleName())
            row.addWidget(enabled)
        edit.setMinimumWidth(150)
        edit.setMaximumWidth(200)
        row.addWidget(edit)
        inset_layout.addLayout(row)
        if index < 2:
            line = QFrame()
            line.setObjectName("separator")
            line.setFixedHeight(1)
            inset_layout.addWidget(line)
    hotkeys.addWidget(inset)
    right.addWidget(w.hotkey_settings_card)
    w.overlay_settings_card, overlay = card(
        "Overlay beállítások", "Az in-game overlay megjelenésének és viselkedésének beállításai.", "monitor"
    )
    inset = QFrame()
    inset.setObjectName("insetPanel")
    inset_layout = QVBoxLayout(inset)
    inset_layout.setContentsMargins(12, 6, 12, 6)
    inset_layout.setSpacing(0)
    inset_layout.addWidget(checkbox_row(w.keep_chatgpt_in_background, "A játék megszakítása nélkül fusson a háttérben."))
    inset_layout.addWidget(checkbox_row(w.game_mode_enabled, "Automatikusan optimalizálja a működést játék közben."))
    overlay.addWidget(inset)
    for title, description, control in (
        ("Overlay láthatósága", "Az overlay átlátszóságának mértéke.", w.overlay_opacity_slider),
        ("Overlay megjelenési ideje (másodperc)", "Mennyi ideig maradjon látható az overlay.", w.overlay_duration_seconds),
    ):
        row = QHBoxLayout()
        info = QVBoxLayout()
        info.setSpacing(4)
        info.addWidget(label(title))
        info.addWidget(label(description, "secondaryText", wrap=True))
        row.addLayout(info, 1)
        control.setMinimumWidth(170)
        control.setMaximumWidth(300)
        row.addWidget(control, 1)
        if control is w.overlay_opacity_slider:
            row.addWidget(w.overlay_opacity_value_label)
        overlay.addLayout(row)
    right.addWidget(w.overlay_settings_card, 1)
    columns.addLayout(right, 1)
    w.drawer_scroll.setWidget(content)
    layout.addWidget(w.drawer_scroll, 1)
    w.settings_footer = QFrame()
    w.settings_footer.setObjectName("settingsFooter")
    footer = QHBoxLayout(w.settings_footer)
    footer.setContentsMargins(16, 7, 6, 7)
    footer.setSpacing(14)
    footer.addWidget(IconBadge("activity", size=46))
    info = QVBoxLayout()
    info.setSpacing(2)
    info.addWidget(label("Állapot", "cardTitle"))
    info.addWidget(label("Az alkalmazás jelenlegi állapota.", "secondaryText"))
    footer.addLayout(info)
    state = QFrame()
    state.setObjectName("insetPanel")
    state_layout = QVBoxLayout(state)
    state_layout.setContentsMargins(14, 5, 14, 5)
    state_layout.setSpacing(1)
    state_layout.addWidget(w.last_run_label)
    state_layout.addWidget(w.status_label)
    footer.addWidget(state, 1)
    footer.addWidget(w.save_settings_button)
    footer.addWidget(w.reset_defaults_button)
    layout.addWidget(w.settings_footer)
    # A részletes napló továbbra is elérhető az állapotmező helyi menüjében.
    state.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    def status_menu(position):
        menu = QMenu(state)
        menu.addAction(w.open_logs_button.text(), w._open_log_directory)
        menu.exec(state.mapToGlobal(position))
    state.customContextMenuRequested.connect(status_menu)
