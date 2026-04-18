"""论文分类器 - LLM 解析 + 本地回退"""

import json
import logging
import re
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from ..core.models import ClassifyResult, PaperInfo

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个专业的学术论文分析助手。请根据论文文本内容，提取以下信息并以 JSON 格式返回：

{
  "title": "论文标题",
  "authors": ["作者1", "作者2"],
  "year": "发表年份",
  "journal": "期刊或会议名",
  "keywords": ["关键词1", "关键词2"],
  "category": "从下方标签中选择一个",
  "confidence": 0.95,
  "reasoning": "分类理由"
}

可选分类标签：
{labels}

要求：
- 标题取论文原标题，不要翻译
- 作者名保持原始语言
- 只返回 JSON，不要其他内容"""

FALLBACK_PROMPT = """请从以下论文文本中提取标题和作者。只返回 JSON，格式如下：
{{"title": "标题", "authors": ["作者1"], "year": "年份"}}

论文文本：
{text}"""


class PaperClassifier:
    """论文分类器"""

    def __init__(
        self,
        chat_model: BaseChatModel | None,
        labels: list[str],
        custom_prompt: str | None = None,
    ):
        self._chat_model = chat_model
        self._labels = labels
        self._custom_prompt = custom_prompt or SYSTEM_PROMPT

    def _build_messages(self, paper_info: PaperInfo) -> list:
        system_text = self._custom_prompt.replace(
            "{labels}", "\n".join(f"- {l}" for l in self._labels)
        )
        text = self._sanitize_prompt_text(paper_info.text[:8000] if len(paper_info.text) > 8000 else paper_info.text)
        return [
            SystemMessage(content=system_text),
            HumanMessage(content=f"文件名: {paper_info.file_name}\n\n{text}"),
        ]

    @staticmethod
    def _sanitize_prompt_text(text: str) -> str:
        """移除潜在的提示词注入内容"""
        lines = text.splitlines()
        blocked = {
            "ignore", "disregard", "previous", "system prompt",
            "you are now", "you now have", "forget all",
            "override", "new instruction",
        }
        cleaned = [
            line for line in lines
            if not any(b in line.lower() for b in blocked)
        ]
        return "\n".join(cleaned)

    async def classify(self, paper_info: PaperInfo) -> tuple[PaperInfo, ClassifyResult]:
        """用 LLM 提取元数据并分类"""
        if self._chat_model is None:
            return self.fallback_classify(paper_info)

        messages = self._build_messages(paper_info)

        response = await self._chat_model.ainvoke(messages)
        content = self._get_text(response)
        logger.debug("LLM 原始返回: %s", content[:300])

        result = self._parse_json(content)

        if result:
            paper_info.title = result.get("title", "") or paper_info.file_path.stem
            paper_info.authors = result.get("authors", []) or []
            paper_info.year = str(result.get("year", ""))
            paper_info.journal = result.get("journal", "")
            paper_info.keywords = result.get("keywords", []) or []

            category = result.get("category", "其他")
            if category not in self._labels:
                category = self._labels[-1]

            logger.info(
                "LLM 分类完成: %s -> %s (标题: %s)",
                paper_info.file_name, category, paper_info.title[:30],
            )
            return paper_info, ClassifyResult(
                category=category,
                confidence=float(result.get("confidence", 0.8)),
                reasoning=result.get("reasoning", ""),
            )

        # JSON 解析失败，尝试简单提取
        logger.warning("完整 JSON 解析失败，尝试简单提取")
        return await self._simple_extract(paper_info)

    async def _simple_extract(self, paper_info: PaperInfo) -> tuple[PaperInfo, ClassifyResult]:
        """只用 LLM 提取标题作者，分类用关键词"""
        if self._chat_model is None:
            return self.fallback_classify(paper_info)

        text = self._sanitize_prompt_text(paper_info.text[:3000])
        prompt = FALLBACK_PROMPT.replace("{text}", text)

        try:
            response = await self._chat_model.ainvoke([HumanMessage(content=prompt)])
            content = self._get_text(response)
            logger.debug("简单提取返回: %s", content[:200])
            result = self._parse_json(content)
            if result:
                paper_info.title = result.get("title", "") or paper_info.file_path.stem
                paper_info.authors = result.get("authors", []) or []
                paper_info.year = str(result.get("year", ""))
        except Exception as e:
            logger.warning("简单提取失败: %s", e)

        if not paper_info.title or paper_info.title == paper_info.file_path.stem:
            self._regex_extract(paper_info)

        category = self._keyword_classify(paper_info.text)
        return paper_info, ClassifyResult(
            category=category,
            confidence=0.5,
            reasoning="LLM 部分失败，结合关键词分类",
            is_fallback=True,
        )

    def fallback_classify(self, paper_info: PaperInfo) -> tuple[PaperInfo, ClassifyResult]:
        """纯本地回退：正则提取 + 关键词分类"""
        self._regex_extract(paper_info)
        category = self._keyword_classify(paper_info.text)
        logger.info("本地回退分类: %s -> %s", paper_info.file_name, category)
        return paper_info, ClassifyResult(
            category=category,
            confidence=0.3,
            reasoning="LLM 未启用，使用本地回退",
            is_fallback=True,
        )

    # ── 辅助方法 ──

    @staticmethod
    def _get_text(response: Any) -> str:
        """从 LLM 响应中提取文本"""
        content = response.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and "text" in item:
                    parts.append(item["text"])
            return "".join(parts)
        return str(content)

    @staticmethod
    def _parse_json(text: str) -> dict | None:
        """从 LLM 回复中提取 JSON"""
        text = text.strip()
        # 尝试直接解析
        if text.startswith("{"):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass

        # 从 markdown 代码块中提取
        m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass

        # 找第一个 { 到最后一个 }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass

        return None

    def _keyword_classify(self, text: str) -> str:
        text_lower = text.lower()
        default = self._labels[-1] if "其他" in self._labels[-1] else self._labels[0]

        keyword_map = {
            "机器学习": ["machine learning", "neural network", "deep learning", "训练", "梯度",
                         "supervised", "unsupervised", "reinforcement"],
            "自然语言处理": ["nlp", "language model", "transformer", "文本", "语义",
                            "bert", "gpt", "tokeniz"],
            "计算机视觉": ["vision", "image", "detection", "segmentation", "视觉", "图像",
                          "cnn", "convolutional", "recogni"],
            "数据挖掘": ["mining", "clustering", "推荐", "挖掘", "聚类", "recommender"],
            "网络与安全": ["network", "security", "attack", "网络", "安全", "入侵", "cryptograph"],
            "系统与架构": ["system", "architecture", "distributed", "系统", "架构", "分布式",
                          "cloud", "container"],
        }

        best_score, best_cat = 0, default
        for cat, keywords in keyword_map.items():
            if cat not in self._labels:
                continue
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > best_score:
                best_score, best_cat = score, cat
        return best_cat

    @staticmethod
    def _regex_extract(paper_info: PaperInfo) -> None:
        """正则提取基础元数据"""
        text = paper_info.text

        if not paper_info.title or paper_info.title == paper_info.file_path.stem:
            first_line = text.strip().split("\n")[0].strip()
            paper_info.title = first_line[:80] if first_line else paper_info.file_path.stem

        if not paper_info.year:
            m = re.search(r'\b(19|20)\d{2}\b', text[:2000])
            if m:
                paper_info.year = m.group(0)

        if not paper_info.authors:
            # 中文学术论文：作者行在"摘要"之前
            m = re.search(r'([^\n]{5,100})\n(?:摘要|Abstract|摘\s*要)', text[:2000], re.DOTALL)
            if m:
                author_line = m.group(1).strip()
                if len(author_line) < 100:
                    paper_info.authors = [a.strip() for a in re.split(r'[,，、\s]+', author_line) if a.strip()][:5]
