# XC-UE AR-1 验收可信性恢复计划书

**版本：** v2.2  
**状态：** CANDIDATE_FOR_FREEZE  
**日期：** 2026-06-25  
**适用对象：** XC-UE 个人本地小说创作工程  
**执行者：** Cursor / Codex  
**验收者：** XC-UE 个人创作工程业务能力总审计官  
**证据基线：** `XC-UE(8).zip` 的实际文件、代码、配置、Schema、测试与独立运行结果  
**替代关系：** 本文件替代 AR-1 v1.1、v1.1 单点修正版、v1.2、v2.0 和 v2.1。旧版不得继续作为执行依据。  
**冻结条件：** 本文件须再次独立验收；通过后方可改为 `FROZEN / APPROVED_FOR_EXECUTION`。

---

# 0. v2.2 修订结论

v2.1 已经解决 v2.0 的七个主体阻断，但独立验收仍发现六个“唯一真源未完全闭合”的缺口。v2.2 对其作定点修正：

1. 根 `AGENTS.override.md` 会替换同目录 `AGENTS.md`  
   → override 必须由验收者从当前根 `AGENTS.md` 完整复制生成，再追加 AR-1 覆盖区；不得手工只写一份缩减版。

2. `REVIEW_REQUIRED` 与 `REVIEW_REQUIRED` 双枚举  
   → 新产物唯一机器状态固定为 `REVIEW_REQUIRED`；旧值仅在读取边界兼容并立即规范化。

3. 复验正向控制的“明确通过”仍可由 Codex自行解释  
   → 冻结完整的 `VALIDATED_GATE_CONTRACT` Schema 谓词；生产 L1 在 AR-1 中不得生成该正例，正例仅用于验证复验器不是恒 false。

4. 输入资格报告只有哈希，没有固定报告真源  
   → 固定报告路径、Schema、一次写入、不可覆盖、失效条件与下游校验方式。

5. 血缘中的 `source` 与 `rules` 对象含糊  
   → 拆分正式章节、输入快照、当前阶段输入；规则使用 `rule_artifacts[]` 与规范化集合哈希。

6. 历史 READY 的失效可能要求篡改历史文件  
   → 历史产物保持只读；新增运行时必读的撤销索引与 evaluator 最低版本闸门。

v2.2 不扩展 AR-1 的阶段目标，不新增自动小说生成能力。

---

# 1. 阶段性质

## 1.1 阶段名称

**AR-1：验收可信性恢复**

## 1.2 阶段唯一目标

恢复 XC-UE 的最低控制可信性：

- 无效输入不能继续进入 L1、L2、L3 或 L3_PATCH；
- 输入身份、正文哈希和规则版本必须沿链路保持一致；
- 局部词面信号不能覆盖整体拒绝；
- 复验通过与采纳启用必须严格分离；
- L2-01 不得再以固定故事、重复填充或项目特判伪装通用修复；
- Codex 不能通过修改测试、路由、状态、输入样本或辅助文件制造表面通过；
- AR-1 期间正式正文不可写。

## 1.3 本阶段不建设

- 通用小说语义理解；
- 自动生成合格修复正文；
- 文风、角色、设定、市场体验成熟修复器；
- 多章连续创作；
- 自动发布；
- 商业部署、包化和多人协作；
- 对所有低质或无意义文本的完备识别。

AR-1 通过只代表控制链恢复最低可信度。

---

# 2. 已证实问题

## P0-1：复验结果被局部信号覆盖

候选被 L1-00 判退、总复验拒绝后，仍可能因 L1-01 局部信号或 L2-01 路由消失进入 `READY_FOR_ACCEPTANCE`。

## P0-2：无效正文继续进入下游

极短占位、未完成或状态不明正文仍能生成 L2、L3 任务。

## P0-3：L2-01 以固定故事和重复填充伪装修复

现有代码包含固定人物、故事、项目、章节、重复 60 次和错误自动执行资格。

## P0-4：词面命中被赋予小说业务裁决权

关键词出现被用于产生结构成立、读者投入或发布相关正向信号，但没有业务有效性证据。

---

# 3. Codex 执行风险模型

本计划默认 Codex 会优先满足显式可见目标，并选择最低成本实现。没有写入验收的系统性质不会自动获得保护。

每个原子任务必须同时固定：

1. **真实目标效果**；
2. **允许修改的精确文件**；
3. **必须保持不变的性质**；
4. **从外部输入输出验证的黑盒结果**。

只达到某个表面指标，不构成完成。

## 3.1 对等绕过原则

即使实现形式改变，只要外部效果与旧错误等价，仍判定失败。例如：

- 重复 60 次改为 59 次；
- 固定故事从 Python 移到 JSON 或 Markdown；
- `TP-001` 改为默认参数隐式注入；
- `READY_FOR_ACCEPTANCE` 改名但保留相同写回权限；
- 删除失败项而不是修正判断；
- 修改测试样本使问题不再出现；
- 改路由使错误模块不再收到输入；
- 吞掉异常后返回“完成”；
- 新增无人读取的配置文件并声称开关已关闭。

---

# 4. 人工前置动作：构建完整 Codex 指令覆盖

该动作只在 v2.2 计划通过独立验收、生成 FROZEN 副本之后执行。由用户或验收者完成，不能交给负责业务代码修改的 Codex自行完成。

## 4.1 为什么不能只写缩减版 override

根目录存在 `AGENTS.override.md` 时，同目录的 `AGENTS.md` 不再作为该目录的活动指令文件。

因此，AR-1 的 override 不能只写新增限制。它必须完整保留根 `AGENTS.md` 中仍有效的规则，再追加 AR-1 覆盖条款。

## 4.2 固定生成方式

不得手工重新概括根规则。必须由验收者使用确定性脚本生成：

1. 读取当前根 `AGENTS.md` 的 UTF-8 文本；
2. 原文完整复制到根 `AGENTS.override.md`；
3. 在末尾追加一个唯一的 `# AR-1 临时覆盖` 区块；
4. 记录基础文件哈希、追加区块哈希和最终 override 哈希；
5. 若 `AGENTS.md` 不是有效 UTF-8、为空或读取失败，则停止。

