---
name: develop-ai-tool
description: 将业务流程、咨询方法、重复任务或个人经验从零开发为 Prompt、Project Instructions、Skill、Plugin 或 MCP，并编排研究、Excel 指标字典、构建、评测和候选包。当用户提出把一套流程做成 AI 工具、从零开发 Skill/Plugin、方法论产品化、需要完整 Skill/Plugin 开发流程，或尚未确定工具形态时使用。已有设计和指标且只要求进入编码、已有产物且只要求评测、仅解释概念、安装已有工具或修改普通 Prompt 时不要触发，应让位给对应阶段 Skill。
version: 0.1.2
title: 开发 AI 工具
agent_created: true
tags: [ai-tool-factory, skill-development, stage-gate, bovey]
trigger:
  - 把业务流程做成 AI 工具
  - 从零开发 Skill 或 Plugin
  - 方法论产品化
  - 开发 AI 工具
  - 博维 AI 工具工厂
disable: false
author: 博维管理咨询 (ChatGPT export, adapted to WorkBuddy)
---

# 开发 AI 工具

## 目标

把用户的业务任务推进到一个可追溯、可测试、可交接的 AI 工具产品。总控遵循 S0-S11，不把“生成了文件”当作“已经可用”。

## 启动时读取

1. 读取 `references/stage-gates.md`，建立阶段和交付物。
2. 读取 `references/artifact-decision.md`，选择最小充分工具形态。
3. 若需要引用外部或内部案例，再读取 `references/case-patterns.md`。
4. 如果工作区已存在，先读取 `design.md`、`plan.md` 和 `stage-status.json`，从当前闸门继续，不重复已完成工作。

## 工作流

### 1. S0-S1：立项与问题

先确认五项最小信息：用户、任务、输入、输出、数据/权限边界。能从上下文可靠取得时直接使用；缺少会改变产品形态或授权边界的信息时一次问完。

若需要新建标准工作区，运行：

```powershell
python ../bovey-ai-tool-factory/scripts/init_product.py <product-id> --output <parent> --artifact-type auto --owner "<owner>"
```

不要覆盖已存在的同名目录。先用 `--dry-run` 查看计划文件。

### 2. S2-S4：研究与指标

转入 `research-ai-tool`：

- 搜集理论、标准、官方规范和方法论；
- 调研用户自有工具、官方工具和 GitHub 同类项目；
- 形成信源台账、同类工具矩阵；
- 将指标写入 Excel 模板，字段至少包含定义、公式、阈值、证据、责任人和闸门。

研究未完成时不得进入正式架构定稿；低成本原型须标明“探索性”。

### 3. S5-S7：基线、架构与 MVP

转入 `build-ai-tool`：

- 先建立无新工具的基线和正向、负向、边界用例；
- 按最小充分原则确定工具形态；
- 使用目标平台提供的官方脚手架；
- 将长知识放 `references/`，确定性操作放 `scripts/`，交付模板放 `assets/`；
- 运行新增脚本，保存真实输出。

### 4. S8-S11：评测、发布与迭代

转入 `evaluate-ai-tool`：

- 先静态检查，再做功能和行为测试；
- 做有/无 Skill 或新/旧版本 A/B；
- 单独检查安全红线，不用平均分抵消；
- 真实打开或解析生成物；
- 只有在行为闸门通过后才打包；
- 记录宿主运行是否真实验证。

## 交付状态

交付时分开报告：

- 已实测：脚本、静态校验、冒烟、行为用例等实际运行项；
- 待验证：目标宿主的真实触发、多人试点、外部平台安装；
- 未执行：因权限或用户未授权而没有做的安装、发布、发送。

## 硬边界

- 不读取或复用未授权的客户原始资料。
- 不把论坛帖子当作可靠结论；只用于发现线索和失败模式。
- 不自动安装到个人或组织环境，不自动向 GitHub/Marketplace 发布。
- 不在输出中写入密钥、Token、真实客户身份或用户专属绝对路径。
- 不声称内部评分是外部框架的官方评分。
- 不把静态结构通过等同于宿主运行通过。

## 完成标准

至少交付：产品设计、实施计划、研究简报、信源台账、Excel 指标字典、评测集、源码、校验报告、发布检查表；若打包，还需版本号和 SHA256。
