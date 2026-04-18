# Paper Tool

PDF 文献自动分类与重命名工具。将 PDF 论文放入监控目录，自动提取元数据（标题、作者、年份等），通过 LLM 智能分类，并按模板规则重命名归档。

## 功能特性

- **实时监控** — 自动检测监控目录中的新 PDF 文件
- **智能分类** — 支持 Ollama / OpenAI / vLLM 多种 LLM 后端，自动提取论文元数据并分类
- **本地回退** — LLM 不可用时自动降级为正则提取 + 关键词匹配分类
- **模板重命名** — 自定义文件名模板，支持按分类创建子目录
- **操作回滚** — 所有操作记录在 SQLite 数据库中，支持单条回滚
- **可视化配置** — PyQt6 GUI 界面，所有配置项可直接编辑
- **系统托盘** — 最小化到托盘，暂停/恢复监控
- **配置热重载** — 修改配置文件后自动生效，无需重启
- **单实例运行** — 防止重复启动

## 快速开始

### 环境要求

- Python >= 3.11
- Windows（单实例限制依赖 Windows API）

### 安装

```bash
# 克隆仓库
git clone https://github.com/WangHNoob/paper-tool.git
cd paper-tool

# 安装依赖
pip install -e .

# 或者使用 uv
uv pip install -e .
```

### 启动

```bash
# 使用默认配置文件 config.yaml
python -m paper_tool

# 指定配置文件
python -m paper_tool -c /path/to/config.yaml
```

首次启动会在当前目录自动创建默认配置文件 `config.yaml`、监控目录 `Inbox/` 和输出目录 `Sorted/`。

### 使用流程

1. 启动应用后，将 PDF 论文文件放入 `Inbox/` 目录
2. 工具自动检测新文件，提取文本并调用 LLM 分析
3. 分析完成后，文件被重命名并移动到 `Sorted/` 对应的分类子目录
4. 在 GUI 中查看操作日志，必要时可回滚

## 配置说明

配置文件为 `config.yaml`，首次启动自动生成。也可通过 GUI 界面直接编辑。

### 完整配置项

```yaml
# 文件监控
monitor:
  watch_dir: "./Inbox"        # 监控目录，新 PDF 放入此目录
  recursive: false             # 是否递归监控子目录
  debounce_seconds: 3.0        # 防抖间隔（秒），避免重复处理

# LLM 后端: ollama / openai / vllm
llm_backend: "ollama"

# Ollama 配置
ollama:
  model: "qwen2.5:7b"
  base_url: "http://localhost:11434"
  temperature: 0.3
  timeout: 60.0

# OpenAI 兼容 API 配置
openai:
  api_key: ""                              # 填写你的 API Key
  base_url: "https://api.openai.com/v1"    # 可改为其他兼容接口地址
  model: "gpt-4o-mini"
  temperature: 0.3
  max_tokens: 1024

# vLLM 配置
vllm:
  base_url: "http://localhost:8000/v1"
  model: "Qwen/Qwen2.5-7B-Instruct"
  api_key: "EMPTY"
  temperature: 0.3
  timeout: 60.0

# 文件重命名
rename:
  template: "{分类}/{作者}_{年份}_{标题}.pdf"   # 重命名模板
  output_base_dir: "./Sorted"                   # 输出根目录
  conflict_strategy: "append_number"             # 冲突策略

# 分类标签
classification:
  labels:
    - "机器学习"
    - "自然语言处理"
    - "计算机视觉"
    - "数据挖掘"
    - "网络与安全"
    - "系统与架构"
    - "其他"

# 数据库
database:
  path: "data/paper_tool.db"

# 日志级别: DEBUG / INFO / WARNING / ERROR
log_level: "INFO"
```

### LLM 后端选择

