"""PyQt6 GUI - 侧边栏导航 + 分段配置页"""

import logging
from typing import Callable

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPalette, QTextCursor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QStackedWidget,
    QFrame,
    QButtonGroup,
)

from ..config.loader import ConfigLoader
from ..config.schema import AppConfig
from ..utils.logging import _CSTFormatter

logger = logging.getLogger(__name__)

# ── 样式常量 ──
FONT_FAMILY = "Segoe UI"
SIDEBAR_W = 62

# 颜色
ACCENT = "#3B82F6"
ACCENT_HOVER = "#2563EB"
SUCCESS_FG = "#16A34A"
ERROR_FG = "#DC2626"
MUTED_FG = "#9CA3AF"

# 浅色主题
LIGHT_PALETTE = {
    QPalette.ColorRole.Window: "#FFFFFF",
    QPalette.ColorRole.WindowText: "#1F2937",
    QPalette.ColorRole.Base: "#FFFFFF",
    QPalette.ColorRole.AlternateBase: "#F3F4F6",
    QPalette.ColorRole.Text: "#1F2937",
    QPalette.ColorRole.Button: "#F3F4F6",
    QPalette.ColorRole.ButtonText: "#1F2937",
    QPalette.ColorRole.Highlight: ACCENT,
    QPalette.ColorRole.HighlightedText: "#FFFFFF",
    QPalette.ColorRole.ToolTipBase: "#1F2937",
    QPalette.ColorRole.ToolTipText: "#F9FAFB",
    QPalette.ColorRole.PlaceholderText: "#9CA3AF",
    QPalette.ColorRole.Mid: "#D1D5DB",
}

# 深色主题（柔和灰，不偏蓝黑）
DARK_PALETTE = {
    QPalette.ColorRole.Window: "#2D2D30",
    QPalette.ColorRole.WindowText: "#E0E0E0",
    QPalette.ColorRole.Base: "#3C3C3C",
    QPalette.ColorRole.AlternateBase: "#444444",
    QPalette.ColorRole.Text: "#E0E0E0",
    QPalette.ColorRole.Button: "#454545",
    QPalette.ColorRole.ButtonText: "#E0E0E0",
    QPalette.ColorRole.Highlight: ACCENT,
    QPalette.ColorRole.HighlightedText: "#FFFFFF",
    QPalette.ColorRole.ToolTipBase: "#454545",
    QPalette.ColorRole.ToolTipText: "#E0E0E0",
    QPalette.ColorRole.PlaceholderText: "#888888",
    QPalette.ColorRole.Mid: "#606060",
}

# QSS
STYLE_COMMON = """
    QPushButton {
        border: none;
        border-radius: 6px;
        padding: 4px 12px;
    }
    QPushButton:hover { background: rgba(128,128,128,0.12); }
    QLineEdit, QComboBox {
        border: 1px solid palette(mid);
        border-radius: 4px;
        padding: 4px 8px;
        min-height: 28px;
    }
    QLineEdit:focus, QComboBox:focus {
        border-color: """ + ACCENT + """;
    }
    QComboBox::drop-down {
        border: none;
        width: 20px;
    }
    QTableWidget {
        gridline-color: palette(mid);
        selection-background-color: """ + ACCENT + """33;
        alternate-background-color: palette(alternate-base);
    }
    QTableWidget::item { padding: 4px; }
    QHeaderView::section {
        background: palette(button);
        padding: 6px;
        border: none;
        border-bottom: 2px solid """ + ACCENT + """;
        font-weight: bold;
    }
    QTextEdit {
        border: 1px solid palette(mid);
        border-radius: 4px;
        padding: 4px;
    }
    QStatusBar {
        border-top: 1px solid palette(mid);
    }
"""

SIDEBAR_LIGHT = "QFrame#sidebar { background: #F0F0F0; border-right: 1px solid #D1D5DB; }"
SIDEBAR_DARK = "QFrame#sidebar { background: #242424; border-right: 1px solid #444444; }"

