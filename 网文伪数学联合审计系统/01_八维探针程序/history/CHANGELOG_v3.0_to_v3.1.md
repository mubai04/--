# CHANGELOG：v3.0 → v3.1

## 破坏性修改

1. 删除 `openai` Python SDK。
2. 删除 `OPENAI_API_KEY` 检查。
3. 删除模型参数、API缓存、重试、API结构化输出调用。
4. 删除 `analyze` 与原 `batch` 命令。
5. 新增 `prepare`：生成 Codex 任务目录。
6. 新增 `score`：读取 Codex 生成的 `extraction.json` 后本地计算。
7. 新增 `batch-score`：只批量计算已有提取文件。
8. 新增正文 SHA-256、任务编号和规则版本交叉校验。
9. 新增 JSON Schema 与提取模板。
10. 改为 Python 标准库实现，无第三方依赖。

## 评分修正

- v3.0：八维全 2 分时 activation=0.5，可能被判为低。
- v3.1：activation=0.5 明确判为中，与“2=合格”一致。

## 报告修正

- 删除“API缓存命中”“模型名”等字段。
- 新增 `api_called_by_script=false`。
- 新增提取端名称、规则版本、权重状态和阈值。
- 正贡献与负贡献分开筛选，不再把零值或正值误放进负贡献列表。

## 保留能力

- 八维向量化；
- 商业硬门；
- 证据覆盖率；
- JSON/Markdown报告；
- 修改前后对比；
- 人工标签权重拟合；
- 默认权重导出；
- 本地自检。