| 后端 | 适用场景 | 说明 |
|------|----------|------|
| `ollama` | 本地部署，无需联网 | 需先安装 [Ollama](https://ollama.ai) 并下载模型 |
| `openai` | 使用 OpenAI 或兼容 API | 支持任何 OpenAI 兼容接口（如 DeepSeek、通义千问等） |
| `vllm` | 自部署 vLLM 推理服务 | 适合有 GPU 服务器的场景 |

切换后端只需修改 `llm_backend` 字段，并在对应后端配置中填入参数。

### 重命名模板

模板支持以下变量：

| 变量 | 说明 | 示例 |
|------|------|------|
| `{标题}` | 论文标题 | 深度学习在NLP中的应用 |
| `{作者}` | 作者（最多3位，逗号分隔） | 张三, 李四 |
| `{年份}` | 发表年份 | 2024 |
| `{期刊}` | 期刊或会议名 | ACL |
| `{关键词}` | 关键词（最多5个） | 深度学习, NLP |
| `{分类}` | 分类标签 | 自然语言处理 |

模板中使用 `/` 会自动创建子目录。示例：

```
{分类}/{作者}_{年份}_{标题}.pdf
→ Sorted/自然语言处理/张三_2024_深度学习在NLP中的应用.pdf

{年份}/{标题}.pdf
→ Sorted/2024/深度学习在NLP中的应用.pdf
```

### 冲突策略

当目标路径已存在同名文件时：

- `append_number` — 自动追加编号，如 `标题.pdf` → `标题_1.pdf`
- `skip` — 跳过不处理，保留原文件

### 默认分类标签

```
机器学习、自然语言处理、计算机视觉、数据挖掘、网络与安全、系统与架构、其他
```

可在配置文件中自由增删分类标签。

## GUI 界面

应用启动后显示 PyQt6 图形界面：

- **配置页** — 编辑所有配置项，保存后立即生效
- **操作日志** — 查看所有文件处理记录，支持刷新、回滚、删除
- **运行日志** — 实时查看应用运行日志
- **系统托盘** — 关闭窗口后最小化到托盘，右键菜单可暂停/恢复监控
- **主题切换** — 支持浅色/深色主题，默认跟随系统

## 处理流程

```
新 PDF 文件 → 文件验证 → 文本提取 (PyMuPDF) → LLM 分类 → 模板渲染 → 文件移动 → 记录日志
                                              ↓ (LLM 失败)
                                        关键词回退分类
```

1. **文件验证** — 检查文件是否存在、非空、PDF 头合法
2. **文本提取** — 使用 PyMuPDF 提取前 10 页文本（最多 8000 字符）
3. **LLM 分类** — 调用大语言模型提取标题、作者、年份等元数据并分类
4. **回退分类** — LLM 不可用时，使用正则提取 + 关键词匹配
5. **模板渲染** — 根据配置的重命名模板生成新文件路径
6. **文件移动** — 将文件移动到输出目录，处理命名冲突
7. **记录日志** — 写入 SQLite 数据库，用于查询和回滚

## 常见问题

### LLM 连接失败

- **Ollama**: 确认 Ollama 已启动（`ollama serve`），且模型已下载（`ollama pull qwen2.5:7b`）
- **OpenAI**: 检查 `api_key` 是否正确，`base_url` 是否可达
- 网络不通时，工具会自动降级为本地关键词分类，不影响基本使用

### 文件未被处理

- 确认文件放入了 `monitor.watch_dir` 指定的目录
- 确认文件后缀为 `.pdf`
- 检查文件是否完全写入（复制大文件时需等待完成）
- 查看运行日志页是否有错误信息

### 如何回滚误操作

在「操作日志」页面选中一条记录，点击「回滚选中」，文件会被移回原始位置。

## 项目结构

```
src/paper_tool/
├── __main__.py          # 入口
├── main.py              # 应用生命周期管理
├── config/              # 配置加载与校验
│   ├── loader.py
│   └── schema.py
├── core/                # 核心处理流程
│   ├── models.py        # 数据模型
│   ├── pipeline.py      # 处理流水线
│   └── queue.py         # 异步任务队列
├── db/                  # SQLite 数据库
│   ├── database.py
│   ├── operations.py
│   └── rollback.py
├── extractor/           # PDF 文本提取
│   └── text.py
├── llm/                 # LLM 集成
│   ├── classifier.py    # 分类器（LLM + 关键词回退）
│   └── factory.py       # 后端工厂
├── monitor/             # 文件监控
│   └── watcher.py
├── renamer/             # 文件重命名与移动
│   ├── mover.py
│   └── template.py
├── ui/                  # 用户界面
│   ├── gui.py           # PyQt6 主窗口
│   └── tray.py          # 系统托盘
└── utils/               # 工具模块
    ├── asyncio_thread.py # 异步线程管理
    ├── logging.py
    ├── retry.py
    └── sanitize.py
```

## 技术栈

- **GUI**: PyQt6
- **文件监控**: watchdog
- **PDF 解析**: PyMuPDF
- **LLM 集成**: LangChain (langchain-core, langchain-openai, langchain-ollama)
- **配置管理**: Pydantic + PyYAML
- **数据库**: SQLite

## License

MIT
