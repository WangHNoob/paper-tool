"""测试配置 fixtures"""

import os
import tempfile
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def tmp_dir():
    """创建临时目录"""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def sample_config_dict():
    """返回测试用的配置字典"""
    return {
        "monitor": {
            "watch_dir": "/tmp/papers_inbox",
            "recursive": False,
            "debounce_seconds": 1.0,
            "file_extensions": [".pdf"],
        },
        "llm_backend": "ollama",
        "ollama": {
            "model": "qwen2.5:7b",
            "base_url": "http://localhost:11434",
            "temperature": 0.3,
        },
        "rename": {
            "template": "{分类}/{作者}_{年份}_{标题}.pdf",
            "output_base_dir": "/tmp/papers_sorted",
            "conflict_strategy": "append_number",
        },
        "classification": {
            "labels": ["机器学习", "自然语言处理", "计算机视觉", "其他"],
        },
        "database": {"path": ":memory:"},
        "log_level": "DEBUG",
    }


@pytest.fixture
def config_file(tmp_dir, sample_config_dict):
    """创建临时配置文件"""
    config_path = tmp_dir / "config.yaml"
    config_path.write_text(yaml.dump(sample_config_dict), encoding="utf-8")
    return config_path


@pytest.fixture
def db(tmp_dir):
    """创建内存数据库"""
    from paper_tool.db.database import Database

    database = Database(":memory:")
    database.connect()
    yield database
    database.close()
