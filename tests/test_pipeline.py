"""流水线测试"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import fitz
import pytest

from paper_tool.config.schema import AppConfig
from paper_tool.core.pipeline import Pipeline


@pytest.fixture
def sample_pdf(tmp_path):
    """创建测试 PDF"""
    pdf_path = tmp_path / "test.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        fitz.Point(72, 72),
        "Deep Learning for Image Classification\n"
        "Author: Zhang San\n"
        "Abstract: This paper proposes a CNN-based method.",
    )
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def app_config(sample_config_dict):
    return AppConfig.model_validate(sample_config_dict)


class TestPipeline:
    @pytest.mark.asyncio
    async def test_submit_to_queue(self, db, app_config):
        pipeline = Pipeline(app_config, db)
        # 不初始化分类器，测试队列提交
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4 test")
            path = Path(f.name)

        try:
            await pipeline.submit(path)
            assert pipeline.queue.pending_count >= 1
        finally:
            path.unlink(missing_ok=True)

    def test_init_classifier(self, db, app_config):
        """测试分类器初始化"""
        pipeline = Pipeline(app_config, db)
        # 应该能成功创建 Ollama 分类器（不需要连接）
        pipeline.init_classifier()
        assert pipeline._classifier is not None