生成后，`AGENTS.override.md` 的前缀内容必须与标准化换行后的根 `AGENTS.md` 完全一致。

## 4.3 固定追加区块

```markdown
# AR-1 临时覆盖

- 当前唯一执行基线：<已冻结的 v2.2 计划文件名及 SHA-256>。
- 旧 P0 任务单、旧 AR-1 版本、旧 B2 完成声明和旧 READY_FOR_ACCEPTANCE 产物暂停作为执行依据。
- AR-1 期间 patch execution、acceptance、formal text write 全部关闭。
- 根 AGENTS.md 中允许旧 B2 在条件满足后写回正式正文的条款，在 AR-1 期间被本区块明确覆盖。
- 每次只执行一个经批准的 AR-1 原子任务。
- 只能修改原子任务白名单中的文件。
- 不得通过修改测试、路由、输入样本、状态含义、Schema 断言或验收器制造通过。
- 发现白名单不足或规格冲突时必须停止并报告 BLOCKED_SCOPE_CHANGE_REQUIRED。
- Codex 无权写入 AR1_ACCEPTED、FROZEN 或 APPROVED_FOR_EXECUTION。
```

`<已冻结的 v2.2 计划文件名及 SHA-256>` 必须在计划验收通过、FROZEN 文件实际生成后填写。候选阶段不得伪造该值。

## 4.4 指令文件大小与完整性

生成脚本必须检查：

- `AGENTS.override.md` 非空；
- 最终内容包含根 `AGENTS.md` 的全部有效文本；
- 最终内容包含唯一一个 AR-1 临时覆盖区块；
- 文件大小未超过当前 Codex 项目指令大小上限；
- 最终文件 SHA-256 已记录。

若超出限制，不得删减根规则；必须停止并提交指令拆分方案。

## 4.5 激活和验证

生成 override 后必须：

1. 关闭旧 Codex 线程或 CLI 运行；
2. 从仓库根目录启动全新会话；
3. 要求 Codex列出活动指令来源和当前约束；
4. 保存 TUI 日志或 session JSONL；
5. 验证活动项目级文件是根 `AGENTS.override.md`；
6. 验证输出同时包含原根规则和 AR-1 覆盖条款；
7. 若仍出现旧 B2 写回许可作为当前有效规则，立即停止。

仅口头询问“你知道规则吗”不构成指令链验收。

---

# 5. 总体执行纪律

## 5.1 单任务、单提交、单验收

固定流程：

1. 下发一个原子任务；
2. Codex 修改并提交；
3. 审计实际修改文件；
4. 运行可见测试；
5. 运行外部黑盒验收；
6. 通过后进入下一任务。

不得一次性交付整个 AR-1。

## 5.2 范围变更

发现必须修改白名单外文件时，Codex必须停止并输出：

```json
{
  "status": "BLOCKED_SCOPE_CHANGE_REQUIRED",
  "required_file": "...",
  "reason": "...",
  "minimal_change": "..."
}
```

不得先改后报。

## 5.3 默认只读对象

- 冻结计划和验收报告；
- `AGENTS.override.md`；
- 正式章节正文；
- 整改基线和哈希清单；
- 外部验收器和隐藏样本；
- 阶段通过状态；
- 当前任务白名单之外的测试；
- 当前任务无关的业务代码与规则。

---

# 6. 运行控制唯一真源

## 6.1 唯一配置位置

以下三项控制不得新增第二份配置文件，唯一运行真源固定为：

`00_工程总控/工程执行层/L3工程/protocol_rules.json`

对象：

`patch_execution`

## 6.2 v2.1 必需字段

```json
{
  "patch_execution": {
    "enabled": false,
    "acceptance_enabled": false,
    "formal_text_write_enabled": false
  }
}
```

现有其他字段可以保留，但不得覆盖上述三项布尔值。

## 6.3 三层阻断语义

### 补丁执行

当：

`patch_execution.enabled == false`

L3_PATCH 必须在创建候选、diff、补丁审计或备份前返回：

`PATCH_EXECUTION_DISABLED`

### 正式采纳

当：

`patch_execution.acceptance_enabled == false`

任何 `--final-decision apply` 或等效调用必须返回：

`ACCEPTANCE_DISABLED`

不得仅因人工批准存在而继续。

### 正式写回

当：

`patch_execution.formal_text_write_enabled == false`

任何指向正式 `chapters/ch*.md` 的写操作必须返回：

`FORMAL_TEXT_WRITE_DISABLED`

该检查必须位于实际原子写函数之前，而不仅位于 CLI。

## 6.4 fail-closed

以下任一情况均按三项全部关闭处理：

- 配置文件缺失；
- `patch_execution` 缺失；
- 任一控制字段缺失；
- 字段不是布尔值；
- 配置 Schema 或版本无效；
- 配置读取失败。

不得回退到旧的 `approved_runtime_only` 行为。

---

# 7. 输入资格唯一规范

## 7.1 人工状态文件位置

每个待处理章节必须有一个人工状态文件：

`<project_root>/runtime/input_status/<chapter_id>.json`

示例：

`70_测试项目/TP-001_CleanHarness_IR_Runtime/runtime/input_status/ch01.json`

`chapter_id` 必须通过现有 `safe_id` 校验。

## 7.2 人工状态 Schema

Schema 文件：

`00_工程总控/工程执行层/公共组件/结构定义/章节输入状态结构.json`

Schema ID：

`xcue.chapter-input-status/1.0`

固定字段：

```json
{
  "schema_version": "xcue.chapter-input-status/1.0",
  "project_id": "TP-001",
  "chapter_id": "ch01",
  "chapter_path": "chapters/ch01.md",
  "chapter_status": "FROZEN_FOR_REVIEW",
  "source_sha256": "<64位小写SHA-256>",
  "declared_by": "human",
  "declared_at": "<RFC3339时间>"
}
```

`additionalProperties` 必须为 `false`。

## 7.3 状态枚举

```text
DRAFT_INCOMPLETE
DRAFT_COMPLETE
FROZEN_FOR_REVIEW
RETIRED
```

唯一可请求进入 L1 的人工状态：

`FROZEN_FOR_REVIEW`

`DRAFT_COMPLETE` 不等于已冻结验收。

