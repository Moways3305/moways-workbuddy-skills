# Changelog

## 0.1.0 - 2026-07-26

- 建仓：博维 WorkBuddy 版 Agent Skill 源仓库，与 ChatGPT 版（bovey-agent-skills）分仓治理。
- 首批收录「博维 AI 工具工厂」套件 v0.1.2（自 ChatGPT codex-plugin 适配）：
  - develop-ai-tool / research-ai-tool / build-ai-tool / evaluate-ai-tool 四个可发现技能；
  - bovey-ai-tool-factory 共享资源包（工厂脚本、Excel 指标字典模板、示范件、测试）。
- 适配内容：frontmatter 扩展（version/title/tags/trigger 等），共享资源路径重定向为 `../bovey-ai-tool-factory/`。
- 安全审计 P2；示范件验证 19/19 PASS；工厂自检 PASS；单元测试 21 passed。
