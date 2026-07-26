---
name: research-ai-tool
description: 为已经立项或准备升级的 Skill、Plugin、Agent Workflow 或 MCP 单独完成理论方法、同类产品、GitHub 工具、信源台账、竞品矩阵和 Excel 指标字典。当用户明确只要求先研究再开发、GitHub 工具对标、设计 AI 工具评测指标、形成 Excel 指标字典或建立 Stage-Gate 时使用。用户要求从零完成整个工具时让位给 develop-ai-tool；一般行业研究、市场规模和非 AI 工具竞品分析不要触发。
version: 0.1.2
title: 研究 AI 工具
agent_created: true
tags: [ai-tool-factory, research, metrics-dictionary, bovey]
trigger:
  - AI 工具研究
  - GitHub 工具对标
  - Excel 指标字典
  - Stage-Gate
disable: false
author: 博维管理咨询 (ChatGPT export, adapted to WorkBuddy)
---

# 研究 AI 工具

## 启动时读取

1. 读取 `references/evidence-and-metrics.md`。
2. 若要比较成熟开发范式，读取 `../develop-ai-tool/references/case-patterns.md`。
3. 读取当前项目的 `design.md`；不存在时先建立问题定义，不直接堆砌资料。

## S1：研究问题

将需求改写为可验证问题：

- 谁在什么场景完成什么任务？
- 当前方案在哪些环节失败？
- 新工具改变哪个决策或动作？
- 哪些输出是必须字段？
- 哪些风险一旦发生就必须阻断？

产出问题树，并区分事实、假设和待验证项。

## S2：理论与方法

优先使用平台官方文档、标准、原始论文和源代码，其次使用维护者资料和高质量工程文章。GitHub issue、论坛和 X 讨论只作为线索或失败样本。

外部信息可能变化时必须联网核验。每个产品设计建议写明：

- 灵感来源；
- 能解决的问题；
- 预期收益；
- 落地成本；
- 已实测或待验证。

## S3：同类工具矩阵

至少覆盖用户已有或博维自研工具、平台官方工具、GitHub 代表性开源实现。比较用户任务、触发入口、资源结构、评测方法、权限边界、发布回滚、可复用设计和不适用条件。

不按 Star 数直接判断质量；检查最近维护状态、测试、文档、issue 和真实可运行证据。

## S4：Excel 指标字典

从插件根目录复制 `../bovey-ai-tool-factory/assets/Skill开发指标字典与Stage-Gate模板.xlsx`。

维护七张表：`00总览`、`01流程阶段`、`02指标字典`、`03竞品工具矩阵`、`04测试用例库`、`05评测记录`、`06信源台账`。

每个指标必须有：

- 指标 ID、名称、目的、阶段；
- 定义、计算方法、分母和单位；
- 数据源、采集方式和责任人；
- 阈值、红线和判定逻辑；
- 适用范围、排除项和证据状态。

安全红线作为硬闸门，不参与均分。

## 交付闸门

- 关键设计结论有可追溯来源或明确标为内部假设；
- 同类工具矩阵包含自研、官方、开源三类；
- Excel 指标可直接用于后续测试，不是只有名称的清单；
- 研究局限和未核实项已列出；
- 数据和案例已脱敏。
