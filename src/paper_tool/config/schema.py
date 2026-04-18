"""Pydantic 配置模型定义"""

from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class MonitorConfig(BaseModel):
    watch_dir: str
    recursive: bool = False
    debounce_seconds: float = 3.0
    file_extensions: list[str] = Field(default_factory=lambda: [".pdf"])
    max_concurrency: int = 2

    @field_validator("max_concurrency")
    @classmethod
    def validate_concurrency(cls, v: int) -> int:
        if v < 1:
            raise ValueError("max_concurrency 必须 >= 1")
        return v

    @field_validator("debounce_seconds")
    @classmethod
    def validate_debounce(cls, v: float) -> float:
        if v < 0:
            raise ValueError("debounce_seconds 必须非负")
        return v


class OllamaConfig(BaseModel):
    model: str = "qwen2.5:7b"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.3
    timeout: float = 60.0


class OpenAIConfig(BaseModel):
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    temperature: float = 0.3
    max_tokens: int = 1024


class VLLMConfig(BaseModel):
    base_url: str = "http://localhost:8000/v1"
    model: str = "Qwen/Qwen2.5-7B-Instruct"
    api_key: str = "EMPTY"
    temperature: float = 0.3
    timeout: float = 60.0


class RenameConfig(BaseModel):
    template: str = "{分类}/{作者}_{年份}_{标题}.pdf"
    output_base_dir: str = "./Sorted"
    conflict_strategy: str = "append_number"

    @field_validator("conflict_strategy")
    @classmethod
    def validate_conflict_strategy(cls, v: str) -> str:
        if v not in ("append_number", "skip"):
            raise ValueError("conflict_strategy 必须是 append_number 或 skip")
        return v


class ClassificationConfig(BaseModel):
    labels: list[str] = Field(
        default_factory=lambda: [
            "机器学习",
            "自然语言处理",
            "计算机视觉",
            "数据挖掘",
            "网络与安全",
            "系统与架构",
            "其他",
        ]
    )
    prompt_template: str | None = None


class DatabaseConfig(BaseModel):
    path: str = "data/paper_tool.db"


class AppConfig(BaseModel):
    monitor: MonitorConfig
    llm_backend: str = "ollama"
    llm_enabled: bool = False
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    vllm: VLLMConfig = Field(default_factory=VLLMConfig)
    rename: RenameConfig = Field(default_factory=RenameConfig)
    classification: ClassificationConfig = Field(default_factory=ClassificationConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    log_level: str = "INFO"

    @field_validator("llm_backend")
    @classmethod
    def validate_llm_backend(cls, v: str) -> str:
        if v not in ("ollama", "openai", "vllm"):
            raise ValueError("llm_backend 必须是 ollama、openai 或 vllm")
        return v
