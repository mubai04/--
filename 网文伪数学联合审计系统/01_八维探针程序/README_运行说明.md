# 八维伪线性探针 v3.2.1 CANDIDATE：运行说明

## 1. 当前运行架构

```text
小说文本
→ Python prepare：封装 task.json
→ Codex：读取任务并生成 extraction.json
→ Python score：校验、向量化、线性计算、门控、报告
```

关键边界：

```text
Codex 已经是模型执行端。
Python 脚本不会再次调用 OpenAI API。
脚本不需要 OPENAI_API_KEY。
脚本不需要 openai Python SDK。
```

该工具不读取模型隐藏层，不是真实线性探针。`activation` 只是内部线性激活值，不是爆款概率、签约率、留存率或收入预测。

## 2. 环境要求

```text
Python 3.11+
第三方 Python 依赖：无
网络：脚本不需要
API Key：脚本不需要
```

本地自检：

```powershell
python pseudo_linear_probe.py self-test
```

预期：

```text
SELF-TEST PASS
```


## 2.1 当前证据完整性规则

除八维数量覆盖率外，v3.2.1 新增两项约束：

```text
权重覆盖率不得低于 70%
因果代价、极速流转、章尾钩子、活人冲突任一缺失 → 证据不足
```

同一句原文可以辅助多个维度，但不得作为三个及以上高分维度的唯一正向证据。

## 3. 单章完整流程

### 第一步：准备任务

```powershell
python pseudo_linear_probe.py prepare `
  --input ".\samples\chapter_before.txt" `
  --input-type single_chapter `
  --metadata ".\metadata.example.json" `
  --output-dir ".\examples\before_task"
```

生成：

```text
examples/before_task/task.json
examples/before_task/CODEX_TASK.md
examples/before_task/extraction.template.json
examples/before_task/extraction.schema.json
```

### 第二步：让 Codex 执行特征提取

给 Codex 的指令：

```text
读取 examples/before_task/CODEX_TASK.md 与 task.json，
按 extraction.template.json 和 extraction.schema.json，
生成 examples/before_task/extraction.json。
不得修改任务编号、文本哈希、输入类型和规则版本。
生成后运行本地 score 命令。
```

Codex 在这一步使用其自身已有的模型/API运行环境。Python 不发起第二次模型请求。

### 第三步：本地计算

```powershell
python pseudo_linear_probe.py score `
  --task ".\examples\before_task\task.json" `
  --extraction ".\examples\before_task\extraction.json" `
  --output ".\reports\before.probe.json"
```

同时生成：

```text
reports/before.probe.json
reports/before.probe.md
```

## 4. 输入类型

```text
online_full       已上线整书
unpublished_full  未上线整书
first_three       前三章
single_chapter    单章
fragment          小说片段
```

输入类型决定允许外推的边界。片段、单章不得被脚本判成整书爆款。

## 5. 批量计算

每个任务目录内放置：

```text
task.json
extraction.json
```

然后运行：

```powershell
python pseudo_linear_probe.py batch-score `
  --root ".\examples" `
  --output-dir ".\reports\batch"
```

生成：

```text
reports/batch/probe_index.csv
reports/batch/probe_failures.json
```

批量命令只处理已经由 Codex 生成的 `extraction.json`，不会调用模型。

## 6. 修改前后对比

```powershell
python pseudo_linear_probe.py compare `
  --before ".\reports\before.probe.json" `
  --after ".\reports\after.probe.json" `
  --output ".\reports\before_after.compare.json" `
  --relation ".\examples\revision_relation.json"
```

默认要求以下口径一致：

```text
脚本版本
规则版本
输入类型
特征提取端名称
权重
偏置
等级阈值
```

差值只表示伪探针内部口径变化，不表示真实读者留存变化。

## 7. 重新拟合权重

人工给探针报告打二元标签：

```json
{"report":"reports/after.probe.json","label":1}
{"report":"reports/before.probe.json","label":0}
```

保存为 JSONL 后运行：

```powershell
python pseudo_linear_probe.py fit `
  --dataset ".\training_dataset.jsonl" `
  --output ".\weights.calibrated.json"
```

默认最低要求：总数至少 40，每类至少 10。该下限只阻止最明显的小样本伪拟合，不证明统计可靠。

## 8. 默认权重的真实状态

默认权重是人工工程初始值：

```text
status = uncalibrated
```

它们可以用于建立流水线、观察相对变化，但不能声称已经学习到市场规律。

等级阈值已修正：

```text
八维全部为 2 分、置信度 100%
→ activation = 0.5
→ 等级 = 中
```

这里的“2”仍保持“合格”语义。

## 9. 主要命令

```text
prepare               封装文本并生成 Codex 任务
score                 本地校验与计算
batch-score           批量计算已有 extraction.json
compare               对比两份报告
fit                   使用人工标签拟合权重
write-default-weights 导出默认权重
write-schema          导出 JSON Schema
self-test             纯本地验收
```

不存在：

```text
analyze API 调用
模型参数
OPENAI_API_KEY
API 缓存
网络重试
```

## 10. 失败处理

### extraction.json 与原文不匹配

脚本会核对：

```text
task_id
source_sha256
input_type
schema_version
rubric_version
```

任意一项不一致，直接失败，禁止把另一篇正文的提取结果误用于当前任务。

### 某维证据不足

必须写：

```json
"evidence_sufficient": false,
"score": null
```

脚本不会把证据不足当成 0 分。

### 覆盖率不足

默认八维有效维度少于 5 个、权重覆盖率低于70%，或关键轴缺失时：

```text
raw_level = 证据不足
```

### 商业门失败

对前三章和整书输入，卖点、情绪、主角发动机、最小兑现任一低于 2 分时，八维高分不得补偿。

## 11. 包内文件索引

```text
START_HERE.txt                         快速入口
pseudo_linear_probe.py                 本地计算脚本
爆款判断_八维伪线性探针_v3.2.1_CANDIDATE.md  当前主规范
TEST_EVIDENCE_v3.2.1.md                当前测试证据
验收报告_v3.2.1.md                      当前验收结论
INTERFACE_网文伪数学公式总表_八维探针_v1.0.md  联合接口规范
samples/                               修改前后示例正文
examples/                              可复现任务、提取和修订关系
reports/                               示例评分、批量与对比报告
history/                               历史变更与旧验收材料
```

当前状态以 `PACKAGE_STATUS.json` 为准。历史文件不得覆盖当前版本判断。

