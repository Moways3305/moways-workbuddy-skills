# 可复用案例模式

## 官方创建器

- 【实证】OpenAI 的 Skill Creator 将创建过程拆为示例、资源规划、初始化、编辑、校验和真实使用迭代，并要求新增脚本实际运行。[source: bundled OpenAI skill-creator, inspected 2026-07-26]
- 【实证】OpenAI 的 Plugin Creator 使用 manifest 组合 Skills、scripts、assets、MCP 或 apps，并提供脚手架与校验器。[source: https://developers.openai.com/plugins/concepts/plugins]

## GitHub 工程模式

- 【实证】Agent Skills 规范采用 `SKILL.md` 与可选 `scripts/`、`references/`、`assets/`，通过名称和描述完成发现。[source: https://agentskills.io/specification]
- 【实证】Superpowers 项目强调在实现前形成规格与计划，并使用测试驱动的 RED-GREEN-REFACTOR。[source: https://github.com/obra/superpowers]
- 【实证】Promptfoo 支持对不同 Skill 或版本运行成组用例，比较输出并形成回归评测。[source: https://www.promptfoo.dev/docs/guides/test-agent-skills/]
- 【实证】Microsoft Waza 将 agent 测试组织为 trials 和可重复验证，适合进入 CI。[source: https://github.com/microsoft/waza]
- 【实证】NVIDIA Skills 展示了 Skill Card、签名、基准与目录化发布的工程思路。[source: https://github.com/NVIDIA/skills]

## 博维内部案例

- 【实证】`bovey-consulting-memory` 采用多个窄职责 Skill、共享模板、触发用例与插件清单，说明内部工作流适合“统一安装、分别触发”。[source: local installed package inspection, 2026-07-26]
- 【实证】`industry-research` 将主流程、详细 references、确定性 scripts 与 MCP 配置分层，说明长方法不应全部塞进 `SKILL.md`。[source: local installed package inspection, 2026-07-26]
- 【实证】`consulting-deck-tools` 让多个 Skill 共享运行时与测试，说明同类交付能力可以在 Plugin 内复用基础设施。[source: local installed package inspection, 2026-07-26]
- 【实证】Luban 的定位是对已有产物做结构、行为、真实交付物和安全复核，不替代从零脚手架。[source: local installed skill inspection, 2026-07-26]

这些模式用于产品设计，不代表上述工具已在当前宿主完成实时触发验证。
