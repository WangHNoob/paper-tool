"""LLM 结构化输出 Pydantic 模型"""

from pydantic import BaseModel, Field


class PaperClassifyResult(BaseModel):
    """LLM 结构化输出 schema"""

    title: str = Field(description="论文标题")
    authors: list[str] = Field(description="作者列表")
    year: str = Field(description="发表年份")
    journal: str = Field(description="期刊/会议名")
    keywords: list[str] = Field(description="关键词")
    category: str = Field(description="从给定标签中选择的分类")
    confidence: float = Field(ge=0, le=1, description="分类置信度")
    reasoning: str = Field(description="分类理由")
