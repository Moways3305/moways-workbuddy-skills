# 博维 WorkBuddy Skills

博维管理咨询内部使用的 **WorkBuddy 版** Agent Skill 源仓库。GitHub 负责版本、审批、发布和更新；WorkBuddy 工作区负责实际部署使用。

> 与 ChatGPT 版分仓治理：ChatGPT/Codex 版技能见 [Moways3305/bovey-agent-skills](https://github.com/Moways3305/bovey-agent-skills)。同一能力在两个平台各有实现时，分别在本仓与彼仓维护，避免混淆。

## 已收录 Skill

| Skill | 用途 | 当前版本 |
|---|---|---|
| develop-ai-tool | 总控：把业务流程/咨询方法编排为可评测、可打包的 AI 工具（S0-S11） | 0.1.2 |
| research-ai-tool | 理论方法、同类产品、GitHub 工具研究与 Excel 指标字典 | 0.1.2 |
| build-ai-tool | 按最小充分原则构建 Skill/Plugin/MCP MVP | 0.1.2 |
| evaluate-ai-tool | 静态/行为/安全评测、独立 Judge、候选打包与发布准备 | 0.1.2 |

共享资源仓库：`skills/bovey-ai-tool-factory/`（工厂脚本、Excel 指标字典模板、示范件与测试）。它本身不是 Skill，被上述 4 个技能以 `../bovey-ai-tool-factory/` 相对路径引用，安装时必须一并拷贝。

## 安装到 WorkBuddy

将 5 个目录全部复制到 WorkBuddy 用户技能目录（Windows 示例）：

```powershell
git clone https://github.com/Moways3305/bovey-workbuddy-skills.git
Copy-Item -Recurse bovey-workbuddy-skills\skills\* "$env:USERPROFILE\.workbuddy\skills\"
```

macOS / Linux：

```bash
git clone https://github.com/Moways3305/bovey-workbuddy-skills.git
cp -r bovey-workbuddy-skills/skills/* ~/.workbuddy/skills/
```

复制完成后**新开 WorkBuddy 会话**即可被自动发现。验证触发：

- 「把我的业务流程做成一个可评测的 AI 工具」→ develop-ai-tool
- 「为这个 AI 工具做 GitHub 同类工具对标和指标字典」→ research-ai-tool
- 「设计和指标已完成，进入构建」→ build-ai-tool
- 「对这个 Skill 做行为评测和发布前验收」→ evaluate-ai-tool

## 目录约定

```
skills/<skill-name>/        # 每个可发现技能一个目录，含 SKILL.md
skills/bovey-ai-tool-factory/  # 共享资源（scripts/assets/examples/evals/tests）
catalog/skills.json         # 收录索引（release 版本 + 各技能 sourceVersion）
scripts/validate_skills.py  # 结构校验（共享包目录走白名单）
CHANGELOG.md                # 变更记录
```

## 边界

- 本仓技能默认不自动安装、不自动发布到 SkillHub / 企业后台；对外发布单独走审批。
- 不含客户原始资料；示例均为虚构数据（已通过静态安全审计，P2）。
