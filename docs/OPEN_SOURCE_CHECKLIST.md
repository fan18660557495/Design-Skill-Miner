# 开源发布检查清单（中文）

这份清单用于把 `design-skill-miner` 发布到公开仓库前的最后检查。

目标只有两个：

- 不泄露敏感信息
- 开源读者能直接跑起来并看懂

## 1. 安全检查（必须）

执行前先确认当前目录是仓库根目录，然后运行：

```bash
git status
rg -n "sk-[A-Za-z0-9]{10,}" .
```

重点确认以下内容没有进入暂存区：

- `.design-skill-miner.toml`
- `.design-skill-miner/`
- `.env` / `.env.*`
- 任何真实会话导出
- 任何带用户名、公司路径、客户名的样本

## 2. 可运行检查（必须）

```bash
python3 -m compileall src/design_skill_miner
node --check web/app.js
```

建议再跑一次本地服务：

```bash
./run-local.sh serve --host 127.0.0.1 --port 8765
```

并手动走一遍：

1. 选择项目
2. 启动智能体
3. 查看“运行过程”
4. 打开草稿并编辑
5. 点击保存，确认提示“已写入记忆”

## 3. 文档一致性检查（必须）

每次发布前确认以下文档内容一致：

- `README.md`：用户视角说明、快速开始、输出结构
- `docs/ARCHITECTURE.md`：为什么它是 Agent（目标/策略/记忆/闸门）
- `docs/HOW-TO-BUILD-THIS-AGENT.md`：如何复刻这类 Agent
- `CONTRIBUTING.md`：贡献流程和提交前检查
- `SECURITY.md`：密钥与数据安全边界
- `CHANGELOG.md`：这次版本改了什么

## 4. 提交与推送（建议流程）

```bash
git add .
git commit -m "docs: improve open-source readiness and release checklist"
git push origin main
```

如果你是首次公开，建议额外做两件事：

- 在仓库主页简介里写清“本地运行、默认不上传会话”
- 给 README 加上“这是草稿生成助手，不是自动定稿器”的定位
