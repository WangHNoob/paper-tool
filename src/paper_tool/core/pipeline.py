"""处理流水线编排"""

import asyncio
import json
import logging
from pathlib import Path

from ..config.schema import AppConfig
from ..db.database import Database
from ..db.operations import record_operation
from ..extractor.text import PyMuPDFExtractor
from ..llm.classifier import PaperClassifier
from ..llm.factory import create_chat_model
from ..renamer.mover import FileMover
from ..renamer.template import render_template
from .models import ClassifyResult, PaperInfo, TaskStatus
from .queue import ProcessingQueue

logger = logging.getLogger(__name__)


class Pipeline:
    """处理流水线，编排 PDF 文件的抽取、分类、重命名流程"""

    def __init__(self, config: AppConfig, db: Database):
        self._config = config
        self._db = db
        self._extractor = PyMuPDFExtractor()
        self._queue = ProcessingQueue(max_concurrency=2)
        self._classifier: PaperClassifier | None = None
        self._mover = FileMover(conflict_strategy=config.rename.conflict_strategy)
        self._running = False
        self._consumer_task: asyncio.Task | None = None

    @property
    def queue(self) -> ProcessingQueue:
        return self._queue

    def init_classifier(self) -> None:
        """初始化分类器"""
        chat_model = create_chat_model(self._config)
        self._classifier = PaperClassifier(
            chat_model=chat_model,
            labels=self._config.classification.labels,
            custom_prompt=self._config.classification.prompt_template,
        )
        logger.info("LLM 分类器已初始化，后端: %s", self._config.llm_backend)

    def start(self) -> None:
        """启动队列消费"""
        self._running = True
        self._consumer_task = asyncio.get_event_loop().create_task(self._consume())

    def stop(self) -> None:
        """停止队列消费"""
        self._running = False
        if self._consumer_task is not None:
            self._consumer_task.cancel()

    async def submit(self, path: Path) -> None:
        """提交文件到处理队列"""
        await self._queue.put(path)
        logger.info("文件已加入处理队列: %s", path.name)

    async def _consume(self) -> None:
        """队列消费协程"""
        while self._running:
            try:
                path = await asyncio.wait_for(self._queue.queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            task = self._queue.create_task(path)
            await self._queue.acquire()
            try:
                await self._process(task)
            except Exception as e:
                logger.error("处理失败 [%s]: %s", path.name, e)
                self._queue.update_task(
                    task.id,
                    status=TaskStatus.FAILED,
                    error_message=str(e),
                )
            finally:
                self._queue.release()

    async def _process(self, task) -> None:
        """处理单个文件的流水线"""
        paper_info = task.paper_info
        path = paper_info.file_path

        logger.info("开始处理: %s", path.name)
        self._queue.update_task(task.id, status=TaskStatus.PROCESSING)

        # Step 1: 文件验证
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {path}")
        if path.stat().st_size == 0:
            raise ValueError(f"文件为空: {path}")

        # Step 2: 文本抽取 [to_thread]
        paper_info.text = await asyncio.to_thread(
            self._extractor.extract, path
        )

        if not paper_info.text.strip():
            raise ValueError(f"无法从 PDF 中抽取文本: {path.name}")

        # Step 3: AI 分类 [async]
        classify_result = await self._classify(paper_info)

        # Step 4: 模板渲染
        new_path = render_template(
            template=self._config.rename.template,
            paper_info=paper_info,
            classify_result=classify_result,
            output_base_dir=self._config.rename.output_base_dir,
        )

        # Step 5: 文件移动 [to_thread]
        actual_path = await asyncio.to_thread(self._mover.move, path, new_path)

        # Step 6: 记录日志
        record_operation(
            self._db,
            original_path=str(path),
            original_name=path.name,
            new_path=str(actual_path),
            new_name=actual_path.name,
            category=classify_result.category,
            title=paper_info.title,
            authors=json.dumps(paper_info.authors, ensure_ascii=False),
            year=paper_info.year,
            journal=paper_info.journal,
            keywords=json.dumps(paper_info.keywords, ensure_ascii=False),
            confidence=classify_result.confidence,
            status="success",
        )

        self._queue.update_task(
            task.id,
            classify_result=classify_result,
            new_path=actual_path,
            status=TaskStatus.SUCCESS,
        )
        logger.info("处理完成: %s -> %s", path.name, actual_path.name)

    async def _classify(self, paper_info: PaperInfo) -> ClassifyResult:
        """分类论文，失败时回退到规则分类"""
        if self._classifier is None:
            logger.warning("分类器未初始化，使用回退分类")
            return ClassifyResult(
                category="其他",
                confidence=0.0,
                reasoning="分类器未初始化",
                is_fallback=True,
            )

        try:
            _, result = await self._classifier.classify(paper_info)
            return result
        except Exception as e:
            logger.warning("LLM 分类失败，使用回退分类: %s", e)
            _, result = self._classifier.fallback_classify(paper_info)
            return result