SECTION_NAMES = ["通用", "LLM"]


def _build_palette(mapping: dict) -> QPalette:
    pal = QPalette()
    for role, color in mapping.items():
        pal.setColor(role, QColor(color))
    return pal


def _apply_theme(dark: bool) -> None:
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        return
    pal = _build_palette(DARK_PALETTE if dark else LIGHT_PALETTE)
    app.setPalette(pal)
    sidebar_css = SIDEBAR_DARK if dark else SIDEBAR_LIGHT
    app.setStyleSheet(STYLE_COMMON + sidebar_css)


# ── 自定义组件 ──

class SegmentedGroup(QWidget):
    """分段选择器，模拟 CTkSegmentedButton"""

    def __init__(self, labels: list[str], parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._buttons: list[QPushButton] = []
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        for i, label in enumerate(labels):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setMinimumHeight(30)
            self._group.addButton(btn, i)
            layout.addWidget(btn)
            self._buttons.append(btn)
        self._group.idClicked.connect(self._on_clicked)
        self._callback = None

    def on_change(self, callback) -> None:
        self._callback = callback

    def set_current(self, index: int) -> None:
        if 0 <= index < len(self._buttons):
            self._buttons[index].setChecked(True)
            self._update_styles(index)

    def _on_clicked(self, idx: int) -> None:
        self._update_styles(idx)
        if self._callback:
            self._callback(idx)

    def _update_styles(self, active: int) -> None:
        for i, btn in enumerate(self._buttons):
            if i == active:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {ACCENT};
                        color: white;
                        border-radius: 4px;
                        font-weight: bold;
                    }}
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        border-radius: 4px;
                    }
                """)


# ── 标签列表组件 ──

TAG_STYLE = """
    QPushButton {
        background: palette(button);
        border: 1px solid palette(mid);
        border-radius: 12px;
        padding: 3px 8px;
        font-size: 12px;
    }
    QPushButton:hover {
        background: palette(alternate-base);
    }
"""

TAG_CLOSE_STYLE = """
    QPushButton {
        background: transparent;
        border: none;
        border-radius: 8px;
        padding: 0px;
        font-size: 11px;
        color: palette(window-text);
    }
    QPushButton:hover {
        background: rgba(220, 38, 38, 0.15);
        color: #DC2626;
    }
"""


class TagListWidget(QWidget):
    """标签列表组件：每个标签一个可删除的 chip + 底部添加行"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tags: list[str] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # 标签区域
        self._tag_container = QWidget()
        self._tag_layout = QHBoxLayout(self._tag_container)
        self._tag_layout.setContentsMargins(0, 0, 0, 0)
        self._tag_layout.setSpacing(6)
        self._tag_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._tag_layout.addStretch()
        layout.addWidget(self._tag_container)

        # 添加行
        add_row = QHBoxLayout()
        add_row.setSpacing(6)
        self._input = QLineEdit()
        self._input.setPlaceholderText("输入新标签，回车添加")
        self._input.setMaxLength(30)
        self._input.returnPressed.connect(self._on_add)
        add_row.addWidget(self._input, 1)

        self._add_btn = QPushButton("添加")
        self._add_btn.setFixedWidth(56)
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.setStyleSheet(f"background: {ACCENT}; color: white; border-radius: 4px; padding: 4px 8px;")
        self._add_btn.clicked.connect(self._on_add)
        add_row.addWidget(self._add_btn)
        layout.addLayout(add_row)

    def labels(self) -> list[str]:
        return list(self._tags)

    def set_labels(self, tags: list[str]) -> None:
        self._tags = list(tags)
        self._rebuild()

    def _on_add(self) -> None:
        text = self._input.text().strip()
        if text and text not in self._tags:
            self._tags.append(text)
            self._insert_tag_chip(len(self._tags) - 1, text)
            self._input.clear()

    def _on_remove(self, tag: str) -> None:
        if tag in self._tags:
            self._tags.remove(tag)
            self._rebuild()

    def _rebuild(self) -> None:
        while self._tag_layout.count() > 1:
            item = self._tag_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        for i, tag in enumerate(self._tags):
            self._insert_tag_chip(i, tag)

    def _insert_tag_chip(self, index: int, tag: str) -> None:
        chip = QWidget()
        row = QHBoxLayout(chip)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(2)

        label = QLabel(tag)
        label.setStyleSheet("background: transparent; border: none; font-size: 12px;")
        row.addWidget(label)

        close = QPushButton("×")
        close.setFixedSize(18, 18)
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.setStyleSheet(TAG_CLOSE_STYLE)
        close.clicked.connect(lambda _, t=tag: self._on_remove(t))
        row.addWidget(close)

        chip.setStyleSheet(TAG_STYLE)
        chip.setCursor(Qt.CursorShape.ArrowCursor)

        self._tag_layout.insertWidget(index, chip)


