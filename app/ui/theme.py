MAIN_QSS = r'''
* { font-family: "Segoe UI"; }
QMainWindow, QWidget { background: #F5F7F9; color: #18232D; }
QFrame#Sidebar { background: #0F1720; border-right: 1px solid #1D2934; }
QLabel#BrandMark { background: #DDF6EC; color: #1B7657; min-width: 30px; max-width: 30px; min-height: 30px; max-height: 30px; border-radius: 15px; qproperty-alignment: AlignCenter; font-size: 15px; font-weight: 700; }
QLabel#Brand { color: #F7FAFC; font-size: 21px; font-weight: 700; }
QLabel#BrandSub { color: #73808C; font-size: 9px; font-weight: 700; padding-left: 4px; }
QLabel#SidebarSection { color: #687784; font-size: 9px; font-weight: 700; padding: 10px 9px 3px; }
QPushButton#Nav { background: transparent; color: #AEB9C3; border: 0; border-radius: 10px; text-align: left; padding: 11px 12px; font-size: 12px; font-weight: 600; }
QPushButton#Nav:hover { background: #18232E; color: #F7FAFC; }
QPushButton#Nav:checked { background: #21313E; color: #F7FAFC; }
QLabel#SidebarStatus { color: #98A6B2; font-size: 10px; background: #151F28; border: 1px solid #263440; border-radius: 9px; padding: 8px 10px; }
QLabel#SidebarStatus[state="ok"] { color: #B9E7D2; background: #12261F; border-color: #254B3D; }
QFrame#Topbar { background: #FFFFFF; border-bottom: 1px solid #E4E9EE; }
QLabel#Eyebrow { color: #70808D; font-size: 9px; font-weight: 700; }
QLabel#PageTitle { color: #18232D; font-size: 27px; font-weight: 700; }
QLabel#PageSubtitle { color: #667582; font-size: 12px; }
QLabel#HeroTitle { color: #14212B; font-size: 28px; font-weight: 700; }
QLabel#HeroSubtitle { color: #5F707D; font-size: 12px; }
QFrame#Hero { background: #EAF6F1; border: 1px solid #D7EEE4; border-radius: 18px; }
QLabel#SectionTitle { color: #1C2934; font-size: 14px; font-weight: 700; }
QLabel#CardDescription { color: #798793; font-size: 10px; }
QLabel#FieldLabel { color: #647482; font-size: 10px; font-weight: 700; }
QLabel#Hint { color: #84919C; font-size: 10px; }
QLabel#ActionNote { color: #6E7C88; font-size: 10px; }
QFrame#Card { background: #FFFFFF; border: 1px solid #E2E8ED; border-radius: 15px; }
QFrame#ActionBar { background: #FFFFFF; border: 1px solid #DFE6EB; border-radius: 14px; }
QFrame#Metric { background: #FFFFFF; border: 1px solid #E2E8ED; border-radius: 13px; }
QLabel#MetricNumber { color: #14212B; font-size: 21px; font-weight: 700; }
QLabel#MetricLabel { color: #7A8792; font-size: 9px; font-weight: 700; }
QLabel#Pill { background: #EEF8F4; color: #187455; border: 1px solid #D7EEE4; border-radius: 10px; padding: 6px 9px; font-size: 10px; font-weight: 700; }
QLineEdit, QComboBox, QSpinBox { background: #FFFFFF; color: #17242F; border: 1px solid #D5DEE5; border-radius: 9px; padding: 9px 10px; font-size: 11px; min-height: 18px; }
QLineEdit:hover, QComboBox:hover, QSpinBox:hover { border-color: #B7C6D1; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 1px solid #39A77D; }
QComboBox::drop-down { border: 0; width: 24px; }
QCheckBox { color: #50606E; spacing: 7px; font-size: 11px; }
QCheckBox::indicator { width: 16px; height: 16px; background: #FFFFFF; border: 1px solid #CAD4DC; border-radius: 5px; }
QCheckBox::indicator:checked { background: #2E9D73; border-color: #2E9D73; }
QPushButton#Primary { background: #1E7C59; color: #FFFFFF; border: 0; border-radius: 10px; padding: 10px 16px; font-size: 11px; font-weight: 700; }
QPushButton#Primary:hover { background: #176A4C; }
QPushButton#Primary:disabled { background: #AFCBBE; }
QPushButton#Secondary { background: #FFFFFF; color: #334350; border: 1px solid #D5DEE5; border-radius: 9px; padding: 9px 13px; font-size: 10px; font-weight: 700; }
QPushButton#Secondary:hover { background: #F6F8FA; }
QScrollArea { border: 0; background: transparent; }
QTableWidget { background: #FFFFFF; border: 0; gridline-color: #EEF1F3; alternate-background-color: #FBFCFD; selection-background-color: #EAF6F1; selection-color: #18232D; }
QHeaderView::section { background: #F6F8FA; color: #74828E; border: 0; border-bottom: 1px solid #E8EDF1; padding: 10px 8px; font-size: 9px; font-weight: 700; }
QTableWidget::item { padding: 9px 8px; border-bottom: 1px solid #F1F3F5; }
QTextBrowser { background: transparent; border: 0; color: #566773; font-size: 11px; }
'''
