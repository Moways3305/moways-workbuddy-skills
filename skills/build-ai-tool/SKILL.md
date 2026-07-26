---
name: build-ai-tool
description: 在已有 design、研究、Excel 指标字典或 evals 的 AI 工具项目中，选择最终架构并用官方脚手架构建可测试的 Skill、Plugin 或 MCP MVP。当用户明确说“设计和指标已经完成，现在进入构建”、要求把既有设计落成 SKILL.md、拆分 references/scripts/assets 或实现既定 Plugin MVP 时使用。用户要求从零走完整开发流程时让位给 develop-ai-tool；缺少研究与验收口径、只修改普通业务代码时不要触发。
version: 0.1.2
title: 构建 AI 工具
agent_created: true
tags: [ai-tool-factory, build, mvp, bovey]
trigger:
  - 构建 Skill 或 Plugin
  - 落成 SKILL.md
  - AI 工具 MVP
disable: false
author: 博维管理咨询 (ChatGPT export, adapted to WorkBuddy)
---

# 构建 AI 工具

## 启动时读取

1. 读取 `references/build-patterns.md`。
2. 读取 `design.md`、研究简报、Excel 指标字典和 `evals/evals.json`。
3. 若工具形态未定，读取 `../develop-ai-tool/references/artifact-decision.md`。

## S5：先建基线和评测集

开发前记录：

- 不使用新工具时的完成率、耗时、错误和缺失字段；
- 至少 5 个正向触发、5 个负向触发、3 个边界场景；
- 关键输出的可机器检查断言；
- 安全红线和拒绝或降级行为。

用例应来自真实任务类型但必须脱敏。不要只写“结果应该很好”。

## S6：架构

选择最小充分形态：

- 单次、短、无复用：Prompt；
- 固定项目规则：Project Instructions/AGENTS.md；
- 可复用知识或工作流：Skill；
- 多个相关 Skill、脚本、模板或连接能力：Plugin；
- 必须访问外部系统或实时数据：MCP，且单列认证与权限。

把决策理由写进 `design.md`，包括未选方案。

## S7：MVP

### Skill

- 使用平台提供的 Skill Creator 或官方脚手架；
- `name` 使用小写连字符，目录同名；
- `description` 同时说明做什么、何时触发、何时不触发；
- `SKILL.md` 只保留核心流程；
- 长知识进入 `references/`；
- 确定性、重复性操作进入 `scripts/`；
- 模板和非上下文资源进入 `assets/`。

### Plugin

- 使用 Plugin Creator 或官方脚手架；
- 根目录和 manifest `name` 一致；
- 一个 Plugin 只承载同一类用户任务；
- manifest 明确版本、描述、Skills 和界面元数据；
- 不在未授权情况下写 Marketplace 或执行安装。

### 脚本

- 默认非破坏性，已有目标拒绝覆盖；
- 支持 `--help`，涉及写入时尽量支持 `--dry-run`；
- 返回稳定退出码；
- 不硬编码密钥、客户信息和个人绝对路径；
- 每个新增脚本必须实际运行并加入测试。

## 构建检查

完成后立即：

1. 解析 JSON/YAML；
2. 运行 Skill 和 Plugin 官方校验器；
3. 运行脚本单元测试；
4. 用临时目录走一次初始化或生成冒烟；
5. 检查所有引用文件真实存在；
6. 将失败转成回归用例。

## 交接

向 `evaluate-ai-tool` 交付源码路径和版本、架构决策、基线与评测集、已运行命令及结果、已知限制，以及真实宿主是否验证。
