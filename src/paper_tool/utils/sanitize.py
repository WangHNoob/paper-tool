"""文件名清洗工具"""

import re

# Windows 文件名中不允许的字符
_UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
# 连续空格/点
_MULTI_SPACES = re.compile(r"\s+")
_MULTI_DOTS = re.compile(r"\.{2,}")
# 文件名保留字
_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

MAX_FILENAME_LENGTH = 200


def sanitize_filename(name: str) -> str:
    """清洗文件名，移除不安全字符并截断长度。

    Args:
        name: 原始文件名（不含路径）

    Returns:
        清洗后的安全文件名
    """
    # 替换不安全字符为下划线
    name = _UNSAFE_CHARS.sub("_", name)
    # 合并连续空格
    name = _MULTI_SPACES.sub(" ", name)
    # 合并连续点
    name = _MULTI_DOTS.sub(".", name)
    # 去除首尾空格和点
    name = name.strip(" .")
    # 检查保留名
    stem = name.rsplit(".", 1)[0] if "." in name else name
    if stem.upper() in _RESERVED_NAMES:
        name = f"_{name}"
    # 截断长度
    if len(name) > MAX_FILENAME_LENGTH:
        if "." in name:
            stem, ext = name.rsplit(".", 1)
            name = f"{stem[:MAX_FILENAME_LENGTH - len(ext) - 1]}.{ext}"
        else:
            name = name[:MAX_FILENAME_LENGTH]
    return name or "unnamed"
