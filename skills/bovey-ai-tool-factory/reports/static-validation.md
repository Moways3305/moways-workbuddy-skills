RELEASE_GATE: PASS
EVIDENCE_TYPE: static_validation
PRODUCT_VERSION: 0.1.2
EVALUATED_AT: 2026-07-26T17:25:00+08:00

# v0.1.2 静态与确定性校验

## 结论

内部候选包所需的静态与确定性检查通过；公开发布条件尚未满足。

## 2026-07-26 实际运行结果

- 21 项自动测试全部通过。
- 4 个 Skill 分别通过 OpenAI Skill Creator 的官方 quick validator。
- Plugin 通过 OpenAI Plugin Creator 的官方 validator。
- 工厂校验器以 `--run-official` 模式检查结果为 PASS，错误 0、警告 0。
- 初始化→项目校验→候选打包链路已在临时目录运行。
- 已验证：已有目标拒绝覆盖、初始化失败不留半成品、JSON 特殊字符转义、阶段状态非法值阻断、5/5/3 用例不足阻断、symlink 和根外路径阻断、旧证据在源码变化后失效、错配类型和过期版本报告阻断、无效或无时区评估时间阻断、公开发布缺 live 证据时阻断。
- 可复现示范件连续三次通过 19/19 项断言，覆盖文件完整性、阶段证据锚点、5/5/3 用例合同、基线 5/10 重算、结果卡状态、证据等级、发布边界和隐私路径/凭据特征。
- Luban 结构尺由 PASS 6 / WARN 6 / FAIL 2 改善为 PASS 7 / WARN 6 / FAIL 1；`examples/` 缺失已闭合，根 `README.md` 仍未补。

## Excel 检查

- 7 张工作表均可由 `openpyxl` 解析。
- 7 张工作表均设置 Excel Table。
- `01流程阶段` 标题为 S0-S11 共 12 阶段。
- `04测试用例库` 含 5 个正向、5 个近似负向、3 个边界和 1 个高风险样例，共 14 条。

## 证据边界

- 本报告证明静态结构、确定性脚本和本机 dry-run，不证明 ChatGPT/Codex 真实语义触发。
- 未安装到个人或组织环境。
- 未执行公开 Marketplace、GitHub 发布或专业供应链安全扫描。
