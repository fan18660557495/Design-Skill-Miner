# design-skill-miner

`design-skill-miner` 是一个本地运行的设计沉淀 Agent。

它的目标不是“总结聊天记录”，而是把日常设计对话里反复出现的判断，提炼成可编辑、可审阅、可发布的技能草稿。

适合处理这类内容：

- 交互模式反复被讨论
- 组件规范反复被纠正
- 样式系统口径反复被统一
- 文案和反馈规则反复被修改

一句话概括：

**它会读取本地会话导出，找出重复的设计讨论，整理成规则洞察，并生成技能草稿。**

## 这是一个什么 Agent

它是一个面向设计团队的本地 Agent，包含一条完整链路：

1. 读取本地会话导出
2. 识别项目归属
3. 过滤设计相关消息
4. 聚类重复讨论
5. 生成规则洞察
6. 生成技能草稿
7. 在浏览器里继续编辑
8. 发布到暂存目录

所以它不是单纯的：

- 报告生成器
- 文档整理脚本
- 规则总结工具

更准确地说，它是一个：

**把历史设计对话转成技能草稿的本地 Agent。**

## Agent 包含哪些部分

这个仓库由 4 层组成：

### 1. Agent 核心

负责真正的分析和生成。

- 读取会话
- 识别项目
- 过滤消息
- 聚类主题
- 提炼规则
- 生成草稿
- 发布草稿

对应目录：

- `src/design_skill_miner/`

### 2. 使用入口

负责让人真正用起来。

- 命令行入口
- 本地网页入口
- 双击启动入口

对应文件：

- `run-local.sh`
- `Start Design Skill Miner.command`
- `Start Design Skill Miner.bat`
- `start-design-skill-miner.sh`

### 3. 网页界面

负责给设计师使用，而不是只给工程师用。

网页流程是：

- 选择项目
- 生成规则洞察
- 生成技能草稿
- 编辑草稿
- 发布到暂存区

对应目录：

- `web/`

### 4. 测试和示例数据

负责保证这个 Agent 改动后不会马上坏掉。

对应目录：

- `tests/`

## 这个 Agent 实际会产出什么

它的核心输出有两层：

### 第一层：规则洞察

用于发现重复模式。

输出内容包括：

- `insights.json`
- `insights.md`

这些文件告诉你：

- 哪些设计话题反复出现
- 它们属于什么分类
- 频率有多高
- 证据来自哪些会话

### 第二层：技能草稿

用于把洞察转成可编辑的技能文档。

输出内容通常包括：

- `SKILL.md`
- `manifest.json`
- `references/principles.md`
- `references/page-patterns.md`
- `references/interaction-patterns.md`
- `references/component-patterns.md`
- `references/style-system.md`
- `references/content-rules.md`

这些草稿不是最终结论，而是：

**可继续编辑、可人工审核、可发布的候选规范。**

## 它适合谁

- 使用 Codex 或类似本地会话导出的设计团队
- 经常和 AI 一起讨论页面、组件、交互规则的人
- 想把历史对话沉淀成技能的人

## 它不重点解决什么

- 通用知识库整理
- 多人云端协作
- 自动安装到全局技能目录
- 不经审核直接发布正式规范

## 安装

### 标准安装

```bash
cd design-skill-miner
python3 -m pip install -e .
```

安装完成后可直接运行：

```bash
design-skill-miner --help
```

### 不安装直接运行

```bash
./run-local.sh --help
```

### 离线或受限环境

```bash
python3 setup.py develop --user
```

## 怎么使用这个 Agent

## 方式一：网页界面

这是最推荐的使用方式。

```bash
cd design-skill-miner
./run-local.sh serve --host 127.0.0.1 --port 8765
```

打开：

- `http://127.0.0.1:8765`

使用流程：

1. 选择项目目录
2. 生成规则洞察
3. 生成技能草稿
4. 在浏览器里继续编辑
5. 发布到暂存目录

### 一键启动

- macOS：双击 `Start Design Skill Miner.command`
- Windows：双击 `Start Design Skill Miner.bat`
- Linux：运行 `./start-design-skill-miner.sh`

## 方式二：命令行

### 查看识别到的项目

```bash
design-skill-miner projects /path/to/sessions
```

### 建立索引

```bash
design-skill-miner index /path/to/sessions --out ./out/index.json
```

### 生成规则洞察

```bash
design-skill-miner scan /path/to/sessions \
  --cwd-prefix "/path/to/project" \
  --out ./out
```

