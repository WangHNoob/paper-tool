"""tkinter 配置/日志/回滚窗口"""

import logging
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from typing import Callable

logger = logging.getLogger(__name__)


class GUIApp:
    """tkinter GUI 应用"""

    def __init__(
        self,
        on_rollback: Callable[[int], bool],
        on_refresh: Callable[[], list[dict]],
    ):
        self._on_rollback = on_rollback
        self._on_refresh = on_refresh
        self._root: tk.Tk | None = None
        self._thread: threading.Thread | None = None
        self._log_text: scrolledtext.ScrolledText | None = None

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
        self._root.geometry("800x600")
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        notebook = ttk.Notebook(self._root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 操作日志 Tab
        self._create_operations_tab(notebook)

        # 日志 Tab
        self._create_log_tab(notebook)

        self._root.mainloop()

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
