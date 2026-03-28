# Security

`design-skill-miner` 设计为本地运行工具，但仍然有几类常见安全风险需要明确约束。

## 不要提交的内容

以下内容不应进入 Git 仓库：

- `.design-skill-miner.toml`
- `.env` 和任何本地环境变量文件
- 真实 API Key
- 真实用户会话导出
- 带有公司路径、用户名、客户信息的测试样本
- 运行时生成目录，例如 `agent-out/`、`skill-draft/`

仓库已通过 `.gitignore` 忽略常见本地配置和输出目录，但在提交前仍建议手动检查一次 `git status`。

## 推荐的密钥使用方式

- 把密钥放在环境变量里，例如 `MOONSHOT_API_KEY`
- 在 `.design-skill-miner.toml` 里只写环境变量名，不写密钥值
- 开源前执行一次仓库扫描，例如：

```bash
rg -n "sk-[A-Za-z0-9]{10,}" .
```

## 配置文件原则

公开仓库中应只保留：

- `.design-skill-miner.toml.example`

不要提交：

- `.design-skill-miner.toml`

## Web 使用注意事项

Web UI 是本地服务，默认只监听 `127.0.0.1`。除非你明确知道风险，不要把它直接暴露到公网。

## 漏洞报告

如果你发现了会导致密钥泄露、路径暴露、任意文件读取或错误发布的安全问题，请不要先公开开 Issue。优先通过私下渠道联系维护者。
