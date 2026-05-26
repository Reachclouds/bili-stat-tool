MAIN_STYLE = """
/* ===== 主窗口 ===== */
QMainWindow {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #e8edf5, stop:1 #d5dce8);
}

/* ===== 卡片容器 ===== */
QGroupBox {
    font-weight: bold;
    font-size: 13px;
    border: 1px solid rgba(200, 210, 225, 0.6);
    border-radius: 12px;
    margin-top: 18px;
    padding: 18px 15px 12px 15px;
    background: rgba(255, 255, 255, 0.85);
    color: #2c3e50;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 18px;
    padding: 0 8px;
    color: #34495e;
    font-size: 13px;
}

/* ===== 按钮通用 ===== */
QPushButton {
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: bold;
    font-size: 12px;
    color: white;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #5b8def, stop:1 #3a6fd8);
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #6e9df5, stop:1 #4a80e8);
}
QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #3a6fd8, stop:1 #2a5bc0);
}
QPushButton:disabled {
    background: #c5cdd9;
    color: #8a95a5;
}

/* ===== 危险按钮（停止、确认排除等） ===== */
QPushButton[cssClass="danger"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #ef6b6b, stop:1 #d94444);
}
QPushButton[cssClass="danger"]:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #f28080, stop:1 #e55555);
}
QPushButton[cssClass="danger"]:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #d94444, stop:1 #c03030);
}

/* ===== 次要按钮（Cookie设置、帮助等） ===== */
QPushButton[cssClass="secondary"] {
    background: rgba(255, 255, 255, 0.75);
    color: #34495e;
    border: 1px solid #c8d2e1;
}
QPushButton[cssClass="secondary"]:hover {
    background: rgba(255, 255, 255, 0.95);
    border: 1px solid #5b8def;
    color: #3a6fd8;
}
QPushButton[cssClass="secondary"]:pressed {
    background: #e8edf5;
}

/* ===== 输入框、日期选择 ===== */
QLineEdit, QDateEdit, QTextEdit, QComboBox {
    border: 1px solid #c8d2e1;
    border-radius: 8px;
    padding: 6px 10px;
    background: rgba(255, 255, 255, 0.9);
    color: #2c3e50;
    selection-background-color: #5b8def;
}
QLineEdit:focus, QDateEdit:focus, QTextEdit:focus, QComboBox:focus {
    border: 2px solid #5b8def;
    padding: 5px 9px;
}
QDateEdit::drop-down {
    border: none;
    border-left: 1px solid #c8d2e1;
    width: 28px;
    background: #e8edf5;
    border-top-right-radius: 7px;
    border-bottom-right-radius: 7px;
}
QDateEdit::drop-down:hover {
    background: #5b8def;
}
QComboBox::drop-down {
    border: none;
    width: 28px;
}
QComboBox QAbstractItemView {
    border: 1px solid #c8d2e1;
    border-radius: 6px;
    background: white;
    selection-background-color: #e8edf5;
    selection-color: #2c3e50;
    padding: 4px;
}

/* ===== 表格 ===== */
QTableWidget {
    gridline-color: transparent;
    border: 1px solid rgba(200, 210, 225, 0.6);
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.85);
    alternate-background-color: #f4f7fb;
    selection-background-color: #dce6f7;
    selection-color: #2c3e50;
    font-size: 12px;
}
QTableWidget::item {
    padding: 8px 10px;
    border-bottom: 1px solid #eef1f6;
}
QTableWidget::item:hover {
    background: #e8edf5;
}
QHeaderView::section {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #f0f3f8, stop:1 #e4e9f2);
    padding: 8px 6px;
    border: none;
    border-bottom: 2px solid #d0d8e6;
    border-right: 1px solid #e4e9f2;
    font-weight: bold;
    color: #34495e;
    font-size: 12px;
}

/* ===== 标签 ===== */
QLabel {
    color: #34495e;
    font-size: 12px;
}

/* ===== 分割线 ===== */
QSplitter::handle {
    background: #d0d8e6;
    width: 1px;
}

/* ===== 滚动条 ===== */
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 8px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #c0c8d6;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #a0aab8;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    border: none;
    background: transparent;
    height: 8px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: #c0c8d6;
    border-radius: 4px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background: #a0aab8;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ===== 复选框 ===== */
QCheckBox {
    spacing: 6px;
    color: #34495e;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #c0c8d6;
    border-radius: 4px;
    background: white;
}
QCheckBox::indicator:checked {
    background: #5b8def;
    border-color: #5b8def;
}
QCheckBox::indicator:hover {
    border-color: #5b8def;
}

/* ===== 工具提示 ===== */
QToolTip {
    background: #2c3e50;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 11px;
}
"""
