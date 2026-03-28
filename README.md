# Design Skill Miner

`design-skill-miner` 是一个本地运行的设计沉淀 Agent。

它会读取本地会话导出，识别重复出现的设计讨论，把这些讨论整理成规则洞察、审校结果和可编辑的 Skill 草稿。

适合这类场景：

- 组件规范反复被纠正
- 页面结构和交互模式反复被讨论
- 样式系统口径反复被统一
- 文案、反馈、状态规则反复被改写

## 特性

- 本地运行，不依赖云端项目存储
- 支持 CLI 和本地 Web UI
- 先做确定性提炼，再做质量审校
- 可选接入 OpenAI-compatible LLM 做润色
- 输出可编辑草稿，而不是直接覆盖正式规范
- 发布默认进入暂存目录，而不是直接写入正式技能库

## 适合谁

- 使用本地会话导出的设计团队
- 希望把历史讨论沉淀成可复用规则的人
- 想把设计对话转成 Skill / Prompt / Guide 草稿的人

## 不重点解决什么

- 通用知识库管理
- 多人在线协作平台
- 零审核自动发布正式规范
- 远程托管的 Agent 平台

## 快速开始

### 安装

```bash
python3 -m pip install -e .
```

安装完成后：

```bash
design-skill-miner --help
```

### 本地配置

复制示例配置：

```bash
cp .design-skill-miner.toml.example .design-skill-miner.toml
```

如果你使用 Kimi / Moonshot：

```bash
export MOONSHOT_API_KEY="your-key"
```

然后在本地 `.design-skill-miner.toml` 中配置：

```toml
[llm]
enabled = false
provider = "openai-compatible"
base_url = "https://api.moonshot.ai/v1"
model = "moonshot-v1-8k"
api_key_env = "MOONSHOT_API_KEY"
```

注意：

- `.design-skill-miner.toml` 仅用于本地，不应提交到仓库
- 真实密钥只放环境变量，不要写进代码或配置文件

## 使用方式

### 1. Web UI

推荐给设计师或需要人工浏览草稿的人。

```bash
./run-local.sh serve --host 127.0.0.1 --port 8765
```

打开：

- [http://127.0.0.1:8765](http://127.0.0.1:8765)

流程：

1. 选择项目目录
2. 选择是否启用润色
3. 点击一次“启动智能体”
4. 查看规则洞察、审校结果和 Skill 草稿
5. 需要时编辑草稿并发布到暂存区

### 2. CLI

查看项目：

```bash
design-skill-miner projects /path/to/sessions
```

生成规则洞察：

```bash
design-skill-miner scan /path/to/sessions \
  --cwd-prefix "/path/to/project" \
  --out ./out
```

直接运行完整 Agent：

```bash
design-skill-miner agent-mine /path/to/sessions \
  --cwd-prefix "/path/to/project" \
  --out ./agent-out \
  --skill-name my-design-skill
```

启用 LLM 润色：

```bash
design-skill-miner agent-mine /path/to/sessions \
  --cwd-prefix "/path/to/project" \
  --out ./agent-out \
  --skill-name my-design-skill \
  --enable-llm
```

将草稿写入现有技能目录：

```bash
design-skill-miner apply-to-skill ./skill-draft /path/to/existing-skill
```

## 输出内容

完整 Agent 运行通常会生成：

```text
agent-out/
├── agent-run.json
├── draft/
│   ├── SKILL.md
│   ├── manifest.json
│   └── references/
└── reports/
    ├── insights.json
    ├── insights.md
    └── review.json
```

其中：

- `insights.*`：规则候选和证据
- `review.json`：质量审校结果
- `draft/`：可编辑的 Skill 草稿
- `agent-run.json`：本次 Agent 执行元数据

## 项目结构

```text
design-skill-miner/
├── src/design_skill_miner/   # Agent 核心
├── web/                      # 本地 Web UI
├── docs/                     # 架构文档
├── README.md
├── CONTRIBUTING.md
├── SECURITY.md
├── CHANGELOG.md
└── .design-skill-miner.toml.example
```

核心模块职责：

- `pipeline.py`：确定性主流程
- `agent.py`：Agent 编排、重规划、产物落盘
- `review.py`：质量审校和自动裁剪
- `llm.py`：OpenAI-compatible LLM 接入
- `draft_skill.py`：草稿文件生成
- `publish_skill.py`：发布到暂存目录
- `web.py` / `web_support.py`：Web 服务与接口
- `run_jobs.py`：后台任务状态管理

更详细的结构说明见 [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

## 开发

静态检查：

```bash
node --check web/app.js
```

本地启动：

```bash
./run-local.sh serve --host 127.0.0.1 --port 8765
```

## 开源前注意事项

- 不要提交 `.design-skill-miner.toml`
- 不要提交真实会话数据
- 不要提交真实 API Key
- 提交前先看一次 `git status`

更多细节见 [SECURITY.md](./SECURITY.md)。

## 路线图

- 提升规则聚类与去重质量
- 增强审校和回退策略
- 改善 Web 端任务监控体验
- 增加更多输出格式和发布适配

## 贡献

见 [CONTRIBUTING.md](./CONTRIBUTING.md)。

## 许可证

MIT，见 [LICENSE](./LICENSE)。