## 7.4 技术资格条件

`eligible=true` 必须同时满足：

1. 项目由现有项目加载器成功解析；
2. `chapter_path` 位于项目 `content_root` 内；
3. 人工状态文件存在且通过 Schema；
4. `project_id`、`chapter_id`、`chapter_path` 与本次调用一致；
5. `chapter_status == FROZEN_FOR_REVIEW`；
6. `declared_by == human`；
7. 正文存在且为普通文件；
8. 实际正文 SHA-256 等于 `source_sha256`；
9. 正文有效字符数不少于 300；
10. 重复段落比例不高于 0.15；
11. 句子唯一率不低于 0.70；
12. 四字窗口重复比例不高于 0.40；
13. 不命中冻结的精确占位标记；
14. 资格报告使用当前 Schema、规则版本和校验器版本。

技术指标必须复用同一套共享实现，禁止输入资格与 L1-00 分别实现同名算法。

## 7.5 精确占位标记

只检查标准化后的完整正文是否等于以下条目，或正文全部由同一条目重复组成：

```text
在这里写第一章正文
待填
正文待填
正文未完成
TODO
TBD
```

不得使用宽泛子串规则把正常小说内容判为占位。

## 7.6 固定 reason code

```text
INPUT_STATUS_MISSING
INPUT_STATUS_SCHEMA_INVALID
INPUT_STATUS_NOT_REVIEWABLE
INPUT_IDENTITY_MISMATCH
INPUT_PATH_OUT_OF_SCOPE
INPUT_SOURCE_MISSING
INPUT_SOURCE_HASH_MISMATCH
INPUT_TOO_SHORT
INPUT_HIGH_REPETITION
INPUT_LOW_SENTENCE_UNIQUENESS
INPUT_REPEATED_NGRAM
INPUT_PLACEHOLDER_DETECTED
INPUT_ELIGIBILITY_VERSION_INVALID
```

同一输入可以返回多个 reason code，但不得只返回自由文本。

## 7.7 人工声明与机器检测冲突

人工状态只表示“请求进入验收”，不能覆盖机器技术拒绝。

即使人工声明 `FROZEN_FOR_REVIEW`，只要任一技术条件失败：

`eligible=false`

## 7.8 输入资格报告唯一真源

每次 pipeline run 只允许生成一份资格报告：

`运行记录/<pipeline_run_id>/输入资格/资格报告.json`

Schema 文件：

`00_工程总控/工程执行层/公共组件/结构定义/输入资格报告结构.json`

Schema ID：

`xcue.input-eligibility-report/1.0`

固定结构至少为：

```json
{
  "schema_version": "xcue.input-eligibility-report/1.0",
  "pipeline_run_id": "...",
  "project_id": "...",
  "chapter_id": "...",
  "chapter_source_path": "...",
  "chapter_source_sha256": "...",
  "input_status_path": "...",
  "input_status_sha256": "...",
  "eligible": false,
  "reason_codes": [],
  "metrics": {
    "effective_char_count": 0,
    "repeated_paragraph_ratio": 0.0,
    "sentence_uniqueness": 0.0,
    "repeated_fourgram_ratio": 0.0
  },
  "validator_version": "...",
  "rules_version": "...",
  "rule_artifacts": [],
  "rule_set_sha256": "...",
  "created_at": "..."
}
```

`additionalProperties` 必须为 `false`。

## 7.9 报告写入规则

资格报告必须：

- 使用 create-exclusive 语义创建；
- 已存在时返回 `INPUT_ELIGIBILITY_REPORT_EXISTS`，不得覆盖；
- 在读取正文和状态文件后立即绑定两者哈希；
- 由共享资格校验器生成；
- 不允许各入口自行生成第二份报告；
- 不允许只写 `eligible` 布尔值；
- `reason_codes` 必须来自第 7.6 节枚举；
- `metrics` 必须保存实际计算值。

## 7.10 报告失效规则

以下任一变化使旧报告立即失效：

- 正式章节哈希变化；
- 人工状态文件哈希变化；
- 项目、章节或路径变化；
- validator 版本变化；
- 资格规则集合变化；
- Schema 版本变化。

下游必须同时校验：

- 报告固定路径；
- 报告文件 SHA-256；
- 报告内部身份；
- 正文哈希；
- 状态文件哈希；
- 规则集合哈希。

仅有 `input_eligibility_report_sha256` 而无法定位并重新读取报告时，必须阻断。

---

# 8. L1 状态与路由冻结矩阵

## 8.1 唯一人工复核机器状态

所有新产物统一使用：

`REVIEW_REQUIRED`

不得再写出：

`HUMAN_REVIEW_REQUIRED`

历史文件或旧接口读取到 `HUMAN_REVIEW_REQUIRED` 时，必须在读取边界立即规范化为 `REVIEW_REQUIRED`，并记录：

`LEGACY_STATUS_NORMALIZED`

严格复验、流水线汇总和 L2 调用条件必须把两个历史表示都视为“未通过”，防止旧产物绕过。

## 8.2 方法分级

所有现有关键词、正则、词表和词频方法统一标记：

```json
{
  "method": "LEXICAL_HEURISTIC",
  "validation_status": "UNVALIDATED",
  "decision_authority": "ADVISORY"
}
```

添加标签本身不算完成，必须同时执行以下状态与路由规则。

## 8.3 L1-00

L1-00 仅处理确定性技术完整性：

| 条件 | 最终状态 | 是否进入 L2 |
|---|---|---:|
| 极短、高重复、低唯一率、重复窗口硬失败 | `SCREENING_REJECT` | 否 |
| 只有技术 warning | `REVIEW_REQUIRED` | 否 |
| 无确定性技术问题 | `SCREENING_PASS` | 继续到 L1-01 |

L1-00 技术失败不得改成词面复核。

## 8.4 L1-01

现有词面方法不得再产生：

- `STRUCTURE_SIGNAL_PRESENT`
- `SCREENING_PASS`
- 基于词面缺失的 `SCREENING_REJECT`

仅有词面证据时固定为：

`REVIEW_REQUIRED`

词面观察可以写入报告，但：

