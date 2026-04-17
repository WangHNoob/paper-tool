"""论文分类器测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from paper_tool.core.models import ClassifyResult, PaperInfo
from paper_tool.llm.classifier import PaperClassifier
from paper_tool.llm.schemas import PaperClassifyResult
from pathlib import Path


@pytest.fixture
def paper_info(tmp_path):
    return PaperInfo(
        file_path=tmp_path / "test.pdf",
        text="This paper proposes a novel deep learning approach for image classification using convolutional neural networks.",
    )


@pytest.fixture
def labels():
    return ["机器学习", "自然语言处理", "计算机视觉", "其他"]


@pytest.fixture
def mock_result():
    return PaperClassifyResult(
        title="Deep Learning for Image Classification",
        authors=["Zhang San", "Li Si"],
        year="2024",
        journal="CVPR",
        keywords=["deep learning", "image classification", "CNN"],
        category="计算机视觉",
        confidence=0.95,
        reasoning="The paper focuses on image classification using CNNs.",
    )


class TestPaperClassifier:
    @pytest.mark.asyncio
    async def test_classify_success(self, paper_info, labels, mock_result):
        mock_llm = MagicMock()
        structured_mock = AsyncMock()
        structured_mock.ainvoke = AsyncMock(return_value=mock_result)
        mock_llm.with_structured_output.return_value = structured_mock

        classifier = PaperClassifier(mock_llm, labels)
        updated_info, result = await classifier.classify(paper_info)

        assert updated_info.title == "Deep Learning for Image Classification"
        assert updated_info.authors == ["Zhang San", "Li Si"]
        assert updated_info.year == "2024"
        assert result.category == "计算机视觉"
        assert result.confidence == 0.95

    def test_fallback_classify_ml(self, paper_info, labels):
        mock_llm = MagicMock()
        paper_info.text = "This paper discusses neural network training with gradient descent for machine learning."

        classifier = PaperClassifier(mock_llm, labels)
        result = classifier.fallback_classify(paper_info)

        assert result.is_fallback is True
        assert result.confidence == 0.3
        assert result.category in labels

    def test_fallback_classify_vision(self, paper_info, labels):
        mock_llm = MagicMock()
        paper_info.text = "We propose a new image detection and segmentation method for computer vision tasks."

        classifier = PaperClassifier(mock_llm, labels)
        result = classifier.fallback_classify(paper_info)

        assert result.category == "计算机视觉"

    def test_fallback_classify_nlp(self, paper_info, labels):
        mock_llm = MagicMock()
        paper_info.text = "This work presents a transformer-based language model for NLP tasks."

        classifier = PaperClassifier(mock_llm, labels)
        result = classifier.fallback_classify(paper_info)

        assert result.category == "自然语言处理"
