"""重命名模块测试"""

import shutil
import tempfile
from pathlib import Path

import pytest

from paper_tool.core.models import ClassifyResult, PaperInfo
from paper_tool.renamer.mover import FileMover
from paper_tool.renamer.template import render_template


@pytest.fixture
def paper_info(tmp_path):
    return PaperInfo(
        file_path=tmp_path / "test.pdf",
        title="Deep Learning for Image Classification",
        authors=["Zhang San", "Li Si"],
        year="2024",
        journal="CVPR",
        keywords=["deep learning", "CNN"],
    )


@pytest.fixture
def classify_result():
    return ClassifyResult(
        category="计算机视觉",
        confidence=0.95,
        reasoning="Test reasoning",
    )


class TestTemplate:
    def test_render_basic_template(self, paper_info, classify_result, tmp_path):
        result = render_template(
            template="{分类}/{作者}_{年份}_{标题}.pdf",
            paper_info=paper_info,
            classify_result=classify_result,
            output_base_dir=str(tmp_path),
        )
        assert "计算机视觉" in str(result)
        assert "2024" in str(result)
        assert result.suffix == ".pdf"

    def test_render_with_missing_fields(self, tmp_path):
        info = PaperInfo(file_path=tmp_path / "test.pdf")
        result = ClassifyResult(category="其他", confidence=0.3, reasoning="")
        path = render_template(
            template="{分类}/{标题}.pdf",
            paper_info=info,
            classify_result=result,
            output_base_dir=str(tmp_path),
        )
        # 空标题应该回退到 "未知标题"
        assert "未知标题" in str(path)

    def test_render_special_characters(self, tmp_path):
        info = PaperInfo(
            file_path=tmp_path / "test.pdf",
            title='Paper: A "Novel" <Approach>',
        )
        result = ClassifyResult(category="ML", confidence=0.5, reasoning="")
        path = render_template(
            template="{标题}.pdf",
            paper_info=info,
            classify_result=result,
            output_base_dir=str(tmp_path),
        )
        filename = path.name
        assert ":" not in filename
        assert "<" not in filename
        assert ">" not in filename


class TestFileMover:
    def test_move_file(self, tmp_path):
        src = tmp_path / "source.pdf"
        src.write_bytes(b"%PDF-1.4 test content")
        dst = tmp_path / "output" / "renamed.pdf"

        mover = FileMover()
        result = mover.move(src, dst)

        assert result.exists()
        assert not src.exists()

    def test_move_conflict_append_number(self, tmp_path):
        src = tmp_path / "source.pdf"
        src.write_bytes(b"%PDF-1.4 test")
        dst = tmp_path / "output" / "renamed.pdf"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(b"existing")

        mover = FileMover(conflict_strategy="append_number")
        result = mover.move(src, dst)

        assert result.exists()
        assert result.name == "renamed_1.pdf"

    def test_move_source_not_found(self, tmp_path):
        src = tmp_path / "nonexistent.pdf"
        dst = tmp_path / "output.pdf"

        mover = FileMover()
        with pytest.raises(FileNotFoundError):
            mover.move(src, dst)