- `候选模块` 必须为空或固定为 `人工复核`；
- 不得自动路由 L2-01；
- 不得生成自动修复任务；
- 不得参与候选采纳。

## 8.5 L1-02

仅有 E/V/C 词面代理时固定为：

`REVIEW_REQUIRED`

不得因关键词命中产生 `SCREENING_PASS`，不得因关键词缺失自动路由 L2-05 或其他 L2。

## 8.6 L1-03

L1-03 分开处理：

### 确定性技术条件

已冻结的最低字数、输入资格、Schema、哈希等可以形成技术拒绝或技术通过。

### 词面型发布判断

钩子、收益、追读、情绪等词面证据只能：

`REVIEW_REQUIRED`

即使全部词面指标命中，也不得产生发布通过或候选采纳资格。

## 8.7 流水线汇总

优先级固定为：

1. 任一确定性硬拒绝 → `SCREENING_REJECT`；
2. 无硬拒绝，但任一业务闸门仅有未验证启发式 → `REVIEW_REQUIRED`；
3. 只有全部必需闸门由已验证的非词面方法明确通过时，才可形成 `SCREENING_PASS`。

AR-1 不建设已验证非词面业务方法，因此生产小说输入在 AR-1 期间通常不能形成业务级全通过。

## 8.8 L2 调用规则

流水线不得因以下内容调用 L2：

- `REVIEW_REQUIRED`；
- `ADVISORY` 词面发现；
- `候选模块 == 人工复核`；
- 空候选模块。

只有明确的、非启发式失败和合法 L2-99 接口判断才可进入相应 L2。

---

# 9. 严格复验、采纳分离与历史撤销

## 9.1 三个不同概念

补丁审计必须分别记录：

```json
{
  "revalidation_passed": true,
  "acceptance_enabled": false,
  "accepted": false
}
```

不得继续用一个 `accepted` 字段同时表达复验是否通过和是否允许正式采纳。

## 9.2 必需闸门集合

复验器的必需闸门固定为：

```json
["L1-00", "L1-01", "L1-02", "L1-03"]
```

必须恰好各出现一次。缺失、重复、未知闸门均失败。

## 9.3 正向通过完整契约

`revalidation_passed=true` 只允许在第一层报告满足以下完整谓词时出现：

### 顶层字段

```json
{
  "status": "SCREENING_PASS",
  "publish_authority": false,
  "human_review_required": false,
  "validation_status": "VALIDATED",
  "decision_scope": "VALIDATED_GATE_CONTRACT",
  "heuristic": false
}
```

### 闸门字段

每个必需闸门必须同时满足：

```json
{
  "判断结果": "SCREENING_PASS",
  "是否进入L15": "否",
  "最终状态": "VALIDATED_PASS"
}
```

并且：

- `失败类型` 为空；
- `失败位置` 为空；
- `调用方向` 不得指向 L1.5、L2、L3 或 L3_PATCH；
- 闸门对象通过当前第一层报告 Schema；
- 四个闸门名称唯一且顺序不影响判断。

### 失败与路由

- 顶层 `失败包` 长度为 0；
- 独立失败包文件 `failure_count == 0` 且 `items == []`；
- `路由建议` 长度为 0；
- 不存在 `REVIEW_REQUIRED` 或历史 `HUMAN_REVIEW_REQUIRED`；
- 不存在任何 heuristic=true 的闸门或失败项。

### 血缘与版本

- 输入资格有效；
- 第一层报告、失败包、规则集合、正式章节、输入快照和阶段输入血缘一致；
- evaluator_version 等于当前最低允许版本；
- 所有相关 Schema 均为当前允许版本。

任一条件不满足：

`revalidation_passed=false`

## 9.4 正向控制的适用边界

`VALIDATED_GATE_CONTRACT` 必须加入第一层报告 Schema 的 `decision_scope` 枚举。

该值在 AR-1 中只用于：

- 复验判定器的合成正向夹具；
- 未来已独立验证的非词面判断器。

AR-1 的生产 L1 不得生成 `VALIDATED_GATE_CONTRACT`，也不得把词面结果包装成该值。

正向夹具必须通过真实 Schema 和真实报告加载器，不能直接构造绕过 Schema 的 Python 字典。

## 9.5 `accepted` 公式

```text
accepted
= revalidation_passed
  AND patch_execution.acceptance_enabled
  AND patch_execution.enabled
  AND patch_execution.formal_text_write_enabled
  AND 未命中历史资格撤销
  AND 所有未来正式采纳条件
```

AR-1 期间三个运行控制均为 false，因此：

`accepted=false`

但复验器必须仍能正确区分正例和负例。

## 9.6 AR-1 状态

正向复验通过但采纳关闭：

`REVALIDATION_PASSED_ACCEPTANCE_DISABLED`

复验失败：

`REVALIDATION_FAILED`

AR-1 期间不得生成新的：

`READY_FOR_ACCEPTANCE`

## 9.7 正负控制矩阵

| 场景 | revalidation_passed | accepted |
|---|---:|---:|
| 完整 `VALIDATED_GATE_CONTRACT`、失败包空、血缘正确、采纳关闭 | true | false |
| L1-00 拒绝、L1-01 正向 | false | false |
| 任一 `REVIEW_REQUIRED` | false | false |
| 历史 `HUMAN_REVIEW_REQUIRED` | false | false |
| failure packet 非空 | false | false |
| 缺失或重复闸门 | false | false |
| 哈希、血缘或 Schema 错误 | false | false |
| evaluator_version 过期 | false | false |
| 有人工批准但其他条件失败 | false | false |

第一行必须存在，防止将判定器硬编码为恒 false。

## 9.8 历史产物不可变

历史 `READY_FOR_ACCEPTANCE` 文件不得：

- 改写；
- 补字段；
- 重命名后继续使用；
- 重新签名；
- 覆盖原哈希。

历史文件只作为证据保留。

## 9.9 历史资格撤销唯一真源

新增运行时必读配置：

`00_工程总控/工程执行层/L3工程/历史补丁资格撤销.json`

Schema 文件：

`00_工程总控/工程执行层/公共组件/结构定义/历史补丁资格撤销结构.json`

Schema ID：

`xcue.patch-revocation/1.0`

固定结构：