### 基于洞察生成技能草稿

```bash
design-skill-miner draft-skill ./out/insights.json \
  --out ./skill-draft \
  --skill-name my-design-skill
```

### 直接从会话生成技能草稿

```bash
design-skill-miner mine-skill /path/to/sessions \
  --cwd-prefix "/path/to/project" \
  --out ./skill-draft \
  --skill-name my-design-skill
```

### 把审核后的草稿写入技能目录

```bash
design-skill-miner apply-to-skill ./skill-draft /path/to/existing-skill
```

### 启动网页

```bash
design-skill-miner serve --host 127.0.0.1 --port 8765
```

## 输出分类

目前默认会整理到这些分类：

- `principles`
- `page-patterns`
- `interaction-patterns`
- `component-patterns`
- `style-system`
- `content-rules`

## 文件夹和文件是怎么用的

下面这部分按“一个 Agent 仓库”的视角来解释。

## 根目录

### `README.md`

项目入口说明。介绍这个 Agent 是什么、怎么运行、输出什么。

### `LICENSE`

开源协议。

### `pyproject.toml`

现代 Python 打包配置。给标准安装方式使用。

### `setup.py`

后备安装入口。适合离线或打包环境不完整时使用。

### `run-local.sh`

本地启动入口。开发时最常用。

它做的事很简单：

- 把 `src/` 放进 `PYTHONPATH`
- 运行 `python3 -m design_skill_miner`

### `Start Design Skill Miner.command`

macOS 双击启动器。

### `Start Design Skill Miner.bat`

Windows 双击启动器。

### `start-design-skill-miner.sh`

Linux 启动脚本。

## `src/design_skill_miner/`

这里是 Agent 的核心。

### `__main__.py`

模块入口，让 `python -m design_skill_miner` 可以直接运行。

### `cli.py`

命令行入口。负责注册和分发这些命令：

- `projects`
- `index`
- `scan`
- `draft-skill`
- `mine-skill`
- `apply-to-skill`
- `serve`

### `models.py`

核心数据结构定义，比如：

- session
- candidate message
- insight

### `ingest.py`

读取本地会话导出，解析 session 数据。

### `attribution.py`

根据项目路径前缀或上下文信息识别项目归属。

### `filter.py`

从原始会话里筛出设计相关消息，过滤无关内容。

### `cluster.py`

把相似讨论聚成重复主题。

### `distill.py`

把重复主题进一步整理成规则洞察。

### `pipeline.py`

主流程编排。

它把这几步串起来：

- ingest
- attribution
- filter
- cluster
- distill

### `report.py`

把规则洞察写成 `json` 和 `md` 报告。

### `draft_skill.py`

把规则洞察转成技能草稿文件。

### `apply_skill.py`

把审核后的草稿合并进已有技能目录，但不直接覆盖手写核心部分。

### `publish_skill.py`

把草稿发布到暂存目录。

### `indexer.py`

负责建立索引和汇总项目。

### `config.py`

读取配置文件。

### `web.py`

本地网页服务入口。

### `web_support.py`

网页界面调用的后端操作层，负责把网页动作接到 Agent 核心流程上。

## `web/`

这里是网页界面。

### `index.html`

页面结构。

### `styles.css`

页面样式。

### `app.js`

页面交互逻辑，包括：

- 步骤切换
- 生成规则洞察
- 生成草稿
- 草稿编辑
- 发布到暂存区

## `tests/`

建议保留。

它不是冗余目录，而是这个 Agent 的最小质量保障。

### `tests/test_pipeline.py`

主流程测试，覆盖：

- 生成规则洞察
- 生成技能草稿
- 发布到暂存区

### `tests/fixtures/`

最小测试数据。

如果以后你改了聚类、草稿结构、发布流程，这些测试能帮你快速发现是否回归。

如果只是你个人临时本地使用、以后也不再维护，`tests/` 可以删。  
但如果这个仓库要给别人用、或者准备开源，建议保留。

## 开发

运行测试：

```bash
python3 -m unittest discover -s tests -v
```

不安装直接启动网页：

```bash
./run-local.sh serve --host 127.0.0.1 --port 8765
```

## 说明

- 生成的规则洞察和草稿是候选内容，不是最终结论
- 发布会进入暂存目录，不会直接进入全局技能目录
- 浏览器内编辑更适合做清洗和调整，不适合大规模文档编写
