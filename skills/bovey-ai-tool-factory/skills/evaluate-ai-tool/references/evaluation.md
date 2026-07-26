# AI 工具评测方法

## 三层验证

1. 静态：结构、schema、引用、脚本、敏感信息。
2. 行为：触发、输出、边界、A/B、重复试验。
3. 宿主：目标 ChatGPT/Codex 环境真实发现、调用和产物。

任何层都不能冒充后一层。

## 最小用例集

- 正向触发不少于 5 个；
- 负向触发不少于 5 个；
- 边界场景不少于 3 个；
- 每个关键输出至少一个命名断言；
- 高波动用例至少重复 3 次；
- 至少一个真实文件或交付物检查。

## A/B

保持用户输入、附件、模型和环境尽量一致，只改变是否使用 Skill 或版本。比较任务成功、字段完整、事实追溯、人工修改和耗时。不能控制的变量要记录。

## 独立 Judge

Judge 只获得需求、评测标准和匿名化输出，不获得实现者的自我解释。Judge 先检查 P0 红线，再评分；报告失败证据，不改源码。

## 参考依据

- 【实证】Agent Skills 官方评测指南区分触发、功能输出和性能，并建议将真实失败加入回归集。[source: https://agentskills.io/skill-creation/evaluating-skills]
- 【实证】Promptfoo 的 Agent Skills 指南支持版本对比和批量评测。[source: https://www.promptfoo.dev/docs/guides/test-agent-skills/]
- 【实证】Waza 提供 trial 驱动的可重复 agent 测试模式。[source: https://github.com/microsoft/waza]
