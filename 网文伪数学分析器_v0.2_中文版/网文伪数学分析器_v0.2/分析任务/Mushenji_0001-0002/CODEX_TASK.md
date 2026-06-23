# Codex 分析任务（方法版本 0.2.0）

读取：

- `task.json`
- 项目根目录 `schemas/extraction.schema.json`
- 项目根目录 `文档/编码手册_v0.2.md`
- 项目根目录 `配置/metric_registry.json`
- 项目根目录 `文档/反刷分协议.md`

生成当前目录下的 `extraction.json`。

硬规则：

1. 不修改 `task_id` 与 `source_sha256`；
2. 每条证据必须填写 `file`、`quote`、`start`、`end`，并与对应章节原文逐字一致；
3. 无证据时输出 `UNKNOWN`、`NA` 或其他缺失状态，不得猜测；
4. 事实指标保留合法的分子、分母、样本量；分子不得为负，不得大于分母；
5. 人工评分使用 0—4 区间并说明判断；
6. 同一根病灶使用同一 `finding_id`，禁止重复处罚；
7. 同一引文默认最多支持两个主判断；确需复用必须写 `reuse_justification`，且最多四项；
8. 完成六项反刷分检查；
9. 不输出作者身份概率、商业成功率、平台留存率或版权结论；
10. 写完后先运行本地 `score`，Schema 或证据校验失败必须修正。
