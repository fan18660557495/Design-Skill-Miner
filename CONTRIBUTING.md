# Contributing

感谢你改进 `design-skill-miner`。

这个项目目前优先关注三类贡献：

- 规则提炼质量：过滤、聚类、审校、草稿生成
- 本地使用体验：CLI、Web UI、启动脚本
- 开源可维护性：测试、文档、配置、安全边界

## 开始之前

1. Fork 仓库并创建分支。
2. 安装本地开发环境：

```bash
python3 -m pip install -e .
```

3. 复制示例配置：

```bash
cp .design-skill-miner.toml.example .design-skill-miner.toml
```

4. 只在本地配置 API 环境变量，不要把真实密钥写入仓库。

## 开发约定

- Python 版本：`>= 3.11`
- 优先保持标准库依赖，避免引入重型第三方包
- 新增能力时，优先补最小测试
- 文档、示例和代码行为保持一致
- 不要提交本地会话数据、真实项目路径、真实密钥

## 提交前检查

运行：

```bash
python3 -m unittest discover -s tests
node --check web/app.js
```

如果你改了 Web 接口，建议再手动跑一次本地服务：

```bash
./run-local.sh serve --host 127.0.0.1 --port 8765
```

## 目录约定

- `src/design_skill_miner/`：核心逻辑
- `web/`：前端资源
- `tests/`：回归测试
- `docs/`：架构和补充说明

## Pull Request 建议

PR 描述最好包含：

- 改动动机
- 主要行为变化
- 测试结果
- 是否涉及配置变更
- 是否影响输出结构或草稿格式

## 安全

如果改动涉及配置、环境变量或外部模型调用，请同时更新 [SECURITY.md](./SECURITY.md) 或至少确认没有引入新的泄露面。