```json
{
  "schema_version": "xcue.patch-revocation/1.0",
  "minimum_evaluator_version": "ar1-revalidation-v2",
  "revoked_statuses": ["READY_FOR_ACCEPTANCE"],
  "reason_code": "INVALIDATED_BY_AR1_REVALIDATION_V2",
  "created_at": "...",
  "created_by": "human"
}
```

`additionalProperties` 必须为 `false`。

## 9.10 撤销运行规则

任何历史候选、补丁审计或 apply 请求必须在实际写入前检查：

1. 撤销配置存在并通过 Schema；
2. 当前审计 evaluator_version 不低于 `minimum_evaluator_version`；
3. 审计原状态不在 `revoked_statuses`；
4. 审计已按当前规则重新生成并通过复验。

以下情况必须 fail-closed：

- 撤销文件缺失；
- Schema 无效；
- evaluator_version 缺失；
- evaluator_version 低于最低版本；
- 状态命中撤销集合；
- 旧产物只补字段但没有从原始输入重新运行。

阻断状态：

`PATCH_QUALIFICATION_REVOKED`

外部验收必须证明旧 READY 无法进入 apply。

---

# 10. L2-01 唯一输入接口与职责

## 10.1 唯一选择依据

L2-01 不读取不存在的 `route` 字段。

唯一合法输入条件是现有 L2-99 接口判断同时满足：

```text
接口判断.主候选模块 == "L2-01"
AND 接口判断.最终状态 == "接口明确"
AND 接口判断.是否越界 == "否"
```

`次候选模块 == "L2-01"` 不得自动生成 L2-01 任务，应进入人工复核或重新路由。

上游原始 `失败包.items[].候选模块` 只作为 L2-99 判断输入，不作为 L2-01 第二套真源。

## 10.2 唯一允许输出

L2-01 只输出结构化任务，不生成正文、候选、diff 或 patch plan。

固定任务对象：

```json
{
  "task_id": "...",
  "source_failure_index": 0,
  "source_gate": "L1-01",
  "source_failure_type": "...",
  "source_name": "...",
  "evidence_anchors": [
    {
      "paragraph": 1,
      "quote": "..."
    }
  ],
  "rule_id": "...",
  "rule_version": "...",
  "rule_hash": "...",
  "revision_objective": "...",
  "facts_to_preserve": [],
  "acceptance_conditions": [],
  "uncertainties": [],
  "automatic_execution_eligible": false,
  "requires_generative_completion": true,
  "patch_operations": []
}
```

该对象必须成为第二层报告的显式 Schema 字段，不得只藏在允许任意内容的 `extensions` 中。

## 10.3 缺证据处理

没有有效文本锚点时，不得编造任务定位。

输出状态：

`BLOCKED_MISSING_ANCHOR`

并保持：

```json
{
  "automatic_execution_eligible": false,
  "requires_generative_completion": true,
  "patch_operations": []
}
```

## 10.4 重复 60 次问题的正确完成条件

完成不是“生成另一份不重复正文”，而是：

- `_确定性替换文本` 及等效正文构造职责不存在；
- 不存在任何字数补齐循环；
- 不生成候选正文；
- 不生成 unified diff；
- 不生成 patch plan；
- 不调用 L3_PATCH；
- 不具有自动执行资格；
- 正式正文哈希不变；
- 上游失败项、接口判断和规则血缘均被保留。

## 10.5 参数化验收

使用外部临时项目夹具，不修改正式项目注册表，至少变化：

- 3 个 project_id；
- 3 个 chapter_id；
- 3 个章节路径；
- 失败项数量与顺序；
- 锚点内容；
- 已知故事专有词；
- 重复次数。

所有结果必须保持相同职责边界，不得依赖 TP-001、ch01 或测试文件名。

---

# 11. 血缘唯一规范

## 11.1 正文对象必须拆分

不得再用含糊的 `source_path/source_sha256` 同时表示正式章节、输入快照和当前阶段输入。

统一血缘对象至少包含：

```json
{
  "project_id": "...",
  "chapter_id": "...",
  "chapter_source_path": "...",
  "chapter_source_sha256": "...",
  "input_snapshot_path": "...",
  "input_snapshot_sha256": "...",
  "stage_input_path": "...",
  "stage_input_sha256": "...",
  "input_status_path": "...",
  "input_status_sha256": "...",
  "input_eligibility_report_path": "...",
  "input_eligibility_report_sha256": "...",
  "rule_artifacts": [],
  "rule_set_sha256": "...",
  "producer_stage": "...",
  "producer_version": "...",
  "created_at": "..."
}
```

## 11.2 字段语义

### 正式章节

- `chapter_source_path`：项目根内正式章节的规范化相对路径；
- `chapter_source_sha256`：生成输入快照时正式章节的哈希。

### 输入快照

- `input_snapshot_path`：当前 pipeline run 的只读输入快照相对路径；
- `input_snapshot_sha256`：快照哈希；
- 创建快照时必须验证它与 `chapter_source_sha256` 一致。

### 当前阶段输入

- `stage_input_path`：本阶段实际读取的文件；
- `stage_input_sha256`：本阶段实际读取文件的哈希；
- L1 通常等于输入快照；
- 后续阶段可以指向结构化上游产物；
- 不得用正式章节哈希冒充阶段输入哈希。

如未来存在候选正文，必须新增独立的：

- `candidate_path`
- `candidate_sha256`

不得复用上述三个对象。

## 11.3 路径规范

所有记录路径必须：

- 相对于仓库根或运行记录根；
- 使用 `/` 作为分隔符；
- 不含 `..`；
- 不使用绝对路径作为跨机器真源；
- 读取时重新执行范围检查。

## 11.4 规则产物列表

`rule_artifacts` 中每一项固定为：

```json
{
  "kind": "L1_GATE_RULES",
  "path": "00_工程总控/工程执行层/L1工程/gate_rules.json",
  "version": "...",
  "sha256": "..."
}
```

不同阶段必须列出其实际读取的每一份规则或路由文件，不得用单个含糊哈希代表多文件。

Markdown 候选标准若实际参与当前运行，也必须列入；未实际读取的文件不得加入集合制造虚假血缘。

## 11.5 规则集合哈希算法

