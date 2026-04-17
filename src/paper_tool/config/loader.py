"""YAML 配置加载/校验/热重载"""

import hashlib
import logging
import time
from pathlib import Path

import yaml
from pydantic import ValidationError

from .schema import AppConfig

logger = logging.getLogger(__name__)


class ConfigLoader:
    """配置加载器，支持热重载"""

    def __init__(self, config_path: str | Path):
        self._path = Path(config_path)
        self._config: AppConfig | None = None
        self._last_hash: str = ""

    def load(self) -> AppConfig:
        """加载并校验配置文件"""
        text = self._path.read_text(encoding="utf-8")
        raw = yaml.safe_load(text)
        self._config = AppConfig.model_validate(raw)
        self._last_hash = hashlib.md5(text.encode()).hexdigest()
        logger.info("配置加载成功: %s", self._path)
        return self._config

    @property
    def config(self) -> AppConfig:
        if self._config is None:
            raise RuntimeError("配置尚未加载，请先调用 load()")
        return self._config

    def save(self, config: AppConfig) -> None:
        """将 AppConfig 序列化并写回 YAML 文件。

        Args:
            config: 要保存的配置对象

        Raises:
            OSError: 文件写入失败
        """
        raw = config.model_dump()
        text = yaml.dump(raw, allow_unicode=True, default_flow_style=False, sort_keys=False)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(text, encoding="utf-8")
        self._config = config
        self._last_hash = hashlib.md5(text.encode()).hexdigest()
        logger.info("配置已保存: %s", self._path)

    def check_and_reload(self) -> AppConfig | None:
        """检查配置文件是否变更，如果变更则重新加载。

        返回新的 AppConfig 如果已重新加载，否则返回 None。
        """
        try:
            text = self._path.read_text(encoding="utf-8")
            current_hash = hashlib.md5(text.encode()).hexdigest()
            if current_hash == self._last_hash:
                return None

            raw = yaml.safe_load(text)
            new_config = AppConfig.model_validate(raw)
            self._config = new_config
            self._last_hash = current_hash
            logger.info("配置热重载成功")
            return new_config
        except (ValidationError, yaml.YAMLError, OSError) as e:
            logger.warning("配置热重载失败，保持旧配置: %s", e)
            return None
