"""tkinter 配置/日志/回滚窗口"""

import logging
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from typing import Callable

from ..config.loader import ConfigLoader
from ..config.schema import AppConfig

logger = logging.getLogger(__name__)


class GUIApp:
    """tkinter GUI 应用"""

    def __init__(
        self,
        config_loader: ConfigLoader,
        on_config_saved: Callable[[AppConfig], None],
        on_rollback: Callable[[int], bool],
        on_refresh: Callable[[], list[dict]],
    ):
        self._config_loader = config_loader
        self._on_config_saved = on_config_saved
        self._on_rollback = on_rollback
        self._on_refresh = on_refresh
        self._root: tk.Tk | None = None
        self._thread: threading.Thread | None = None
        self._log_text: scrolledtext.ScrolledText | None = None
        # 配置表单变量
        self._vars: dict[str, tk.Variable] = {}

    def start(self) -> None:
        """在独立线程中启动 GUI"""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """关闭 GUI"""
        if self._root is not None:
            try:
                self._root.quit()
                self._root.destroy()
            except tk.TclError:
                pass

    def _run(self) -> None:
        """GUI 主循环"""
        self._root = tk.Tk()
        self._root.title("Paper Tool - 文献管理工具")
        self._root.geometry("860x680")
        self._root.minsize(700, 500)
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        notebook = ttk.Notebook(self._root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self._create_config_tab(notebook)
        self._create_operations_tab(notebook)
        self._create_log_tab(notebook)

        self._root.mainloop()

    # ────────────────────────────────────────────
    # 配置编辑标签页
    # ────────────────────────────────────────────

    def _create_config_tab(self, notebook: ttk.Notebook) -> None:
        """创建可视化配置编辑标签页"""
        outer = ttk.Frame(notebook)
        notebook.add(outer, text="配置")

        canvas = tk.Canvas(outer, highlightthickness=0)
        v_scroll = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview)
        self._config_frame = ttk.Frame(canvas)

        self._config_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self._config_frame, anchor="nw")
        canvas.configure(yscrollcommand=v_scroll.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 绑定鼠标滚轮
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self._build_config_form()

    def _build_config_form(self) -> None:
        """构建配置表单所有字段"""
        config = self._config_loader.config

        # ── 通用设置 ──
        self._section("通用设置")
        self._combo("llm_backend", "LLM 后端", ["ollama", "openai", "vllm"], config.llm_backend)
        self._combo("log_level", "日志级别", ["DEBUG", "INFO", "WARNING", "ERROR"], config.log_level)

        # ── 监控设置 ──
        self._section("文件监控")
        self._dir_entry("monitor.watch_dir", "监控目录", config.monitor.watch_dir)
        self._check("monitor.recursive", "递归监控子目录", config.monitor.recursive)
        self._entry("monitor.debounce_seconds", "防抖间隔 (秒)", str(config.monitor.debounce_seconds))

        # ── Ollama 配置 ──
        self._section("Ollama 配置")
        self._entry("ollama.model", "模型名称", config.ollama.model)
        self._entry("ollama.base_url", "API 地址", config.ollama.base_url)
        self._entry("ollama.temperature", "Temperature", str(config.ollama.temperature))
        self._entry("ollama.timeout", "超时 (秒)", str(config.ollama.timeout))

        # ── OpenAI 兼容 API 配置 ──
        self._section("OpenAI 兼容 API 配置")
        self._entry("openai.api_key", "API Key", config.openai.api_key, show="*")
        self._entry("openai.base_url", "API 地址", config.openai.base_url)
        self._entry("openai.model", "模型名称", config.openai.model)
        self._entry("openai.temperature", "Temperature", str(config.openai.temperature))
        self._entry("openai.max_tokens", "Max Tokens", str(config.openai.max_tokens))

        # ── vLLM 配置 ──
        self._section("vLLM 配置")
        self._entry("vllm.base_url", "API 地址", config.vllm.base_url)
        self._entry("vllm.model", "模型名称", config.vllm.model)
        self._entry("vllm.api_key", "API Key", config.vllm.api_key, show="*")
        self._entry("vllm.temperature", "Temperature", str(config.vllm.temperature))
        self._entry("vllm.timeout", "超时 (秒)", str(config.vllm.timeout))

        # ── 重命名配置 ──
        self._section("重命名规则")
        self._entry("rename.template", "文件名模板", config.rename.template)
        self._dir_entry("rename.output_base_dir", "输出目录", config.rename.output_base_dir)
        self._combo(
            "rename.conflict_strategy",
            "冲突策略",
            ["append_number", "skip"],
            config.rename.conflict_strategy,
        )

        # ── 分类配置 ──
        self._section("分类标签")
        self._entry(
            "classification.labels",
            "标签 (逗号分隔)",
            ", ".join(config.classification.labels),
        )

        # ── 底部按钮 ──
        btn_frame = ttk.Frame(self._config_frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=15)

        ttk.Button(btn_frame, text="保存配置", command=self._save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="重置为当前值", command=self._reset_config).pack(side=tk.LEFT, padx=5)

        # 状态标签
        self._config_status = ttk.Label(btn_frame, text="", foreground="gray")
        self._config_status.pack(side=tk.LEFT, padx=15)

    def _section(self, title: str) -> None:
        """创建分组标题"""
        frame = ttk.LabelFrame(self._config_frame, text=title)
        frame.pack(fill=tk.X, padx=10, pady=(10, 0))
        # 将后续字段放入此 frame，直到下一个 section
        self._current_section = frame

    def _entry(self, key: str, label: str, default: str, show: str | None = None) -> None:
        """创建带标签的输入框"""
        row = ttk.Frame(self._current_section)
        row.pack(fill=tk.X, padx=8, pady=3)

        ttk.Label(row, text=label, width=18, anchor="w").pack(side=tk.LEFT)
        var = tk.StringVar(value=default)
        entry = ttk.Entry(row, textvariable=var, show=show or "")
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        self._vars[key] = var

    def _dir_entry(self, key: str, label: str, default: str) -> None:
        """创建带"浏览"按钮的目录选择输入框"""
        row = ttk.Frame(self._current_section)
        row.pack(fill=tk.X, padx=8, pady=3)

        ttk.Label(row, text=label, width=18, anchor="w").pack(side=tk.LEFT)
        var = tk.StringVar(value=default)
        entry = ttk.Entry(row, textvariable=var)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        def _browse():
            chosen = filedialog.askdirectory(initialdir=var.get() or None)
            if chosen:
                var.set(chosen)

        ttk.Button(row, text="浏览...", command=_browse, width=6).pack(side=tk.LEFT, padx=(4, 0))
        self._vars[key] = var

    def _combo(self, key: str, label: str, values: list[str], default: str) -> None:
        """创建带标签的下拉框"""
        row = ttk.Frame(self._current_section)
        row.pack(fill=tk.X, padx=8, pady=3)

        ttk.Label(row, text=label, width=18, anchor="w").pack(side=tk.LEFT)
        var = tk.StringVar(value=default)
        combo = ttk.Combobox(row, textvariable=var, values=values, state="readonly", width=30)
        combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        self._vars[key] = var

    def _check(self, key: str, label: str, default: bool) -> None:
        """创建勾选框"""
        var = tk.BooleanVar(value=default)
        cb = ttk.Checkbutton(self._current_section, text=label, variable=var)
        cb.pack(fill=tk.X, padx=8, pady=3)
        self._vars[key] = var

    def _get_var(self, key: str) -> str:
        """获取变量值（字符串）"""
        val = self._vars[key].get()
        return val.strip()

    def _collect_config(self) -> AppConfig:
        """从表单收集所有字段，构建 AppConfig"""
        labels_raw = self._get_var("classification.labels")
        labels = [l.strip() for l in labels_raw.split(",") if l.strip()]

        return AppConfig(
            monitor={
                "watch_dir": self._get_var("monitor.watch_dir"),
                "recursive": self._vars["monitor.recursive"].get(),
                "debounce_seconds": float(self._get_var("monitor.debounce_seconds")),
            },
            llm_backend=self._get_var("llm_backend"),
            ollama={
                "model": self._get_var("ollama.model"),
                "base_url": self._get_var("ollama.base_url"),
                "temperature": float(self._get_var("ollama.temperature")),
                "timeout": float(self._get_var("ollama.timeout")),
            },
            openai={
                "api_key": self._get_var("openai.api_key"),
                "base_url": self._get_var("openai.base_url"),
                "model": self._get_var("openai.model"),
                "temperature": float(self._get_var("openai.temperature")),
                "max_tokens": int(self._get_var("openai.max_tokens")),
            },
            vllm={
                "base_url": self._get_var("vllm.base_url"),
                "model": self._get_var("vllm.model"),
                "api_key": self._get_var("vllm.api_key"),
                "temperature": float(self._get_var("vllm.temperature")),
                "timeout": float(self._get_var("vllm.timeout")),
            },
            rename={
                "template": self._get_var("rename.template"),
                "output_base_dir": self._get_var("rename.output_base_dir"),
                "conflict_strategy": self._get_var("rename.conflict_strategy"),
            },
            classification={
                "labels": labels,
            },
            database={
                "path": self._config_loader.config.database.path,
            },
            log_level=self._get_var("log_level"),
        )

    def _save_config(self) -> None:
        """保存配置到 YAML 并通知主应用"""
        try:
            new_config = self._collect_config()
        except (ValueError, KeyError, tk.TclError) as e:
            messagebox.showerror("配置校验失败", str(e))
            return

        try:
            self._config_loader.save(new_config)
        except OSError as e:
            messagebox.showerror("保存失败", f"无法写入配置文件:\n{e}")
            return

        self._config_status.configure(text="配置已保存", foreground="green")
        self._on_config_saved(new_config)
        logger.info("GUI 配置已保存并应用")

    def _reset_config(self) -> None:
        """将表单重置为当前配置文件的值"""
        config = self._config_loader.config

        self._vars["llm_backend"].set(config.llm_backend)
        self._vars["log_level"].set(config.log_level)
        self._vars["monitor.watch_dir"].set(config.monitor.watch_dir)
        self._vars["monitor.recursive"].set(config.monitor.recursive)
        self._vars["monitor.debounce_seconds"].set(str(config.monitor.debounce_seconds))
        self._vars["ollama.model"].set(config.ollama.model)
        self._vars["ollama.base_url"].set(config.ollama.base_url)
        self._vars["ollama.temperature"].set(str(config.ollama.temperature))
        self._vars["ollama.timeout"].set(str(config.ollama.timeout))
        self._vars["openai.api_key"].set(config.openai.api_key)
        self._vars["openai.base_url"].set(config.openai.base_url)
        self._vars["openai.model"].set(config.openai.model)
        self._vars["openai.temperature"].set(str(config.openai.temperature))
        self._vars["openai.max_tokens"].set(str(config.openai.max_tokens))
        self._vars["vllm.base_url"].set(config.vllm.base_url)
        self._vars["vllm.model"].set(config.vllm.model)
        self._vars["vllm.api_key"].set(config.vllm.api_key)
        self._vars["vllm.temperature"].set(str(config.vllm.temperature))
        self._vars["vllm.timeout"].set(str(config.vllm.timeout))
        self._vars["rename.template"].set(config.rename.template)
        self._vars["rename.output_base_dir"].set(config.rename.output_base_dir)
        self._vars["rename.conflict_strategy"].set(config.rename.conflict_strategy)
        self._vars["classification.labels"].set(", ".join(config.classification.labels))

        self._config_status.configure(text="已重置", foreground="gray")

    # ────────────────────────────────────────────
    # 操作日志标签页
    # ────────────────────────────────────────────

    def _create_operations_tab(self, notebook: ttk.Notebook) -> None:
        """创建操作日志标签页"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="操作日志")

        # 工具栏
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(toolbar, text="刷新", command=self._refresh_operations).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="回滚选中", command=self._rollback_selected).pack(side=tk.LEFT, padx=5)

        # 操作表格
        columns = ("ID", "原始文件", "新文件名", "分类", "标题", "状态", "时间")
        self._tree = ttk.Treeview(frame, columns=columns, show="headings", height=20)
        for col in columns:
            self._tree.heading(col, text=col)
            self._tree.column(col, width=100)

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)

        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _refresh_operations(self) -> None:
        """刷新操作列表"""
        for item in self._tree.get_children():
            self._tree.delete(item)

        try:
            operations = self._on_refresh()
        except Exception as e:
            messagebox.showerror("错误", f"刷新失败: {e}")
            return

        for op in operations:
            self._tree.insert("", tk.END, iid=str(op["id"]), values=(
                op["id"],
                op["original_name"],
                op["new_name"],
                op["category"],
                op["title"][:30],
                op["status"],
                op["created_at"],
            ))

    def _rollback_selected(self) -> None:
        """回滚选中操作"""
        selected = self._tree.selection()
        if not selected:
            messagebox.showinfo("提示", "请先选择要回滚的操作")
            return

        op_id = int(selected[0])
        if messagebox.askyesno("确认", f"确定要回滚操作 #{op_id} 吗？"):
            if self._on_rollback(op_id):
                messagebox.showinfo("成功", "回滚成功")
                self._refresh_operations()
            else:
                messagebox.showerror("失败", "回滚失败，请查看日志")

    # ────────────────────────────────────────────
    # 运行日志标签页
    # ────────────────────────────────────────────

    def _create_log_tab(self, notebook: ttk.Notebook) -> None:
        """创建日志标签页"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="运行日志")

        self._log_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD)
        self._log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 设置日志 handler
        text_handler = TextHandler(self._log_text)
        text_handler.setFormatter(
            logging.Formatter("[%(asctime)s] %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
        )
        logging.getLogger("paper_tool").addHandler(text_handler)

    # ────────────────────────────────────────────

    def _on_close(self) -> None:
        """窗口关闭事件"""
        self._root.withdraw()


class TextHandler(logging.Handler):
    """将日志输出到 tkinter Text 控件"""

    def __init__(self, text_widget: scrolledtext.ScrolledText):
        super().__init__()
        self._widget = text_widget

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self._widget.after(0, self._append, msg + "\n")
        except Exception:
            pass

    def _append(self, msg: str) -> None:
        try:
            self._widget.configure(state=tk.NORMAL)
            self._widget.insert(tk.END, msg)
            self._widget.configure(state=tk.DISABLED)
            self._widget.see(tk.END)
        except tk.TclError:
            pass