`rule_set_sha256` 使用以下唯一算法：

1. 校验每个对象恰好包含 `kind/path/version/sha256`；
2. `path` 规范化为仓库相对 POSIX 路径；
3. 按 `(kind, path, version, sha256)` Unicode 码点升序排序；
4. 将排序后的数组使用 Python 等价规则序列化：

```python
json.dumps(
    items,
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
)
```

5. 将结果编码为 UTF-8；
6. 计算小写十六进制 SHA-256。

禁止：

- 使用文件系统遍历顺序；
- 使用绝对路径；
- 使用平台相关换行；
- 只哈希文件名；
- 各阶段自行发明集合算法。

必须提供跨两次运行、不同插入顺序得到同一哈希的测试。

## 11.6 必须同步修改的 Schema

由于现有多个 Schema 使用 `additionalProperties: false`，血缘接入必须明确覆盖：

- `输入资格报告结构.json`
- `第一层报告结构.json`
- `失败包结构.json`
- `第二层报告结构.json`
- `第三层任务包结构.json`
- `第三层补丁审计结构.json`
- 对应 Python 模型、写入器和读取器

不得把血缘塞入无人校验的自由文本或任意 `extensions`。

## 11.7 每层重新验证

每一层读取上游产物时必须重新验证：

- Schema；
- 上游文件哈希；
- 项目和章节身份；
- 正式章节哈希；
- 输入快照哈希；
- 当前阶段输入哈希；
- 人工状态文件哈希；
- 输入资格报告路径与哈希；
- 规则产物清单；
- 规则集合哈希；
- producer 版本。

缺失、篡改、过期或身份不一致全部阻断。

---

# 12. 外部黑盒验收隔离

## 12.1 验收根

验收器与隐藏样本必须位于 XC-UE 仓库和 Codex 工作区之外。

由验收者设置：

`XCUE_AR1_AUDIT_ROOT`

示例：

`<XC-UE父目录>/XC-UE_AR1_AUDIT_PRIVATE`

该目录不得加入 Cursor/Codex 工作区，不得提交到项目仓库。

## 12.2 外部内容

至少包含：

```text
validator/
hidden_cases/
expected_contracts/
baseline_hashes/
results/
```

## 12.3 隔离要求

- Codex任务中不得提供隐藏样本文本；
- 验收器从外部调用项目公开 CLI 或 Python 接口；
- 临时项目在系统临时目录生成；
- 不修改正式项目注册表；
- 验收前记录 validator 与 hidden_cases 的 SHA-256；
- 验收后复算，必须一致；
- Codex无权写 `results/`；
- `AR1_ACCEPTED` 只能由验收者根据外部结果写入。

## 12.4 防测试识别

隐藏测试运行时随机化：

- 临时目录名；
- project_id；
- chapter_id；
- 运行 ID；
- 故事词；
- 失败项顺序；
- 重复次数。

生产代码不得检查：

- `pytest`；
- `tmp_path`；
- `hidden`；
- `audit`；
- 固定测试目录名；
- 环境中的测试专用身份。

---

# 13. 工作包与固定顺序

---

## AR1-00：整改前基线

### 真实目标

在任何业务代码或配置修改前记录当前真实状态。

### 允许修改

只允许新增：

- 基线采集脚本；
- 基线结果目录。

不得修改业务代码、配置和测试。

### 必须记录

- Git 或文件快照状态；
- Python 版本；
- pytest 收集数量；
- 根 `AGENTS.md` 哈希；
- 冻结计划文件名和哈希；
- `protocol_rules.json` 当前值和哈希；
- L1、L2-01、L3 关键文件哈希；
- 全部正式正文哈希；
- 相关 Schema 哈希；
- 现有测试基线；
- 历史 READY 清单。

### 通过条件

基线可复算，正式正文零改动。

---

## 人工动作 A：生成并激活完整 override

AR1-00 通过后，由验收者按第 4 节生成完整 `AGENTS.override.md`，重启 Codex，并保存活动指令来源证据。

该动作不属于 Codex代码提交。

---

## AR1-01：运行控制与历史撤销锁定

### 真实目标

把补丁执行、正式采纳和正文写回在真实运行入口中全部关闭，并使旧 READY 无法继续 apply。

### 精确改动范围

至少包括：

- `L3工程/protocol_rules.json`
- `L3工程/历史补丁资格撤销.json`
- `公共组件/结构定义/历史补丁资格撤销结构.json`
- `L3工程/协议规则加载.py`
- `L3工程/L3补丁执行器.py`
- `L3工程/L3补丁执行入口.py`
- 与运行控制和撤销直接相关的 Schema/测试

### 必须保持

- 历史审计文件只读；
- 读取失败时 fail-closed；
- 不删除历史产物；
- 不修改正式正文；
- 不通过 CLI 隐藏参数绕过实际写函数检查。

### 正负控制

- 三项 false：分别阻断执行、采纳、写回；
- 缺任一字段：阻断；
- 非布尔值：阻断；
- 测试夹具中三项 true：加载器能正确读取，但 AR-1 正式配置仍为 false；
- 旧 READY：`PATCH_QUALIFICATION_REVOKED`；
- 新 evaluator 版本但未通过当前复验：拒绝；
- 历史文件哈希前后不变。

---

## AR1-02：输入资格与唯一报告

### 真实目标

只有状态明确冻结、哈希一致且技术完整的章节可以进入 L1，并生成一份不可覆盖、可复算的资格报告。

### 精确改动范围

- `章节输入状态结构.json`
- `输入资格报告结构.json`
- 共享输入资格校验器；
- 共享技术完整性计算模块；
- 资格报告 create-exclusive 写入器；
- 项目加载与 L1 前置接入；
- 专属测试。

### 必须保持

- 项目加载器原有路径安全；
- 不为 TP-001 或 ch01 特判；
- 人工状态不能覆盖机器失败；
- 正文或状态变化后旧资格立即失效；
- 每个 pipeline run 只存在一份资格报告。

---

## AR1-03：入口、状态规范化与血缘封闭

### 真实目标

PIPELINE、PROJECT、L1、L2、L3 和 L3_PATCH 均无法绕过同一资格报告、状态规范化和血缘。