# ── GUIApp ──

class GUIApp(QMainWindow):
    """PyQt6 GUI 应用"""

    def __init__(
        self,
        config_loader: ConfigLoader,
        on_config_saved: Callable[[AppConfig], None],
        on_rollback: Callable[[int], bool],
        on_refresh: Callable[[], list[dict]],
        on_delete: Callable[[list[int]], int] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._config_loader = config_loader
        self._on_config_saved = on_config_saved
        self._on_rollback = on_rollback
        self._on_refresh = on_refresh
        self._on_delete = on_delete
        self._is_dark = False

        # 配置字段 widgets
        self._fields: dict[str, QLineEdit | QComboBox | QCheckBox] = {}

        # 导航按钮
        self._nav_buttons: list[QPushButton] = []

        # 持久化日志 handler（必须在 _build_layout 之前初始化）
        self._text_handler = QtTextHandler()
        self._text_handler.setFormatter(
            _CSTFormatter("[%(asctime)s] %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
        )
        logging.getLogger("paper_tool").addHandler(self._text_handler)

        self.setWindowTitle("Paper Tool")
        self.setMinimumSize(780, 540)
        self.resize(960, 720)

        # 检测系统主题
        self._detect_system_theme()

        # 构建布局
        self._build_layout()
        self._navigate(0)

    # ── 生命周期 ──

    def start(self) -> None:
        self.show()

    def stop(self) -> None:
        self.close()

    # ── 主题 ──

    def _detect_system_theme(self) -> None:
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app and app.styleHints().colorScheme() == Qt.ColorScheme.Dark:
                self._is_dark = True
            else:
                self._is_dark = False
        except Exception:
            self._is_dark = False
        _apply_theme(self._is_dark)

    def _toggle_theme(self) -> None:
        self._is_dark = not self._is_dark
        _apply_theme(self._is_dark)

    # ── 主布局 ──

    def _build_layout(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 侧边栏
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(SIDEBAR_W)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(6, 12, 6, 12)
        sidebar_layout.setSpacing(4)

        logo = QLabel("PT")
        logo.setFont(QFont(FONT_FAMILY, 14, QFont.Weight.Bold))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet(f"color: {ACCENT};")
        sidebar_layout.addWidget(logo)
        sidebar_layout.addSpacing(12)

        pages = ["⚙", "☰", "≡"]
        for i, symbol in enumerate(pages):
            btn = QPushButton(symbol)
            btn.setFixedSize(44, 40)
            btn.setFont(QFont(FONT_FAMILY, 16))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, idx=i: self._navigate(idx))
            sidebar_layout.addWidget(btn)
            self._nav_buttons.append(btn)

        sidebar_layout.addStretch()

        theme_btn = QPushButton("◐")
        theme_btn.setFixedSize(44, 40)
        theme_btn.setFont(QFont(FONT_FAMILY, 14))
        theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        theme_btn.clicked.connect(self._toggle_theme)
        sidebar_layout.addWidget(theme_btn)

        main_layout.addWidget(sidebar)

        # 内容区 QStackedWidget
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_config_page())   # index 0
        self._stack.addWidget(self._build_operations_page()) # index 1
        self._stack.addWidget(self._build_logs_page())       # index 2
        main_layout.addWidget(self._stack, 1)

        # 状态栏
        config = self._config_loader.config
        status = QStatusBar()
        status.setFixedHeight(28)
        self.setStatusBar(status)
        status.showMessage(f"  ● 监控中  |  后端: {config.llm_backend}")

    def _navigate(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_buttons):
            if i == index:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: rgba(59, 130, 246, 0.15);
                        border-radius: 8px;
                        color: {ACCENT};
                    }}
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        border-radius: 8px;
                    }
                    QPushButton:hover { background: rgba(0,0,0,0.06); }
                """)

    # ── 配置页 ──

    def _build_config_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 12, 16, 12)

        title = QLabel("配置")
        title.setFont(QFont(FONT_FAMILY, 14, QFont.Weight.Bold))
        layout.addWidget(title)

        hint = QLabel("修改后点击「保存配置」生效")
        hint.setStyleSheet(f"color: {MUTED_FG};")
        layout.addWidget(hint)
        layout.addSpacing(4)

        # 分段
        self._config_seg = SegmentedGroup(SECTION_NAMES)
        self._config_seg.on_change(self._on_seg_change)
        layout.addWidget(self._config_seg)
        layout.addSpacing(6)

        # 段容器
        self._seg_stack = QStackedWidget()
        self._seg_stack.addWidget(self._build_seg_general())  # 0
        self._seg_stack.addWidget(self._build_seg_llm())      # 1
        layout.addWidget(self._seg_stack, 1)

        # 底部按钮
        btn_row = QHBoxLayout()
        save_btn = QPushButton("保存配置")
        save_btn.setStyleSheet(f"background: {ACCENT}; color: white; border-radius: 4px; padding: 6px 20px;")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._save_config)
        btn_row.addWidget(save_btn)

        reset_btn = QPushButton("重置为当前值")
        reset_btn.setStyleSheet("border: 1px solid palette(mid); border-radius: 4px; padding: 6px 20px;")
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.clicked.connect(self._reset_config)
        btn_row.addWidget(reset_btn)

        self._config_status = QLabel("")
        btn_row.addWidget(self._config_status)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._init_all_fields()
        self._config_seg.set_current(0)

        return page

    def _on_seg_change(self, idx: int) -> None:
        self._seg_stack.setCurrentIndex(idx)

    def _section_header(self, layout: QVBoxLayout, title: str) -> None:
        label = QLabel(title)
        label.setFont(QFont(FONT_FAMILY, 12, QFont.Weight.Bold))
        label.setStyleSheet(f"color: {ACCENT};")
        layout.addWidget(label)
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background: palette(mid);")
        layout.addWidget(line)
        layout.addSpacing(4)

    def _add_field(self, form: QFormLayout, label: str, key: str, widget=None) -> QWidget:
        if widget is not None:
            w = widget
        else:
            w = QLineEdit()
        self._fields[key] = w
        form.addRow(label, w)
        return w

    def _add_combo_field(self, form: QFormLayout, label: str, key: str, values: list[str]) -> QComboBox:
        combo = QComboBox()
        combo.addItems(values)
        combo.setEditable(False)
        self._fields[key] = combo
        form.addRow(label, combo)
        return combo

    def _add_dir_field(self, form: QFormLayout, label: str, key: str) -> QWidget:
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        entry = QLineEdit()
        self._fields[key] = entry
        h.addWidget(entry, 1)
        browse_btn = QPushButton("浏览")
        browse_btn.setFixedWidth(56)
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        def _browse():
            chosen = QFileDialog.getExistingDirectory(self, "选择目录", entry.text())
            if chosen:
                entry.setText(chosen)

        browse_btn.clicked.connect(_browse)
        h.addWidget(browse_btn)
        form.addRow(label, row)
        return row

    # ── 通用段 ──

    def _build_seg_general(self) -> QWidget:
        widget = QWidget()
        scroll_layout = QVBoxLayout(widget)
        scroll_layout.setContentsMargins(4, 8, 4, 4)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(8)

        self._section_header(scroll_layout, "基础")
        self._add_combo_field(form, "LLM 后端:", "llm_backend", ["ollama", "openai", "vllm"])
        self._add_combo_field(form, "日志级别:", "log_level", ["DEBUG", "INFO", "WARNING", "ERROR"])

        scroll_layout.addLayout(form)
        scroll_layout.addSpacing(8)

        form2 = QFormLayout()
        form2.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form2.setSpacing(8)
        self._section_header(scroll_layout, "目录")
        self._add_dir_field(form2, "监控目录:", "monitor.watch_dir")
        self._add_dir_field(form2, "输出目录:", "rename.output_base_dir")
        scroll_layout.addLayout(form2)
        scroll_layout.addSpacing(8)

        form3 = QFormLayout()
        form3.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form3.setSpacing(8)
        self._section_header(scroll_layout, "监控")
        cb = QCheckBox("递归监控子目录")
        self._fields["monitor.recursive"] = cb
        form3.addRow("", cb)
        self._add_field(form3, "防抖间隔 (秒):", "monitor.debounce_seconds")
        scroll_layout.addLayout(form3)
        scroll_layout.addSpacing(8)

        form4 = QFormLayout()
        form4.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form4.setSpacing(8)
        self._section_header(scroll_layout, "重命名")
        self._add_field(form4, "文件名模板:", "rename.template")
        self._add_combo_field(form4, "冲突策略:", "rename.conflict_strategy", ["append_number", "skip"])
        scroll_layout.addLayout(form4)
        scroll_layout.addSpacing(8)

        form5 = QFormLayout()
        form5.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form5.setSpacing(8)
        self._section_header(scroll_layout, "分类")
        self._tag_list = TagListWidget()
        scroll_layout.addWidget(self._tag_list)
        scroll_layout.addStretch()

        return widget

    # ── LLM 段 ──

    def _build_seg_llm(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 8, 4, 4)

        self._llm_seg = SegmentedGroup(["Ollama", "OpenAI", "vLLM"])
        self._llm_seg.on_change(self._on_llm_sub_change)
        layout.addWidget(self._llm_seg)
        layout.addSpacing(6)

        self._llm_stack = QStackedWidget()
        self._llm_stack.addWidget(self._build_llm_ollama())   # 0
        self._llm_stack.addWidget(self._build_llm_openai())   # 1
        self._llm_stack.addWidget(self._build_llm_vllm())     # 2
        layout.addWidget(self._llm_stack, 1)

        self._llm_seg.set_current(0)
        return widget

    def _on_llm_sub_change(self, idx: int) -> None:
        self._llm_stack.setCurrentIndex(idx)

    def _build_llm_ollama(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 8, 4, 4)
        self._section_header(layout, "Ollama 配置")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(8)
        self._add_field(form, "模型名称:", "ollama.model")
        self._add_field(form, "API 地址:", "ollama.base_url")
        self._add_field(form, "Temperature:", "ollama.temperature")
        self._add_field(form, "超时 (秒):", "ollama.timeout")
        layout.addLayout(form)
        layout.addStretch()
        return widget

    def _build_llm_openai(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 8, 4, 4)
        self._section_header(layout, "OpenAI 兼容 API 配置")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(8)
        api_key_edit = QLineEdit()
        api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._add_field(form, "API Key:", "openai.api_key", api_key_edit)
        self._add_field(form, "API 地址:", "openai.base_url")
        self._add_field(form, "模型名称:", "openai.model")
        self._add_field(form, "Temperature:", "openai.temperature")
        self._add_field(form, "Max Tokens:", "openai.max_tokens")
        layout.addLayout(form)
        layout.addStretch()
        return widget

    def _build_llm_vllm(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 8, 4, 4)
        self._section_header(layout, "vLLM 配置")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(8)
        api_key_edit = QLineEdit()
        api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._add_field(form, "API Key:", "vllm.api_key", api_key_edit)
        self._add_field(form, "API 地址:", "vllm.base_url")
        self._add_field(form, "模型名称:", "vllm.model")
        self._add_field(form, "Temperature:", "vllm.temperature")
        self._add_field(form, "超时 (秒):", "vllm.timeout")
        layout.addLayout(form)
        layout.addStretch()
        return widget

    # ── 配置读写 ──

    def _init_all_fields(self) -> None:
        config = self._config_loader.config
        mapping = {
            "llm_backend": config.llm_backend,
            "log_level": config.log_level,
            "monitor.watch_dir": config.monitor.watch_dir,
            "monitor.debounce_seconds": str(config.monitor.debounce_seconds),
            "ollama.model": config.ollama.model,
            "ollama.base_url": config.ollama.base_url,
            "ollama.temperature": str(config.ollama.temperature),
            "ollama.timeout": str(config.ollama.timeout),
            "openai.api_key": config.openai.api_key,
            "openai.base_url": config.openai.base_url,
            "openai.model": config.openai.model,
            "openai.temperature": str(config.openai.temperature),
            "openai.max_tokens": str(config.openai.max_tokens),
            "vllm.base_url": config.vllm.base_url,
            "vllm.model": config.vllm.model,
            "vllm.api_key": config.vllm.api_key,
            "vllm.temperature": str(config.vllm.temperature),
            "vllm.timeout": str(config.vllm.timeout),
            "rename.template": config.rename.template,
            "rename.output_base_dir": config.rename.output_base_dir,
            "rename.conflict_strategy": config.rename.conflict_strategy,
        }
        for key, val in mapping.items():
            w = self._fields.get(key)
            if w is None:
                continue
            if isinstance(w, QComboBox):
                w.setCurrentText(val)
            elif isinstance(w, QLineEdit):
                w.setText(val)
        cb = self._fields.get("monitor.recursive")
        if isinstance(cb, QCheckBox):
            cb.setChecked(config.monitor.recursive)
        if hasattr(self, "_tag_list"):
            self._tag_list.set_labels(config.classification.labels)

    def _get_field(self, key: str) -> str:
        w = self._fields.get(key)
        if isinstance(w, QComboBox):
            return w.currentText().strip()
        if isinstance(w, QLineEdit):
            return w.text().strip()
        return ""

    def _collect_config(self) -> AppConfig:
        labels = self._tag_list.labels() if hasattr(self, "_tag_list") else []

        cb = self._fields.get("monitor.recursive")
        recursive = cb.isChecked() if isinstance(cb, QCheckBox) else False

        return AppConfig(
            monitor={
                "watch_dir": self._get_field("monitor.watch_dir"),
                "recursive": recursive,
                "debounce_seconds": float(self._get_field("monitor.debounce_seconds")),
            },
            llm_backend=self._get_field("llm_backend"),
            ollama={
                "model": self._get_field("ollama.model"),
                "base_url": self._get_field("ollama.base_url"),
                "temperature": float(self._get_field("ollama.temperature")),
                "timeout": float(self._get_field("ollama.timeout")),
            },
            openai={
                "api_key": self._get_field("openai.api_key"),
                "base_url": self._get_field("openai.base_url"),
                "model": self._get_field("openai.model"),
                "temperature": float(self._get_field("openai.temperature")),
                "max_tokens": int(self._get_field("openai.max_tokens")),
            },
            vllm={
                "base_url": self._get_field("vllm.base_url"),
                "model": self._get_field("vllm.model"),
                "api_key": self._get_field("vllm.api_key"),
                "temperature": float(self._get_field("vllm.temperature")),
                "timeout": float(self._get_field("vllm.timeout")),
            },
            rename={
                "template": self._get_field("rename.template"),
                "output_base_dir": self._get_field("rename.output_base_dir"),
                "conflict_strategy": self._get_field("rename.conflict_strategy"),
            },
            classification={"labels": labels},
            database={"path": self._config_loader.config.database.path},
            log_level=self._get_field("log_level"),
        )

    def _save_config(self) -> None:
        try:
            new_config = self._collect_config()
        except (ValueError, KeyError) as e:
            QMessageBox.critical(self, "配置校验失败", str(e))
            return
        try:
            self._config_loader.save(new_config)
        except OSError as e:
            QMessageBox.critical(self, "保存失败", f"无法写入配置文件:\n{e}")
            return
        self._config_status.setText("✓ 配置已保存")
        self._config_status.setStyleSheet(f"color: {SUCCESS_FG};")
        self._on_config_saved(new_config)
        logger.info("GUI 配置已保存并应用")

    def _reset_config(self) -> None:
        self._init_all_fields()
        self._config_status.setText("已重置")
        self._config_status.setStyleSheet(f"color: {MUTED_FG};")

    # ── 操作日志页 ──

    def _build_operations_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 12, 16, 12)

        title = QLabel("操作日志")
        title.setFont(QFont(FONT_FAMILY, 14, QFont.Weight.Bold))
        layout.addWidget(title)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        refresh_btn = QPushButton("刷新")
        refresh_btn.setStyleSheet(f"background: {ACCENT}; color: white; border-radius: 4px; padding: 5px 16px;")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self._refresh_operations)
        toolbar.addWidget(refresh_btn)

        rollback_btn = QPushButton("回滚选中")
        rollback_btn.setStyleSheet("border: 1px solid palette(mid); border-radius: 4px; padding: 5px 16px;")
        rollback_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        rollback_btn.clicked.connect(self._rollback_selected)
        toolbar.addWidget(rollback_btn)

        delete_btn = QPushButton("删除选中")
        delete_btn.setStyleSheet(f"border: 1px solid palette(mid); border-radius: 4px; padding: 5px 16px; color: {ERROR_FG};")
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.clicked.connect(self._delete_selected)
        toolbar.addWidget(delete_btn)

        clear_btn = QPushButton("清空全部")
        clear_btn.setStyleSheet(f"border: 1px solid palette(mid); border-radius: 4px; padding: 5px 16px; color: {ERROR_FG};")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.clicked.connect(self._delete_all)
        toolbar.addWidget(clear_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 表格
        cols = ["原始文件", "新文件名", "分类", "标题", "状态", "时间"]
        self._table = QTableWidget(0, len(cols))
        self._table.setHorizontalHeaderLabels(cols)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)

        widths = [160, 160, 80, 140, 60, 120]
        for i, w in enumerate(widths):
            self._table.setColumnWidth(i, w)

        layout.addWidget(self._table, 1)

        # 初始加载
        QTimer.singleShot(100, self._refresh_operations)

        return page

    def _refresh_operations(self) -> None:
        self._table.setRowCount(0)
        try:
            operations = self._on_refresh()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"刷新失败: {e}")
            return
        for op in operations:
            row = self._table.rowCount()
            self._table.insertRow(row)
            values = [
                op.get("original_name", ""),
                op.get("new_name", ""),
                op.get("category", ""),
                (op.get("title", "") or "")[:30],
                op.get("status", ""),
                op.get("created_at", ""),
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(val)
                item.setData(Qt.ItemDataRole.UserRole, op["id"])
                self._table.setItem(row, col, item)

    def _get_selected_ids(self) -> list[int]:
        ids = set()
        for item in self._table.selectedItems():
            row_id = item.data(Qt.ItemDataRole.UserRole)
            if row_id is not None:
                ids.add(row_id)
        return list(ids)

    def _rollback_selected(self) -> None:
        ids = self._get_selected_ids()
        if not ids:
            QMessageBox.information(self, "提示", "请先选择要回滚的操作")
            return
        op_id = ids[0]
        if QMessageBox.question(self, "确认", f"确定要回滚操作 #{op_id} 吗？") == QMessageBox.StandardButton.Yes:
            if self._on_rollback(op_id):
                QMessageBox.information(self, "成功", "回滚成功")
                self._refresh_operations()
            else:
                QMessageBox.critical(self, "失败", "回滚失败，请查看日志")

    def _delete_selected(self) -> None:
        if self._on_delete is None:
            QMessageBox.warning(self, "提示", "删除功能未配置")
            return
        ids = self._get_selected_ids()
        if not ids:
            QMessageBox.information(self, "提示", "请先选择要删除的记录")
            return
        if QMessageBox.question(self, "确认", f"确定要删除选中的 {len(ids)} 条记录吗？") == QMessageBox.StandardButton.Yes:
            deleted = self._on_delete(ids)
            QMessageBox.information(self, "完成", f"已删除 {deleted} 条记录")
            self._refresh_operations()

    def _delete_all(self) -> None:
        if self._on_delete is None:
            QMessageBox.warning(self, "提示", "删除功能未配置")
            return
        if QMessageBox.question(self, "确认", "确定要清空所有操作记录吗？此操作不可撤销！") == QMessageBox.StandardButton.Yes:
            deleted = self._on_delete([])
            QMessageBox.information(self, "完成", f"已清空 {deleted} 条记录")
            self._refresh_operations()

    # ── 运行日志页 ──

    def _build_logs_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 12, 16, 12)

        title = QLabel("运行日志")
        title.setFont(QFont(FONT_FAMILY, 14, QFont.Weight.Bold))
        layout.addWidget(title)

        toolbar = QHBoxLayout()
        clear_btn = QPushButton("清空")
        clear_btn.setStyleSheet("border: 1px solid palette(mid); border-radius: 4px; padding: 4px 16px;")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.clicked.connect(self._clear_logs)
        toolbar.addWidget(clear_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setFont(QFont("Consolas", 10))
        layout.addWidget(self._log_text, 1)

        # 设置持久化 handler 的 widget（只设一次，不随导航销毁）
        self._text_handler.set_widget(self._log_text)

        return page

    def _clear_logs(self) -> None:
        self._text_handler.clear_buffer()
        if self._log_text:
            self._log_text.clear()

    # ── 关闭行为 ──

    def closeEvent(self, event) -> None:
        event.ignore()
        self.hide()


# ── QtTextHandler ──

class QtTextHandler(logging.Handler):
    """将日志输出到 QTextEdit，带缓冲区，线程安全"""

    MAX_BUFFER = 500

    def __init__(self):
        super().__init__()
        self._widget: QTextEdit | None = None
        self._buffer: list[str] = []

    def set_widget(self, widget: QTextEdit) -> None:
        self._widget = widget
        for msg in self._buffer:
            self._do_append(msg)

    def clear_widget(self) -> None:
        self._widget = None

    def clear_buffer(self) -> None:
        self._buffer.clear()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record) + "\n"
            self._buffer.append(msg)
            if len(self._buffer) > self.MAX_BUFFER:
                self._buffer = self._buffer[-self.MAX_BUFFER:]
            if self._widget is not None:
                QTimer.singleShot(0, lambda m=msg: self._do_append(m))
        except Exception:
            pass

    def _do_append(self, msg: str) -> None:
        if self._widget is None:
            return
        try:
            cursor = self._widget.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText(msg)
            self._widget.setTextCursor(cursor)
            self._widget.ensureCursorVisible()
        except Exception:
            pass
