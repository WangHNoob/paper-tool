"""模板解析与渲染引擎"""

import re
from pathlib import Path

from ..core.models import ClassifyResult, PaperInfo
from ..utils.sanitize import sanitize_filename

# 支持的模板变量
_TEMPLATE_VARS = {
    "{标题}": "title",
    "{作者}": "authors",
    "{年份}": "year",
    "{期刊}": "journal",
    "{关键词}": "keywords",
    "{分类}": "category",
}


def render_template(
    template: str,
    paper_info: PaperInfo,
    classify_result: ClassifyResult,
    output_base_dir: str,
) -> Path:
    """渲染文件名模板，生成目标路径。

    模板支持变量: {标题}, {作者}, {年份}, {期刊}, {关键词}, {分类}
    目录分隔符使用 /，会被转换为系统路径分隔符。

    Args:
        template: 文件名模板，如 "{分类}/{作者}_{年份}_{标题}.pdf"
        paper_info: 论文信息
        classify_result: 分类结果
        output_base_dir: 输出根目录

    Returns:
        完整的目标路径
    """
    # 构建变量值映射
    values = {
        "title": sanitize_filename(paper_info.title) if paper_info.title else "未知标题",
        "authors": sanitize_filename(", ".join(paper_info.authors[:3])) if paper_info.authors else "未知作者",
        "year": paper_info.year or "未知年份",
        "journal": sanitize_filename(paper_info.journal) if paper_info.journal else "未知期刊",
        "keywords": sanitize_filename(", ".join(paper_info.keywords[:5])) if paper_info.keywords else "",
        "category": sanitize_filename(classify_result.category) if classify_result.category else "未分类",
    }

    # 替换模板变量
    result = template
    for placeholder, key in _TEMPLATE_VARS.items():
        result = result.replace(placeholder, values[key])

    # 处理路径分隔符
    result = result.replace("/", str(Path("/")))
    # 清理多余的路径分隔符
    while "//" in result:
        result = result.replace("//", "/")

    target = (Path(output_base_dir) / result).resolve()
    base = Path(output_base_dir).resolve()
    if not target.is_relative_to(base):
        raise ValueError(f"禁止路径穿越: {target} 超出输出目录 {base}")
    return target
