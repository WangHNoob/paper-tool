"""BaseChatModel 工厂方法"""

from langchain_core.language_models.chat_models import BaseChatModel

from ..config.schema import AppConfig


def create_chat_model(config: AppConfig) -> BaseChatModel:
    """根据配置创建对应的 BaseChatModel 实例。

    Args:
        config: 应用配置

    Returns:
        BaseChatModel 实例

    Raises:
        ValueError: 不支持的 LLM 后端
    """
    match config.llm_backend:
        case "ollama":
            from langchain_ollama import ChatOllama

            return ChatOllama(
                model=config.ollama.model,
                base_url=config.ollama.base_url,
                temperature=config.ollama.temperature,
                num_predict=4096,
            )
        case "openai":
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=config.openai.model,
                base_url=config.openai.base_url,
                api_key=config.openai.api_key,
                temperature=config.openai.temperature,
                max_tokens=config.openai.max_tokens,
            )
        case "vllm":
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=config.vllm.model,
                base_url=config.vllm.base_url,
                api_key=config.vllm.api_key,
                temperature=config.vllm.temperature,
            )
        case _:
            raise ValueError(f"不支持的 LLM 后端: {config.llm_backend}")
