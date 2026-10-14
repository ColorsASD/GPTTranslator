"""A Gamer Translator szürke, natív kezdőlapja és beállítási felülete."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QCheckBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QMenu,
    QPlainTextEdit, QPushButton, QScrollArea, QSizePolicy, QSlider,
    QVBoxLayout, QWidget,
)

from .defaults import APP_NAME
from .design_widgets import AmbientPanel, IconBadge, NavButton, SuggestionCard, ToggleSwitch, icon


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
    w.current_url_label.setContentsMargins(20, 3, 20, 5)
    w.current_url_label.setMinimumHeight(28)
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
    # Az eredet az új kezdőlap és a beállítások mellett is látható marad.
    root_layout.addWidget(w.current_url_label)
    body = QWidget()
    body_layout = QHBoxLayout(body)
    body_layout.setContentsMargins(10, 0, 18, 18)
    body_layout.setSpacing(20)
    w.sidebar = QFrame()
    w.sidebar.setObjectName("sidebar")
    w.sidebar.setFixedWidth(96)
    nav_layout = QVBoxLayout(w.sidebar)
    nav_layout.setContentsMargins(4, 6, 4, 18)
    nav_layout.setSpacing(8)
    w.nav_buttons = {}
    for key, text, symbol in (
        ("home", "Kezdőlap", "home"), ("history", "Előzmények", "history"),
        ("discover", "Felfedezés", "compass"), ("profile", "Profil", "profile"),
        ("settings", "Egyebek", "grid"),
    ):
        if key == "settings":
            line = QFrame()
            line.setObjectName("separator")
            line.setFixedHeight(1)
            nav_layout.addSpacing(10)
            nav_layout.addWidget(line)
            nav_layout.addSpacing(10)
        item = NavButton(text, symbol)
        item.clicked.connect(lambda checked=False, section=key: w._navigate_shell(section))
        nav_layout.addWidget(item)
        w.nav_buttons[key] = item
    nav_layout.addStretch(1)
    avatar = button("E", "", lambda: w._navigate_shell("profile"), "avatarButton")
    avatar.setFixedSize(56, 56)
    avatar.setAccessibleName("ChatGPT profil")
    nav_layout.addWidget(avatar, 0, Qt.AlignmentFlag.AlignHCenter)
    body_layout.addWidget(w.sidebar)
    w.content_surface = QFrame()
    w.content_surface.setObjectName("contentSurface")
    w.content_layout = QVBoxLayout(w.content_surface)
    w.content_layout.setContentsMargins(1, 1, 1, 1)
    w.content_layout.setSpacing(0)
    w.content_layout.addWidget(w.browser)
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
    build_home(w)
    build_settings(w)
    w._shell_page = "home"
    w._home_mode = "chat"
    w._show_home()


def build_home(w) -> None:
    w.home_panel = AmbientPanel(w.content_surface)
    layout = QVBoxLayout(w.home_panel)
    layout.setContentsMargins(36, 20, 36, 22)
    layout.setSpacing(0)
    tabs = QFrame()
    tabs.setObjectName("modeTabs")
    tabs.setFixedSize(296, 50)
    tab_layout = QHBoxLayout(tabs)
    tab_layout.setContentsMargins(2, 2, 2, 2)
    tab_layout.setSpacing(0)
    w.chat_tab_button = QPushButton("Chat")
    w.work_tab_button = QPushButton("Work")
    for control, mode in ((w.chat_tab_button, "chat"), (w.work_tab_button, "work")):
        control.setObjectName("modeTab")
        control.setCheckable(True)
        control.setCursor(Qt.CursorShape.PointingHandCursor)
        control.clicked.connect(lambda checked=False, selected=mode: w._set_home_mode(selected))
        tab_layout.addWidget(control)
    w.chat_tab_button.setChecked(True)
    layout.addWidget(tabs, 0, Qt.AlignmentFlag.AlignHCenter)
    layout.addStretch(2)
    logo = QLabel()
    logo.setPixmap(icon("chatgpt", size=84).pixmap(84, 84))
    logo.setFixedSize(84, 84)
    w.home_logo = logo
    layout.addWidget(logo, 0, Qt.AlignmentFlag.AlignHCenter)
    layout.addSpacing(18)
    w.home_greeting = label("Jó újra látni, Erik!", "homeGreeting")
    w.home_greeting.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(w.home_greeting)
    layout.addSpacing(8)
    w.home_question = label("Miben segíthetek ma?", "homeQuestion")
    w.home_question.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(w.home_question)
    layout.addSpacing(5)
    hint = label("Kérdezz bátran, fordíttass, elemezz, vagy kérj segítséget a játékok világában.", "homeHint", wrap=True)
    hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
    w.home_hint = hint
    layout.addWidget(hint)
    layout.addSpacing(38)
    composer = QFrame()
    w.home_composer = composer
    composer.setObjectName("homeComposer")
    composer.setMinimumHeight(86)
    composer.setMaximumWidth(930)
    composer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    composer_row = QHBoxLayout(composer)
    composer_row.setContentsMargins(17, 10, 17, 10)
    composer_row.setSpacing(18)
    w.home_attach_button = button("", "plus", w._show_capture_menu, "roundButton")
    w.home_attach_button.setFixedSize(56, 56)
    w.home_attach_button.setAccessibleName("Kép fordítása")
    w.home_attach_button.setToolTip("Képkivágás fordítása")
    composer_row.addWidget(w.home_attach_button)
    w.home_input = QLineEdit()
    w.home_input.setObjectName("homeInput")
    w.home_input.setPlaceholderText("Kérdezz a ChatGPT-től...")
    w.home_input.setAccessibleName("Üzenet a ChatGPT-nek")
    w.home_input.returnPressed.connect(w._submit_home_text)
    composer_row.addWidget(w.home_input, 1)
    model_button = button("ChatGPT", "chevron_down", w._show_browser, "composerTool")
    model_button.setToolTip("A ChatGPT oldal megnyitása és modellválasztás")
    composer_row.addWidget(model_button)
    w.home_voice_button = button("", "microphone", w._open_voice_input, "composerTool")
    w.home_voice_button.setToolTip("Hangbevitel megnyitása a ChatGPT-ben")
    w.home_voice_button.setAccessibleName("ChatGPT hangbevitel")
    composer_row.addWidget(w.home_voice_button)
    w.home_send_button = button("", "arrow_up", w._submit_home_text, "sendCircle")
    w.home_send_button.setIcon(icon("arrow_up", color="#171717", size=30))
    w.home_send_button.setIconSize(QSize(30, 30))
    w.home_send_button.setFixedSize(56, 56)
    w.home_send_button.setAccessibleName("Üzenet elküldése")
    composer_row.addWidget(w.home_send_button)
    layout.addWidget(composer, 0, Qt.AlignmentFlag.AlignHCenter)
    layout.addSpacing(28)
    cards = QWidget()
    w.home_cards_container = cards
    cards.setMaximumWidth(1290)
    cards_layout = QHBoxLayout(cards)
    cards_layout.setContentsMargins(0, 0, 0, 0)
    cards_layout.setSpacing(18)
    w.suggestion_cards = []
    for index, (title, description, symbol) in enumerate((
        ("Játékfordítás", "Fordítsd le ezt a játékszöveget magyarra.", "gamepad"),
        ("Patch note összefoglaló", "Foglald össze a legújabb frissítés főbb változásait.", "document"),
        ("Stratégiai tippek", "Adj tippeket egy nehéz boss fight-hoz.", "bulb"),
        ("Nyelvi segítség", "Magyarázd el a játékszakszavak jelentését.", "language"),
    )):
        item = SuggestionCard(title, description, symbol)
        item.clicked.connect(lambda checked=False, selected=index: w._use_suggestion(selected))
        cards_layout.addWidget(item, 1)
        w.suggestion_cards.append(item)
    layout.addWidget(cards, 0, Qt.AlignmentFlag.AlignHCenter)
    layout.addStretch(3)
    footer = QHBoxLayout()
    footer.setSpacing(20)
    for item in (QFrame(), label("Powered by ChatGPT", "poweredLabel"), QFrame()):
        if isinstance(item, QFrame) and not isinstance(item, QLabel):
            item.setObjectName("separator")
            item.setFixedSize(170, 1)
        footer.addWidget(item)
    footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addLayout(footer)
    layout.addSpacing(30)
    w.home_top_caption = label("A J Á T É K O K\nN Y E L V É N .\nM I N D I G  V E L E D .", "ambientCaption")
    w.home_bottom_caption = label("J Á T É K O K .\nE M B E R E K .\nN Y E L V E K  Ö S S Z E K Ö T N E K .", "ambientCaption")
    for caption in (w.home_top_caption, w.home_bottom_caption):
        caption.setParent(w.home_panel)
        caption.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        caption.show()


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
    text.addWidget(label("Szabd személyre a Gamer Translator működését.", "settingsSubtitle"))
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
    active_text.addWidget(label("A Gamer Translator fusson a háttérben.", "secondaryText"))
    row.addLayout(active_text, 1)
    row.addWidget(w.monitoring_enabled)
    general.addWidget(active)
    general.addWidget(label("Kézi prompt"))
    general.addWidget(w.prompt_template, 1)
    for control, description in (
        (w.copy_response_to_clipboard, "A fordítás eredménye automatikusan a vágólapra másolódik."),
        (w.ocr_text_from_clipboard_image, "OCR segítségével szöveg kinyerése a képekből."),
        (w.webview_gpu_acceleration_enabled, "Gyorsabb és folyamatosabb működés a támogatott rendszereken."),
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
