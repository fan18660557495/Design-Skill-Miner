# 架构说明

## 项目做什么

`design-skill-miner` 会把本地会话导出中的重复设计讨论，整理成可编辑的 Skill 草稿。

它不是聊天摘要器，而是一条本地 Agent 工作流，主要包含这些步骤：

1. 读取本地会话导出
2. 归属到项目
3. 过滤设计相关消息
4. 聚类重复主题
5. 提炼候选规则
6. 做质量审校
7. 可选使用 LLM 做规则润色
8. 生成 Skill 草稿
9. 可选发布到暂存目录

## 端到端流程

```text
sessions -> ingest -> attribution -> filter -> cluster -> distill
         -> review -> optional llm polish -> draft files -> publish
```

## 主要分层

### 1. 确定性提炼主流程

这些模块负责从本地会话中产出规则洞察：

- `ingest.py`
- `attribution.py`
- `filter.py`
- `cluster.py`
- `distill.py`
- `pipeline.py`

### 2. Agent 工作流

这些模块负责执行编排、质量审校和可选 LLM 增强：

- `agent.py`
- `review.py`
- `llm.py`

### 3. 草稿与发布

这些模块负责把洞察变成可落地的草稿结果：

- `report.py`
- `draft_skill.py`
- `apply_skill.py`
- `publish_skill.py`

### 4. 使用入口

这些模块负责把能力暴露给用户：

- `cli.py`
- `web.py`
- `web_support.py`
- `run_jobs.py`
- `web/`

## 仓库结构

```text
design-skill-miner/
├── src/design_skill_miner/
│   ├── agent.py
│   ├── apply_skill.py
│   ├── attribution.py
│   ├── cli.py
│   ├── cluster.py
│   ├── config.py
│   ├── distill.py
│   ├── draft_skill.py
│   ├── filter.py
│   ├── indexer.py
│   ├── ingest.py
│   ├── llm.py
│   ├── models.py
│   ├── pipeline.py
│   ├── publish_skill.py
│   ├── report.py
│   ├── review.py
│   ├── run_jobs.py
│   ├── web.py
│   └── web_support.py
├── web/
├── docs/
├── README.md
├── CONTRIBUTING.md
├── SECURITY.md
└── CHANGELOG.md
```

## 输出结果

一次典型运行会生成：

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

## 配置模型

项目把公开配置和本地配置分开：

- 可以提交 `.design-skill-miner.toml.example`
- `.design-skill-miner.toml` 只保留在本地
- 真实密钥放在环境变量里

这样做是为了保证开源仓库安全，同时让本地部署仍然可复现。