### 精确改动范围

- `统一运行入口.py`
- `流水线运行.py`
- L1/L2/L3/L3_PATCH 入口
- 状态规范化共享模块
- 血缘共享校验器
- 第 11 节列出的 Schema、模型、读写器
- 专属测试

### 必须保持

- 新产物只写 `REVIEW_REQUIRED`；
- 历史旧值读取后立即规范化；
- 所有入口共用同一资格报告；
- 不兼容旧缺血缘产物；
- 缺字段不得 warning 后继续；
- 旧运行记录不得自动补字段。

---

## AR1-04：严格复验正负契约

### 真实目标

修复复验算法，同时保持采纳关闭；证明算法既不是恒 false，也不会接受词面启发式伪正例。

### 精确改动范围

- `第一层报告结构.json` 中 `VALIDATED_GATE_CONTRACT` 所需最小扩展；
- `L3工程/L3补丁执行器.py` 中复验判定；
- `第三层补丁审计结构.json`
- 补丁审计模型/加载器；
- 直接相关测试。

### 必须实现

- 第 9 节完整正向谓词；
- `revalidation_passed`
- `acceptance_enabled`
- `accepted`
- 正负控制矩阵；
- 历史状态兼容拒绝；
- AR-1 新状态。

### 禁止

- 永久返回 false；
- 把词面 `SCREENING_PASS` 当正例；
- 删除正向测试；
- 用人工批准覆盖复验；
- 保留同义 READY 状态。

---

## AR1-05：L2-01 职责收缩

### 真实目标

撤销固定故事、重复填充和正文补丁职责，只产出结构化生成任务。

### 精确改动范围

至少包括：

- `L2工程/L2_01_叙事结构能力.py`
- `L2工程/L2运行入口.py`
- `L2工程/修复单生成.py`
- `L2工程/L2模型.py`
- `第二层报告结构.json`
- 直接相关测试

### 唯一输入

`主候选模块 == "L2-01"`、`最终状态 == "接口明确"`、`是否越界 == "否"`。

### 必须保持

- 上游失败项不被吞掉；
- L2-99 路由语义不因本任务改变；
- 正式正文不变；
- 不新增等效生成模块。

---

## AR1-06：词面启发式去授权

### 真实目标

保留词面证据，但撤销它产生业务通过、自动失败路由和采纳权限的能力。

### 精确改动范围

- L1-01、L1-02、L1-03 决策汇总层；
- L1报告和失败包生产；
- 第一层报告/失败包 Schema；
- 流水线 L2 调用条件；
- 直接相关测试。

### 必须实现

第 8 节完整状态与路由矩阵。

### 正负控制

- 关键词全命中垃圾文本：不得业务通过、不得自动 L2；
- 正常文本目标词少：不得自动拒绝、不得自动 L2；
- 技术硬失败：仍由 L1-00 拒绝；
- 纯词面发现：`REVIEW_REQUIRED`；
- 无词面发现：也不能因此业务通过；
- 新产物不得出现 `HUMAN_REVIEW_REQUIRED`。

---

## AR1-07：外部对抗验收与回归

### 真实目标

证明前六项不是通过修改代理指标、测试、路由、状态、历史文件或样本制造的。

### 必须执行

1. 外部隐藏黑盒验收；
2. AR-1 核心测试；
3. 受影响模块回归；
4. 全量限时回归；
5. 前后文件与正文哈希比较；
6. 修改白名单审计；
7. 旧测试断言变更审计；
8. override 活动来源复核；
9. 历史 READY 撤销实跑；
10. 规则集合哈希顺序稳定性测试。

### 测试结论

- 核心测试必须全部完成通过；
- 受影响模块测试必须全部完成；
- 全量测试若超时，只能记为 `FULL_SUITE_INCOMPLETE`；
- 不得声称“全量无新增失败”。

---

# 14. 既有测试修改规则

行为发生合法变化时，可以修改直接相关旧测试，但必须：

1. 在证据包中保存旧断言；
2. 说明旧断言为何对应已废止的错误语义；
3. 新测试必须包含正向、负向和边界控制；
4. 不得减少原有路径覆盖；
5. 不得只把 expected 值改成当前输出；
6. 不得修改与当前工作包无关的测试；
7. 不得新增 skip、xfail 或条件性逃逸。

---

# 15. Codex 原子任务格式

```text
任务编号：

真实目标效果：

精确允许修改文件：
- ...

禁止修改：
- ...

必须保持不变：
- ...

输入和现有接口：
- ...

唯一要求的外部结果：
- ...

正向控制：
- ...

负向控制：
- ...

边界控制：
- ...

等效绕过判定：
- ...

必须运行：
- ...

必须提交：
- 实际修改文件清单
- 行为变化说明
- 旧断言与新断言差异
- 测试结果
- 正文前后哈希
- 未解决风险
- 是否触发范围变更

停止条件：
白名单不足、规范冲突、无法维持保持不变项时，停止并输出 BLOCKED_SCOPE_CHANGE_REQUIRED。
```

---

# 16. 阶段硬验收门槛

## H1：指令链完整且一致

活动 `AGENTS.override.md` 完整继承根规则，并追加 AR-1 覆盖；新 Codex 会话的活动来源有日志证据。

## H2：运行控制真实关闭

三项开关位于唯一配置真源，并由实际入口和写函数执行。

## H3：历史资格真实撤销

旧 READY 文件保持原样，但运行时必读撤销索引和最低 evaluator 版本使其无法 apply。

## H4：输入资格明确

人工状态、Schema、阈值、reason code、唯一资格报告和 fail-closed 均实现。

## H5：入口无绕过

PIPELINE、PROJECT、L1、L2、L3、L3_PATCH 均校验同一资格报告和血缘。

## H6：机器状态唯一

新产物只使用 `REVIEW_REQUIRED`；旧值读取后规范化且不能通过复验。

## H7：复验算法真实存在

完整 `VALIDATED_GATE_CONTRACT` 正例得到 `revalidation_passed=true`；所有负例为 false；采纳始终关闭。

## H8：L2-01 职责收缩

不生成正文、候选、diff、patch plan，不调用 L3_PATCH。

## H9：无项目和样本特判

