# 构建模式

## 渐进披露

元数据负责被发现，`SKILL.md` 负责核心流程，`references/` 按需加载，`scripts/` 执行确定性动作，`assets/` 被复制进交付物。不要让主文件承载所有背景资料。

## 目录最小集

Skill：

```text
skill-name/
├── SKILL.md
├── agents/openai.yaml
├── references/
├── scripts/
└── assets/
```

只创建真实需要的目录。

Plugin：

```text
plugin-name/
├── .codex-plugin/plugin.json
├── skills/
├── scripts/
├── assets/
└── tests/
```

## 描述测试

`description` 包含具体能力、5-15 个自然语言触发表达、至少一个不触发边界。避免“通用、灵活、强大”等无法支持发现的词。

## 脚本接口

- 使用参数而不是修改源码；
- 目标已存在时默认拒绝；
- 先校验输入再写文件；
- 错误写 stderr，成功写 stdout；
- 成功退出码 0，可预期输入错误使用非 0；
- 生成物可再次解析验证。
