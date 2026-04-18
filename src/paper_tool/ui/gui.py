"""CustomTkinter GUI - 侧边栏导航 + 分段配置页"""

import logging
import threading
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
from typing import Callable

import customtkinter as ctk

from ..config.loader import ConfigLoader
from ..utils.logging import _CSTFormatter
from ..config.schema import AppConfig

logger = logging.getLogger(__name__)

# ── 字体 & 样式常量 ──
FONT_FAMILY = "Segoe UI"
FONT_TITLE = (FONT_FAMILY, 15, "bold")
FONT_SECTION = (FONT_FAMILY, 13, "bold")
FONT_BODY = (FONT_FAMILY, 12)
FONT_SMALL = (FONT_FAMILY, 11)
FONT_MONO = ("Consolas", 11)

ACCENT = ("#3B82F6", "#2563EB")
ACCENT_HOVER = ("#2563EB", "#1D4ED8")
SUCCESS_FG = ("#16A34A", "#22C55E")
ERROR_FG = ("#DC2626", "#EF4444")
WARN_FG = ("#D97706", "#F59E0B")
MUTED_FG = ("#6B7280", "#9CA3AF")

SIDEBAR_W = 62
SECTION_NAMES = ["通用", "LLM"]


class GUIApp:
    """CustomTkinter GUI 应用"""

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
        self._root: ctk.CTk | None = None
        self._thread: threading.Thread | None = None
        self._vars: dict[str, tk.Variable] = {}
        self._current_page: str = ""
        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        self._main_area: ctk.CTkFrame | None = None
        self._log_text: ctk.CTkTextbox | None = None
        self._config_status: ctk.CTkLabel | None = None
        self._seg_frames: dict[str, ctk.CTkFrame] = {}
        self._active_seg: str = ""
        # LLM 子段
        self._llm_sub_frames: dict[str, ctk.CTkFrame] = {}
        self._active_llm_sub: str = ""

    # ── 生命周期 ──

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._root is not None:
            try:
                self._root.quit()
                self._root.destroy()
            except Exception:
                pass

    def _run(self) -> None:
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self._root = ctk.CTk()
        self._root.title("Paper Tool")
        self._root.geometry("960x720")
        self._root.minsize(780, 540)
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_layout()
        self._navigate("config")
        self._root.mainloop()

    # ── 主布局 ──

    def _build_layout(self) -> None:
        self._root.grid_rowconfigure(0, weight=1)
        self._root.grid_columnconfigure(1, weight=1)

        sidebar = ctk.CTkFrame(self._root, width=SIDEBAR_W, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)

        ctk.CTkLabel(
            sidebar, text="PT", font=(FONT_FAMILY, 16, "bold"), text_color=ACCENT,
        ).pack(pady=(18, 20))

        for symbol, page in [("\u2699", "config"), ("\u2630", "operations"), ("\u2261", "logs")]:
            btn = ctk.CTkButton(
                sidebar, text=symbol, width=40, height=40,
                font=(FONT_FAMILY, 18),
                fg_color="transparent",
                text_color=("gray30", "gray70"),
                hover_color=("gray80", "gray35"),
                corner_radius=8,
                command=lambda p=page: self._navigate(p),
            )
            btn.pack(pady=(5, 5), padx=10)
            self._nav_buttons[page] = btn

        ctk.CTkButton(
            sidebar, text="\u25D0", width=40, height=40,
            font=(FONT_FAMILY, 16),
            fg_color="transparent",
            text_color=("gray30", "gray70"),
            hover_color=("gray80", "gray35"),
            corner_radius=8,
            command=self._toggle_theme,
        ).pack(side="bottom", pady=(0, 15), padx=10)

        self._main_area = ctk.CTkFrame(self._root, fg_color="transparent")
        self._main_area.grid(row=0, column=1, sticky="nsew", padx=(0, 8), pady=8)

        status_bar = ctk.CTkFrame(self._root, height=30, corner_radius=0)
        status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        status_bar.grid_propagate(False)

        config = self._config_loader.config
        ctk.CTkLabel(
            status_bar,
            text=f"  \u25CF 监控中  |  后端: {config.llm_backend}",
            font=FONT_SMALL, anchor="w",
        ).pack(side="left", padx=10, pady=4)

    def _navigate(self, page: str) -> None:
        for w in self._main_area.winfo_children():
            w.destroy()

        for name, btn in self._nav_buttons.items():
            btn.configure(
                fg_color=("gray75", "gray30") if name == page else "transparent"
            )

        if page == "config":
            self._build_config_page()
        elif page == "operations":
            self._build_operations_page()
        elif page == "logs":
            self._build_logs_page()
        self._current_page = page

    def _toggle_theme(self) -> None:
        mode = ctk.get_appearance_mode()
        ctk.set_appearance_mode("Dark" if mode == "Light" else "Light")

    # ── 配置页 ──

    def _build_config_page(self) -> None:
        ctk.CTkLabel(
            self._main_area, text="配置", font=FONT_TITLE, anchor="w",
        ).pack(fill="x", padx=16, pady=(12, 2))
        ctk.CTkLabel(
            self._main_area, text="修改后点击「保存配置」生效",
            font=FONT_SMALL, text_color=MUTED_FG, anchor="w",
        ).pack(fill="x", padx=16, pady=(0, 8))

        seg_var = tk.StringVar(value="通用")
        seg = ctk.CTkSegmentedButton(
            self._main_area, values=SECTION_NAMES,
            variable=seg_var, command=self._on_seg_change,
            font=FONT_SMALL,
        )
        seg.pack(fill="x", padx=16, pady=(0, 10))
        self._seg_var_ref = seg_var

        self._config_card = ctk.CTkFrame(self._main_area, border_width=1, corner_radius=8)
        self._config_card.pack(fill="both", expand=True, padx=16)
        self._config_card.pack_propagate(False)

        self._init_all_vars()

        # 预创建两个主段
        self._seg_frames = {}
        self._build_seg_general()
        self._build_seg_llm()

        # 底部按钮
        btn_row = ctk.CTkFrame(self._main_area, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(8, 12))

        ctk.CTkButton(
            btn_row, text="保存配置", width=120,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            command=self._save_config,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            btn_row, text="重置为当前值", width=120,
            fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"),
            hover_color=("gray80", "gray35"),
            command=self._reset_config,
        ).pack(side="left", padx=(0, 12))
        self._config_status = ctk.CTkLabel(btn_row, text="", font=FONT_SMALL)
        self._config_status.pack(side="left")

        self._on_seg_change("通用")

    def _init_all_vars(self) -> None:
        config = self._config_loader.config
        defaults = {
            "llm_backend": config.llm_backend,
            "log_level": config.log_level,
            "monitor.watch_dir": config.monitor.watch_dir,
            "monitor.recursive": config.monitor.recursive,
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
            "classification.labels": ", ".join(config.classification.labels),
        }
        for key, val in defaults.items():
            if isinstance(val, bool):
                self._vars[key] = tk.BooleanVar(value=val)
            else:
                self._vars[key] = tk.StringVar(value=val)

    def _on_seg_change(self, name: str) -> None:
        if self._active_seg and self._active_seg in self._seg_frames:
            self._seg_frames[self._active_seg].pack_forget()
        if name in self._seg_frames:
            self._seg_frames[name].pack(fill="both", expand=True, padx=6, pady=6)
        self._active_seg = name

    # ── 段构建辅助 ──

    def _field_row(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=3)
        return row

    def _add_entry(self, parent, label, key, show=None):
        ctk.CTkLabel(parent, text=label, font=FONT_BODY, width=140, anchor="w").pack(side="left")
        ctk.CTkEntry(parent, textvariable=self._vars[key], show=show or "", height=32).pack(
            side="left", fill="x", expand=True, padx=(10, 0),
        )

    def _add_combo(self, parent, label, key, values):
        ctk.CTkLabel(parent, text=label, font=FONT_BODY, width=140, anchor="w").pack(side="left")
        ctk.CTkOptionMenu(
            parent, variable=self._vars[key], values=values, height=32, font=FONT_BODY,
        ).pack(side="left", fill="x", expand=True, padx=(10, 0))

    def _add_dir(self, parent, label, key):
        ctk.CTkLabel(parent, text=label, font=FONT_BODY, width=140, anchor="w").pack(side="left")
        ctk.CTkEntry(parent, textvariable=self._vars[key], height=32).pack(
            side="left", fill="x", expand=True, padx=(10, 0),
        )

        def _browse():
            chosen = filedialog.askdirectory(initialdir=self._vars[key].get() or None)
            if chosen:
                self._vars[key].set(chosen)

        ctk.CTkButton(
            parent, text="浏览", width=56, height=32,
            fg_color=("gray75", "gray30"), hover_color=("gray65", "gray40"),
            text_color=("gray10", "gray90"), font=FONT_SMALL, command=_browse,
        ).pack(side="left", padx=(6, 0))

    def _sub_header(self, parent: ctk.CTkFrame, title: str) -> None:
        ctk.CTkLabel(
            parent, text=title, font=FONT_SECTION, anchor="w", text_color=ACCENT,
        ).pack(fill="x", padx=14, pady=(14, 2))
        ctk.CTkFrame(parent, height=1, fg_color=("gray80", "gray30")).pack(
            fill="x", padx=14, pady=(0, 6),
        )

    # ── 通用段（基础 + 目录 + 监控 + 重命名 + 分类）──

    def _build_seg_general(self) -> None:
        frame = ctk.CTkFrame(self._config_card, fg_color="transparent")
        self._seg_frames["通用"] = frame

        # ── 基础 ──
        self._sub_header(frame, "基础")
        r = self._field_row(frame)
        self._add_combo(r, "LLM 后端", "llm_backend", ["ollama", "openai", "vllm"])
        r = self._field_row(frame)
        self._add_combo(r, "日志级别", "log_level", ["DEBUG", "INFO", "WARNING", "ERROR"])

        # ── 目录（监控 + 输出放一起）──
        self._sub_header(frame, "目录")
        r = self._field_row(frame)
        self._add_dir(r, "监控目录", "monitor.watch_dir")
        r = self._field_row(frame)
        self._add_dir(r, "输出目录", "rename.output_base_dir")

        # ── 监控选项 ──
        self._sub_header(frame, "监控")
        r = self._field_row(frame)
        ctk.CTkCheckBox(
            r, text="递归监控子目录", variable=self._vars["monitor.recursive"],
            font=FONT_BODY, checkbox_width=20, checkbox_height=20,
        ).pack(side="left")
        r = self._field_row(frame)
        self._add_entry(r, "防抖间隔 (秒)", "monitor.debounce_seconds")

        # ── 重命名 ──
        self._sub_header(frame, "重命名")
        r = self._field_row(frame)
        self._add_entry(r, "文件名模板", "rename.template")
        r = self._field_row(frame)
        self._add_combo(r, "冲突策略", "rename.conflict_strategy", ["append_number", "skip"])

        # ── 分类 ──
        self._sub_header(frame, "分类")
        r = self._field_row(frame)
        self._add_entry(r, "标签 (逗号分隔)", "classification.labels")

    # ── LLM 段（子切换 Ollama / OpenAI / vLLM）──

    def _build_seg_llm(self) -> None:
        frame = ctk.CTkFrame(self._config_card, fg_color="transparent")
        self._seg_frames["LLM"] = frame

        # 子切换栏
        self._llm_sub_var = tk.StringVar(value="Ollama")
        sub_seg = ctk.CTkSegmentedButton(
            frame, values=["Ollama", "OpenAI", "vLLM"],
            variable=self._llm_sub_var, command=self._on_llm_sub_change,
            font=FONT_SMALL,
        )
        sub_seg.pack(fill="x", padx=14, pady=(12, 6))

        # 子段容器
        self._llm_sub_container = ctk.CTkFrame(frame, fg_color="transparent")
        self._llm_sub_container.pack(fill="both", expand=True)

        # 预创建三个子段
        self._llm_sub_frames = {}
        self._build_llm_ollama()
        self._build_llm_openai()
        self._build_llm_vllm()

        self._on_llm_sub_change("Ollama")

    def _on_llm_sub_change(self, name: str) -> None:
        if self._active_llm_sub and self._active_llm_sub in self._llm_sub_frames:
            self._llm_sub_frames[self._active_llm_sub].pack_forget()
        if name in self._llm_sub_frames:
            self._llm_sub_frames[name].pack(fill="both", expand=True, padx=6, pady=6)
        self._active_llm_sub = name

    def _build_llm_ollama(self) -> None:
        f = ctk.CTkFrame(self._llm_sub_container, fg_color="transparent")
        self._llm_sub_frames["Ollama"] = f
        ctk.CTkLabel(f, text="Ollama 配置", font=FONT_SECTION, anchor="w").pack(
            fill="x", padx=14, pady=(10, 4),
        )
        ctk.CTkFrame(f, height=1, fg_color=("gray80", "gray30")).pack(
            fill="x", padx=14, pady=(0, 10),
        )
        for label, key in [("模型名称", "ollama.model"), ("API 地址", "ollama.base_url"),
                           ("Temperature", "ollama.temperature"), ("超时 (秒)", "ollama.timeout")]:
            r = self._field_row(f)
            self._add_entry(r, label, key)

    def _build_llm_openai(self) -> None:
        f = ctk.CTkFrame(self._llm_sub_container, fg_color="transparent")
        self._llm_sub_frames["OpenAI"] = f
        ctk.CTkLabel(f, text="OpenAI 兼容 API 配置", font=FONT_SECTION, anchor="w").pack(
            fill="x", padx=14, pady=(10, 4),
        )
        ctk.CTkFrame(f, height=1, fg_color=("gray80", "gray30")).pack(
            fill="x", padx=14, pady=(0, 10),
        )
        r = self._field_row(f)
        self._add_entry(r, "API Key", "openai.api_key", show="*")
        for label, key in [("API 地址", "openai.base_url"), ("模型名称", "openai.model"),
                           ("Temperature", "openai.temperature"), ("Max Tokens", "openai.max_tokens")]:
            r = self._field_row(f)
            self._add_entry(r, label, key)

    def _build_llm_vllm(self) -> None:
        f = ctk.CTkFrame(self._llm_sub_container, fg_color="transparent")
        self._llm_sub_frames["vLLM"] = f
        ctk.CTkLabel(f, text="vLLM 配置", font=FONT_SECTION, anchor="w").pack(
            fill="x", padx=14, pady=(10, 4),
        )
        ctk.CTkFrame(f, height=1, fg_color=("gray80", "gray30")).pack(
            fill="x", padx=14, pady=(0, 10),
        )
        r = self._field_row(f)
        self._add_entry(r, "API Key", "vllm.api_key", show="*")
        for label, key in [("API 地址", "vllm.base_url"), ("模型名称", "vllm.model"),
                           ("Temperature", "vllm.temperature"), ("超时 (秒)", "vllm.timeout")]:
            r = self._field_row(f)
            self._add_entry(r, label, key)

    # ── 配置读写 ──

    def _get_var(self, key: str) -> str:
        return self._vars[key].get().strip()

    def _collect_config(self) -> AppConfig:
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
            classification={"labels": labels},
            database={"path": self._config_loader.config.database.path},
            log_level=self._get_var("log_level"),
        )

    def _save_config(self) -> None:
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
        self._config_status.configure(text="\u2713 配置已保存", text_color=SUCCESS_FG)
        self._on_config_saved(new_config)
        logger.info("GUI 配置已保存并应用")

    def _reset_config(self) -> None:
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
            "classification.labels": ", ".join(config.classification.labels),
        }
        for key, val in mapping.items():
            self._vars[key].set(val)
        self._vars["monitor.recursive"].set(config.monitor.recursive)
        self._config_status.configure(text="已重置", text_color=MUTED_FG)

    # ── 操作日志页 ──

    def _build_operations_page(self) -> None:
        ctk.CTkLabel(
            self._main_area, text="操作日志", font=FONT_TITLE, anchor="w",
        ).pack(fill="x", padx=16, pady=(12, 4))

        toolbar = ctk.CTkFrame(self._main_area, fg_color="transparent")
        toolbar.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkButton(
            toolbar, text="刷新", width=80, height=32,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            command=self._refresh_operations,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            toolbar, text="回滚选中", width=100, height=32,
            fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"),
            hover_color=("gray80", "gray35"),
            command=self._rollback_selected,
        ).pack(side="left")

        tree_frame = ctk.CTkFrame(self._main_area, fg_color="transparent")
        tree_frame.pack(fill="both", expand=True, padx=12, pady=(2, 12))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Ops.Treeview", rowheight=30, font=FONT_SMALL)
        style.configure("Ops.Treeview.Heading", font=(FONT_FAMILY, 10, "bold"))

        cols = ("original", "new_name", "category", "title", "status", "time")
        self._tree = ttk.Treeview(
            tree_frame, columns=cols, show="headings",
            style="Ops.Treeview", height=18,
        )
        for col, (text, w) in [
            ("original", ("原始文件", 160)), ("new_name", ("新文件名", 160)),
            ("category", ("分类", 80)), ("title", ("标题", 140)),
            ("status", ("状态", 60)), ("time", ("时间", 120)),
        ]:
            self._tree.heading(col, text=text)
            self._tree.column(col, width=w, minwidth=40)

        v_scroll = ctk.CTkScrollbar(tree_frame, command=self._tree.yview)
        self._tree.configure(yscrollcommand=v_scroll.set)
        self._tree.pack(side="left", fill="both", expand=True)
        v_scroll.pack(side="right", fill="y")
        self._refresh_operations()

    def _refresh_operations(self) -> None:
        if not hasattr(self, "_tree"):
            return
        for item in self._tree.get_children():
            self._tree.delete(item)
        try:
            operations = self._on_refresh()
        except Exception as e:
            messagebox.showerror("错误", f"刷新失败: {e}")
            return
        for op in operations:
            self._tree.insert("", "end", iid=str(op["id"]), values=(
                op["original_name"], op["new_name"], op["category"],
                op["title"][:30], op.get("status", ""), op["created_at"],
            ))

    def _rollback_selected(self) -> None:
        if not hasattr(self, "_tree"):
            return
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

    # ── 运行日志页 ──

    def _build_logs_page(self) -> None:
        ctk.CTkLabel(
            self._main_area, text="运行日志", font=FONT_TITLE, anchor="w",
        ).pack(fill="x", padx=16, pady=(12, 4))

        toolbar = ctk.CTkFrame(self._main_area, fg_color="transparent")
        toolbar.pack(fill="x", padx=16, pady=(0, 6))

        ctk.CTkButton(
            toolbar, text="清空", width=70, height=30,
            fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"),
            hover_color=("gray80", "gray35"),
            font=FONT_SMALL, command=self._clear_logs,
        ).pack(side="left")

        self._log_text = ctk.CTkTextbox(self._main_area, font=FONT_MONO, wrap="word")
        self._log_text.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        text_handler = TextHandler(self._log_text)
        text_handler.setFormatter(
            _CSTFormatter("[%(asctime)s] %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
        )
        logging.getLogger("paper_tool").addHandler(text_handler)

    def _clear_logs(self) -> None:
        if self._log_text is not None:
            self._log_text.configure(state="normal")
            self._log_text.delete("1.0", "end")
            self._log_text.configure(state="disabled")

    def _on_close(self) -> None:
        self._root.withdraw()


class TextHandler(logging.Handler):
    """将日志输出到 CTkTextbox"""

    def __init__(self, text_widget: ctk.CTkTextbox):
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
            self._widget.configure(state="normal")
            self._widget.insert("end", msg)
            self._widget.configure(state="disabled")
            self._widget.see("end")
        except Exception:
            pass
