# Codex 固定执行指令

## 目标

把小说文本提取成八维结构化证据。Codex 是唯一模型执行端；本地 Python 不调用 API。

## 标准流程

```text
1. 运行 prepare 生成任务目录。
2. 读取任务目录内 CODEX_TASK.md、task.json、extraction.template.json、extraction.schema.json。
3. 只依据 task.json 中的正文与元数据填写 extraction.json。
4. 不输出综合总分，不输出爆款概率、签约率、留存率、收入。
5. 运行 score，让 Python 完成确定性计算。
6. 检查 probe.report.json 与 probe.report.md 是否生成。
```

## 可直接交给 Codex 的命令

```text
阅读当前目录的 README_运行说明.md 与爆款判断_八维伪线性探针_v3.2.1_CANDIDATE.md。
对指定小说文件运行 pseudo_linear_probe.py prepare。
随后读取生成的 CODEX_TASK.md 与 task.json，严格按 extraction.schema.json 生成 extraction.json。
不得修改 task_id、source_sha256、input_type、schema_version、rubric_version。
同一句原文不得作为三个及以上高分维度的唯一正向证据。
最后运行 pseudo_linear_probe.py score。
Python 脚本不得接入、调用或配置任何模型 API。
```
