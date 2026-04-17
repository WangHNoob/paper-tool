"""论文分类器 - 封装 LangChain 调用 + prompt"""

import logging

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from ..core.models import ClassifyResult, PaperInfo
from .schemas import PaperClassifyResult

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = """你是一个专业的学术论文分类助手。根据论文的文本内容，你需要：
1. 提取论文的元数据（标题、作者、年份、期刊/会议、关键词）
2. 从给定的分类标签中选择最合适的分类
3. 给出分类置信度和理由

可选的分类标签：
{labels}

请仔细分析论文内容，确保提取的信息准确。"""


class PaperClassifier:
    """论文分类器"""

    def __init__(
        self,
        chat_model: BaseChatModel,
        labels: list[str],
        custom_prompt: str | None = None,
    ):
        self._structured_llm = chat_model.with_structured_output(PaperClassifyResult)
        self._labels = labels
        self._custom_prompt = custom_prompt

    def _build_messages(self, paper_info: PaperInfo) -> list:
        """构建 LLM 消息列表"""
        system_text = self._custom_prompt or DEFAULT_SYSTEM_PROMPT
        system_text = system_text.format(labels="\n".join(f"- {l}" for l in self._labels))

        # 截取文本以避免超出 token 限制
        text = paper_info.text[:6000] if len(paper_info.text) > 6000 else paper_info.text

        return [
            SystemMessage(content=system_text),
            HumanMessage(
                content=f"请分析以下论文内容并提取信息：\n\n{paper_info.file_name}\n\n{text}"
            ),
        ]

    async def classify(self, paper_info: PaperInfo) -> tuple[PaperInfo, ClassifyResult]:
        """对论文进行分类。

        Args:
            paper_info: 论文信息（包含文本）

        Returns:
            更新后的 PaperInfo 和 ClassifyResult 元组
        """
        messages = self._build_messages(paper_info)
        result: PaperClassifyResult = await self._structured_llm.ainvoke(messages)

        # 合并 LLM 提取的元数据到 paper_info
        paper_info.title = result.title
        paper_info.authors = result.authors
        paper_info.year = result.year
        paper_info.journal = result.journal
        paper_info.keywords = result.keywords

        classify_result = ClassifyResult(
            category=result.category,
            confidence=result.confidence,
            reasoning=result.reasoning,
        )

        logger.info(
            "分类完成: %s -> %s (置信度: %.2f)",
            paper_info.file_name,
            result.category,
            result.confidence,
        )

        return paper_info, classify_result

    def fallback_classify(self, paper_info: PaperInfo) -> ClassifyResult:
        """规则回退分类：当 LLM 不可用时使用简单规则。

        基于文本关键词匹配进行分类。
        """
        text_lower = paper_info.text.lower()
        category = self._labels[-1] if "其他" in self._labels[-1] else self._labels[0]

        keyword_map = {
            "机器学习": ["machine learning", "neural network", "deep learning", "训练", "梯度", "machine learning"],
            "自然语言处理": ["nlp", "language model", "transformer", "文本", "语义", "language"],
            "计算机视觉": ["vision", "image", "detection", "segmentation", "视觉", "图像", "识别"],
            "数据挖掘": ["mining", "clustering", "推荐", "挖掘", "聚类"],
            "网络与安全": ["network", "security", "attack", "网络", "安全", "入侵"],
            "系统与架构": ["system", "architecture", "distributed", "系统", "架构", "分布式"],
        }

        best_score = 0
        for cat, keywords in keyword_map.items():
            if cat not in self._labels:
                continue
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > best_score:
                best_score = score
                category = cat

        logger.info("规则回退分类: %s -> %s", paper_info.file_name, category)
        return ClassifyResult(
            category=category,
            confidence=0.3,
            reasoning="LLM 不可用，使用关键词匹配回退分类",
            is_fallback=True,
        )