不同临时项目、章节和内容保持同一行为。

## H10：词面启发式无业务授权

词面发现只能 `REVIEW_REQUIRED`，不产生业务通过或自动 L2。

## H11：血缘对象明确

正式章节、输入快照和阶段输入分别绑定；规则清单和集合哈希可复算。

## H12：独立验收隔离

验收器和隐藏样本位于 Codex 工作区外，哈希前后一致。

## H13：正式正文保护

所有测试和异常路径中正式正文哈希不变。

## H14：证据完整

全部结论可以从文件、哈希和测试结果复算。

任一硬门槛失败，AR-1 不得通过。

---

# 17. 最低证据包

目录：

`运行记录/AR1-ACCEPTANCE-<run_id>/`

至少包含：

- `AR1_整改前基线.json`
- `冻结计划哈希.json`
- `根AGENTS与override前后哈希.json`
- `活动指令来源日志.json`
- `任务提交清单.json`
- `每任务修改白名单.json`
- `实际修改文件清单.json`
- `旧测试断言变更清单.json`
- `关键文件前后哈希.json`
- `正式正文前后哈希.json`
- `历史审计前后哈希.json`
- `运行控制测试结果.json`
- `历史READY撤销测试结果.json`
- `输入资格状态测试结果.json`
- `输入资格报告唯一性测试结果.json`
- `入口与血缘测试结果.json`
- `规则集合哈希稳定性测试结果.json`
- `状态规范化测试结果.json`
- `严格复验完整正负控制结果.json`
- `L2-01外部黑盒结果.json`
- `词面启发式状态路由结果.json`
- `目标投机检查结果.json`
- `外部验收器前后哈希.json`
- `受影响模块回归结果.json`
- `全量限时回归结果.json`
- `未解决事项.json`

---

# 18. 阶段允许终态

只允许：

- `AR1_ACCEPTED`
- `AR1_REJECTED`
- `AR1_BLOCKED`
- `AR1_PARTIAL_NOT_ACCEPTED`

不得使用：

- 基本完成；
- 大部分通过；
- 技术上完成；
- 可先进入下一阶段；
- 仅剩少量问题；
- 等待后续补证。

`AR1_ACCEPTED` 只能由独立验收者写入。

---

# 19. AR-1 通过后可以声明什么

只可以声明：

- 输入控制链恢复最低可信；
- 运行时补丁、采纳和正文写回处于关闭状态；
- 复验通过与采纳权限已经分离；
- 固定样例伪修复职责已撤销；
- 词面启发式已失去业务授权；
- 可以开始下一阶段的正向小说能力设计。

不得声明：

- XC-UE 已理解小说；
- L1 判断准确；
- L2-01 能自动修文；
- B2 自动补丁恢复；
- 真实小说业务闭环完成；
- 系统可以无人值守创作。

---

# 20. 固定执行顺序

0. v2.2 候选计划独立验收；
1. 验收通过后生成 v2.2 FROZEN 副本并记录 SHA-256；
2. AR1-00：整改前基线；
3. 验收者生成完整 `AGENTS.override.md`；
4. 关闭旧 Codex 会话，启动新会话并验证活动指令来源；
5. AR1-01：运行控制与历史撤销；
6. AR1-02：输入资格与唯一报告；
7. AR1-03：入口、状态规范化与血缘；
8. AR1-04：严格复验正负契约；
9. AR1-05：L2-01 职责收缩；
10. AR1-06：词面启发式去授权；
11. AR1-07：外部对抗验收与回归。

不得跳步、并行或合并。

---

# 21. 反向压力测试

## 21.1 override 只写新增限制，导致根规则丢失

由“完整复制根 AGENTS.md + 追加覆盖区块”、前缀一致性检查和活动来源日志阻断。

## 21.2 新旧人工复核状态并存

由新产物唯一 `REVIEW_REQUIRED`、读取边界规范化和复验双值拒绝阻断。

## 21.3 Codex 把三项开关写进新 JSON，但运行时不读取

由唯一真源路径、实际入口调用测试和缺字段 fail-closed 阻断。

## 21.4 Codex 把复验器永久写成 false

由完整 `VALIDATED_GATE_CONTRACT` 正向控制要求 `revalidation_passed=true` 阻断。

## 21.5 Codex 把当前词面 SCREENING_PASS 包装成正例

由 `decision_scope=VALIDATED_GATE_CONTRACT`、`validation_status=VALIDATED`、`heuristic=false` 和完整闸门谓词阻断。

## 21.6 各入口各自产生一份资格报告

由固定路径、create-exclusive、每 run 一份和下游报告哈希复验阻断。

## 21.7 正式章节哈希与输入快照哈希混用

由三类路径/哈希字段拆分和每层重新验证阻断。

## 21.8 规则集合因遍历顺序变化而产生不同哈希

由规范化 JSON 排序算法和插入顺序无关测试阻断。

## 21.9 Codex 直接改写旧 READY 文件标失效

由历史文件哈希保护、独立撤销索引和外部哈希对比阻断。

## 21.10 Codex 只给词面报告加 ADVISORY 标签

由冻结状态/路由矩阵和黑盒调用 L2 检查阻断。

## 21.11 Codex 改掉重复 60 次，换成模板或随机句

由 L2-01 完全禁止正文类输出和外部文件检查阻断。

## 21.12 Codex 改测试以匹配代码

由旧断言留档、外部隐藏验收和白名单审计阻断。

---

# 22. 候选冻结结论

v2.2 已针对 v2.1 验收报告中的六个定点阻断项完成修订：

- 指令覆盖完整继承根规则；
- 人工复核状态唯一；
- 正向复验谓词完整冻结；
- 输入资格报告成为可定位、不可覆盖的唯一产物；
- 正文与规则血缘可复算；
- 历史 READY 通过独立撤销真源失效且历史文件保持不可变。

当前状态仍为：

`CANDIDATE_FOR_FREEZE`

下一步只能进行计划书独立验收。

通过后才能复制为：

`XC-UE_AR1_验收可信性恢复计划书_v2.2_FROZEN_2026-06-25.md`

并记录冻结文件 SHA-256。

未经再次验收，不得生成活动 override，不得交付 Codex实施。
