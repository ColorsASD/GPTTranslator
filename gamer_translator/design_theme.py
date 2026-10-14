"""Semleges szürke felületszínek és a referenciákhoz igazított méretek."""

STYLESHEET = """
QWidget { color: #ececec; font-family: 'Segoe UI'; font-size: 14px; }
#rootSurface { background: #141414; }
#topBar { background: #171717; border-bottom: 1px solid #292929; }
#topStatusFrame { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #242424,stop:1 #1b1b1b); border: 1px solid #383838; border-radius: 16px; }
#topStatusLabel { font-size: 16px; color: #d2d2d2; background: transparent; }
#originLabel { color: #c4c4c4; font-size: 13px; }
#sidebar { background: #171717; border: 1px solid #292929; border-radius: 16px; }
#contentSurface { background: #171717; border: 1px solid #323232; border-radius: 20px; }
QLabel { background: transparent; border: none; }
QPushButton { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #292929,stop:1 #212121); border: 1px solid #3b3b3b; border-radius: 14px; padding: 13px 18px; color: #ececec; }
QPushButton:hover { background: #333333; border-color: #575757; }
QPushButton:pressed { background: #1b1b1b; }
QPushButton:focus { border-color: #b5b5b5; }
QPushButton:disabled { color: #858585; background: #232323; }
#headerButton, #accentHeaderButton { min-height: 54px; max-height: 54px; padding: 0 10px; font-size: 15px; }
#accentHeaderButton, #primaryButton, #sendCircle { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #d0d0d0,stop:1 #aaaaaa); color: #171717; border: 1px solid #dedede; font-weight: 600; }
#accentHeaderButton:hover, #primaryButton:hover, #sendCircle:hover { background: #dedede; }
#accentHeaderButton:pressed, #primaryButton:pressed, #sendCircle:pressed { background: #999999; }
#avatarButton { border-radius: 28px; padding: 0; }
#modeTabs { background: #212121; border: 1px solid #353535; border-radius: 25px; }
#modeTab { background: transparent; border: 1px solid transparent; border-radius: 21px; color: #bcbcbc; padding: 10px 30px; font-size: 17px; }
#modeTab:checked { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #454545,stop:1 #323232); color: #f5f5f5; font-weight: 600; }
#modeTab:hover { color: #ffffff; }
#homeGreeting { font-size: 40px; font-weight: 700; color: #f5f5f5; }
#homeQuestion { font-size: 26px; color: #eeeeee; }
#homeHint { font-size: 17px; color: #b2b2b2; }
#homeComposer { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #272727,stop:1 #202020); border: 1px solid #484848; border-radius: 43px; }
#homeInput { border: none; background: transparent; font-size: 18px; padding: 6px; }
#homeInput:focus { border: none; }
#roundButton { border-radius: 28px; padding: 0; background: #333333; border: 1px solid #3c3c3c; }
#sendCircle { border-radius: 28px; padding: 0; }
#composerTool { padding: 8px 4px; background: transparent; border: none; color: #bfbfbf; font-size: 16px; }
#composerTool:hover { background: #333333; }
#poweredLabel { color: #a5a5a5; font-size: 14px; }
#ambientCaption { color: #858585; font-size: 11px; line-height: 22px; }
#separator { background: #444444; border: none; }
#drawerContent, QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; border: none; }
#settingsTitle { font-size: 32px; font-weight: 700; }
#settingsSubtitle { font-size: 17px; color: #d1d1d1; }
#settingsCard, #settingsFooter { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #292929,stop:1 #202020); border: 1px solid #393939; border-radius: 16px; }
#insetPanel { background: rgba(20,20,20,55); border: 1px solid #3b3b3b; border-radius: 13px; }
#cardTitle { font-size: 18px; font-weight: 700; }
#secondaryText { color: #b6b6b6; font-size: 13px; }
QLineEdit, QPlainTextEdit, QSpinBox { background: #171717; color: #eeeeee; border: 1px solid #3c3c3c; border-radius: 12px; padding: 10px 16px; selection-background-color: #666666; }
QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus { border-color: #949494; }
QPlainTextEdit { font-size: 14px; }
QSpinBox::up-button, QSpinBox::down-button { width: 16px; border: none; background: transparent; }
QCheckBox { color: #ececec; spacing: 20px; }
QCheckBox::indicator { width: 28px; height: 28px; border-radius: 8px; border: 1px solid #666666; background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #626262,stop:1 #505050); }
QCheckBox::indicator:checked { background: #bcbcbc; border-color: #dddddd; image: url("CHECK_MARK_ASSET"); }
QCheckBox::indicator:unchecked:hover { border-color: #c0c0c0; }
QSlider::groove:horizontal { background: #535353; height: 6px; border-radius: 3px; }
QSlider::sub-page:horizontal { background: #bababa; border-radius: 3px; }
QSlider::handle:horizontal { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #d2d2d2,stop:1 #aaaaaa); border: 1px solid #dddddd; width: 24px; margin: -10px 0; border-radius: 12px; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 3px; }
QScrollBar::handle:vertical { background: #626262; min-height: 30px; border-radius: 3px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { height: 0; }
QMenu { background: #242424; color: #ececec; border: 1px solid #484848; padding: 5px; }
QMenu::item { padding: 9px 18px; }
QMenu::item:selected { background: #414141; border-radius: 5px; }
"""
