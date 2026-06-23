---
document_id: XCUE-REMEDIATION-PLAN
document_version: v1.1
status: PENDING_ACCEPTANCE
date: 2026-06-23
human_readable_plan: XC-UE_全量整改计划书_v1.1_2026-06-23.md
canonical_task_ledger: XC-UE_整改任务台账_v1.1_2026-06-23.json
supersedes: XC-UE_全量整改任务清单与修改方向_v1.0_2026-06-23.md
---

# XC-UE 全量整改计划书与任务台账说明

- 修订版本：v1.1
- 适用对象：`XC-UE (2).zip`
- 输入依据：两轮深度盘查报告、v1.0 任务清单及其验收报告
- 当前状态：待独立验收，未冻结
- 机器执行真源：`XC-UE_整改任务台账_v1.1_2026-06-23.json`
- 本 Markdown 用途：解释目标、修改方向、验收标准和执行纪律
- 状态更新规则：任务状态与依赖只修改 JSON 台账，再重新生成 Markdown；禁止两处分别手改

## 版本修订摘要

v1.1 对 v1.0 作出以下实质修正：

1. 为所有任务补齐统一元数据；
2. 将所有模糊依赖改为明确任务 ID；
3. 增加 59 个盘查问题的完整追溯矩阵；
4. 新增 M2-08、M2-09、M5-07、SCOPE-01；
5. 将 5 个过大任务改为 Epic，并拆出 17 个可独立验收子任务；
6. 将严重度与执行顺序分离；
7. 将首批 10 项拆成 6 个串行批次；
8. 将模糊验收词改为命令、数值或确定行为；
9. 定义工程、生产候选、业务验证、自动改写和发布权限五级成熟度；
10. 增加版本变更、回滚、清理、Fixture 边界和可复现构建要求。

## 任务规模

- 主要工作项：59
- Epic：5
- Epic 子任务：17
- 总任务 ID：76
- 可直接领取任务：71
- 可直接领取任务严重度：P0=33，P1=35，P2=3

任务数量增加不是范围扩张，而是把原先不可独立验收的“大任务”拆成可追踪工作包。

# 一、整改总判定

XC-UE 当前的核心缺陷不是单个函数，而是四套机制未统一：

```text
文档声明的规则
运行时真正执行的规则
阶段输入输出契约
运行记录与验收证据
```

整改路线固定为：

```text
基线与故障样本
→ 输入和状态可信
→ 运行证据不可变
→ 规则真实控制执行
→ 项目中立化
→ Python 工程重构
→ 最小执行—Diff—回流闭环
→ 文档、CI、发布候选验收
```

# 二、六个工程不变量

## INV-01 非法输入绝不成功

损坏 JSON、空对象、缺少必填字段、未知 Schema 版本、血缘不匹配和非法项目清单，必须在业务规则执行前失败。

## INV-02 结构化规则必须真实控制执行

运行规则必须经过：结构化定义、Schema 校验、解析对象、执行器消费和行为测试。仅被解析进报告的规则不得标记为已执行。

## INV-03 运行证据不可静默覆盖

同一运行身份不得覆盖旧报告。重试必须创建新 attempt，并保留父运行、输入哈希、规则哈希、输出哈希和失败原因。

## INV-04 单项失败不得无条件拖死整批

可执行项、待重路由项、外部阻断项和非法项必须分离；只有系统级不可恢复错误可以终止整批。

## INV-05 技术、业务、人工和发布状态必须分离

执行完成不等于业务通过；启发式未发现风险不等于验证通过；人工待审不等于发布许可。

## INV-06 引擎不得依赖具体小说项目

删除 TP-001 后，引擎仍须能启动、校验规则和项目清单。新增第二项目不得修改引擎源码。

# 三、任务治理规则

## 3.1 单一台账

JSON 台账是任务状态、依赖、责任人、严重度、交付物和验收测试的唯一机器真源。Markdown 不单独维护这些字段。

## 3.2 状态转换

```text
TODO → IN_PROGRESS → READY_FOR_REVIEW → ACCEPTED
                  ↘ BLOCKED
                  ↘ REJECTED
TODO/IN_PROGRESS → DEFERRED
```

进入 `IN_PROGRESS` 的前提：全部 `depends_on` 为 `ACCEPTED`。

Epic 不得直接领取。只有全部子任务为 `ACCEPTED`，Epic 才可进入 `READY_FOR_REVIEW`。

## 3.3 严重度不覆盖执行顺序

- `severity=P0`：缺陷严重，阻断相应能力或发布；
- `sequence`：实际执行次序；
- 任何任务不得因 P0 而跳过依赖。

## 3.4 每项任务的强制提交证据

1. 修改文件清单；
2. 设计选择和被拒绝方案；
3. 新增或修改测试；
4. 可复制命令及真实结果；
5. 未解决问题；
6. 回滚方法；
7. 任务状态变更记录。

## 3.5 全局禁止项

- 不得用改名代替功能实现；
- 不得删除失败样本以获得通过；
- 不得通过放宽 Schema 兼容非法输入；
- 不得重新引入 Python 业务 fallback；
- 不得在权限、diff、审批、回滚未成立前自动改正式正文；
- 不得批量冻结全部规则；
- 不得覆盖历史 run/attempt；
- 不得把 Fixture 成功解释为作品质量或生产就绪。

# 四、成熟度状态

| 状态 | 含义 | 是否允许发布 |
|---|---|---|
| `ENGINEERING_CORE_READY` | 输入、状态、证据、项目边界和测试链成立 | 否 |
| `TECHNICAL_PRODUCTION_CANDIDATE` | 最小正式规则、发布包和跨平台验收成立 | 否 |
| `BUSINESS_SIGNAL_VALIDATED` | L1 代理指标通过人工标注集验证 | 仍需人工 |
| `AUTO_EDIT_APPROVED` | 指定任务类型通过沙箱、diff、审批、回滚验证 | 仅限获批任务类型 |
| `PUBLICATION_AUTHORITY_GRANTED` | 项目外部明确授予发布判断权 | 是，且不由 M8 自动获得 |

M8 完成的最高自动结果是 `TECHNICAL_PRODUCTION_CANDIDATE`，并固定：

```text
publication_authority = NONE
business_validation = UNVALIDATED
```

# 五、任务总览与机读索引

| Seq | Task ID | 类型 | 严重度 | 状态 | 明确依赖 | 来源问题 |
|---:|---|---|---|---|---|---|
| 001 | M0-01 | TASK | P0 | TODO | — | GOV-M0-01 |
| 002 | M0-02 | TASK | P0 | TODO | M0-01 | R1-P0-01 |
| 003 | SCOPE-01 | TASK | P0 | TODO | M0-01 | R1-P1-08 |
| 004 | M1-01 | TASK | P0 | TODO | M0-02 | R2-P0-01 |
| 005 | M1-02 | TASK | P0 | TODO | M1-01 | R2-C-02, R2-P0-01 |
| 006 | M1-03 | TASK | P0 | TODO | M1-01 | R2-C-01, R2-P0-01 |
| 007 | M1-04 | TASK | P0 | TODO | M1-03 | R1-P0-01, R2-C-03 |
| 008 | M1-05 | TASK | P0 | TODO | M1-01, M1-02, M1-03 | R1-P0-05, R1-P2-04, R2-A-03… |
| 009 | M2-01 | TASK | P0 | TODO | M1-01, M1-02, M1-05 | R2-P-01, R2-P0-03 |
| 010 | M2-02 | TASK | P0 | TODO | M2-01 | R1-P2-04, R2-P0-03, R2-P0-04 |
| 011 | M2-03 | TASK | P1 | TODO | M2-02 | R2-C-06 |
| 012 | M2-04 | EPIC | P0 | TODO | M2-02 | R2-P-02, R2-P0-03 |
| 013 | M2-04A | SUBTASK | P0 | TODO | M2-02 | R2-P-02, R2-P0-03 |
| 014 | M2-04B | SUBTASK | P0 | TODO | M2-04A | R2-P-02, R2-P0-03 |
| 015 | M2-04C | SUBTASK | P0 | TODO | M2-04A, M2-04B | R2-P-02, R2-P0-03 |
| 016 | M2-05 | TASK | P0 | TODO | M2-02 | R2-P-03 |
| 017 | M2-06 | TASK | P1 | TODO | M2-05 | R1-P2-05, R2-C-07, R2-P-04 |
| 018 | M2-07 | TASK | P0 | TODO | M1-02, M1-05 | R2-P-05, R2-P0-05 |
| 019 | M2-08 | TASK | P1 | TODO | M2-05, M2-06 | R1-P2-05, R2-P-08 |
| 020 | M2-09 | TASK | P0 | TODO | M2-02 | R2-A-07 |
| 021 | M3-01 | TASK | P0 | TODO | M1-01, M1-02, M1-03, M1-05, M2-01, M2-02, M2-05, M2-07 | R1-P0-03, R2-D-02, R2-D-06 |
| 022 | M3-02 | TASK | P0 | TODO | M3-01 | R1-P0-03 |
| 023 | M3-03 | TASK | P0 | TODO | M3-01 | R1-P0-03, R2-P0-02 |
| 024 | M3-04 | TASK | P0 | TODO | M3-01 | R1-P0-03, R2-P0-02 |
| 025 | M3-05 | EPIC | P0 | TODO | M3-01 | R1-P0-03, R2-A-06, R2-P0-02 |
| 026 | M3-05A | SUBTASK | P0 | TODO | M3-01 | R2-A-06, R2-P0-02 |
| 027 | M3-05B | SUBTASK | P0 | TODO | M3-01 | R2-A-06, R2-P0-02 |
| 028 | M3-05C | SUBTASK | P0 | TODO | M3-01 | R2-A-06, R2-P0-02 |
| 029 | M3-06 | TASK | P1 | TODO | M3-02, M3-03, M3-04, M3-05A, M3-05B, M3-05C | R1-P0-03, R2-A-01, R2-P0-02 |
| 030 | M3-07 | TASK | P1 | TODO | M3-06 | R1-P0-06, R2-P-07 |
| 031 | M4-01 | TASK | P0 | TODO | M1-02, SCOPE-01 | R1-P0-02, R1-P1-08, R2-A-04 |
| 032 | M4-02 | TASK | P0 | TODO | M4-01 | R1-P0-02, R2-A-04 |
| 033 | M4-03 | TASK | P0 | TODO | M4-02 | R1-P0-02 |
| 034 | M4-04 | TASK | P0 | TODO | M4-03 | R1-P0-02 |
| 035 | M4-05 | TASK | P1 | TODO | M4-04 | R1-P1-02, R2-C-09 |
| 036 | M5-01 | TASK | P1 | TODO | M1-04, M1-05, M2-02, M3-01, M4-05 | R1-P1-01, R2-C-04 |
| 037 | M5-02 | EPIC | P1 | TODO | M5-01, M2-01, M2-02, M2-05, M2-07 | R2-C-05 |
| 038 | M5-02A | SUBTASK | P1 | TODO | M5-01, M2-01, M2-02, M2-05 | R2-C-05 |
| 039 | M5-02B | SUBTASK | P1 | TODO | M5-01, M2-05, M2-07 | R2-C-05 |
| 040 | M5-02C | SUBTASK | P1 | TODO | M5-02A, M5-02B, M2-04C | R2-C-05 |
| 041 | M5-03 | TASK | P1 | TODO | M5-01, M5-02C | R1-P1-02 |
| 042 | M5-04 | TASK | P1 | TODO | M1-01, M5-01 | R2-C-07, R2-C-08 |
| 043 | M5-05 | TASK | P1 | TODO | M5-01, M5-03 | R1-P1-01 |
| 044 | M5-06 | TASK | P2 | TODO | M4-05, M5-01, M5-03 | R1-P1-02, R1-P2-03, R2-A-06… |
| 045 | M5-07 | TASK | P1 | TODO | M5-01, M5-05 | R1-P1-01, R1-P2-02 |
| 046 | M6-01 | TASK | P0 | TODO | M1-05 | R1-P0-04, R1-P0-05, R2-A-02 |
| 047 | M6-02 | TASK | P1 | TODO | M2-05, M3-05A, M3-05B, M3-05C, M4-02, M6-01 | R1-P0-04 |
| 048 | M6-03 | TASK | P1 | TODO | M2-02, M2-05, M2-07, M3-05A, M3-05B, M3-05C, M4-02, M5-03, M6-02 | R1-P0-04 |
| 049 | M6-04 | EPIC | P1 | TODO | M6-03 | R1-P0-04 |
| 050 | M6-04A | SUBTASK | P1 | TODO | M2-04C, M2-05, M3-05A, M4-02, M6-03 | GOV-M6-04A |
| 051 | M6-04B | SUBTASK | P1 | TODO | M6-04A | GOV-M6-04B |
| 052 | M6-04C | SUBTASK | P1 | TODO | M6-04B, M3-05A, M3-05C | GOV-M6-04C |
| 053 | M6-04D | SUBTASK | P1 | TODO | M6-04C, M2-05 | GOV-M6-04D |
| 054 | M6-05 | TASK | P1 | TODO | M1-01, M2-02, M2-05, M3-06, M6-04D | R1-P0-04 |
| 055 | M6-06 | TASK | P1 | TODO | M2-04C, M2-05, M6-04D | R1-P0-04, R2-P-02 |
| 056 | M7-01 | TASK | P0 | TODO | M1-05 | R1-P0-07, R1-P1-07, R2-D-03 |
| 057 | M7-02 | TASK | P1 | TODO | M3-01 | R1-P1-06, R2-D-01 |
| 058 | M7-03 | TASK | P1 | TODO | M7-01 | R1-P0-07, R2-D-03, R2-D-04 |
| 059 | M7-04 | TASK | P2 | TODO | M0-01 | R1-P2-04, R2-D-06, R2-D-07… |
| 060 | M7-05 | TASK | P1 | TODO | M1-04, M7-01 | R1-P0-07, R1-P1-07, R2-D-05 |
| 061 | M7-06 | TASK | P1 | TODO | M3-06, M7-02 | R1-P0-03, R1-P1-06, R2-D-02 |
| 062 | M8-01 | TASK | P0 | TODO | M5-03 | R1-P1-05, R2-C-10 |
| 063 | M8-02 | TASK | P0 | TODO | M1-03, M1-04 | R1-P0-01, R1-P1-05, R2-C-03 |
| 064 | M8-03 | TASK | P0 | TODO | M3-02, M3-03, M3-04, M3-05A, M3-05B, M3-05C | R1-P0-03, R2-A-01 |
| 065 | M8-04 | TASK | P1 | TODO | M2-03, M2-04C | GOV-M8-04 |
| 066 | M8-05 | TASK | P0 | TODO | M4-02, M4-04 | R1-P0-02 |
| 067 | M8-06 | EPIC | P1 | TODO | M5-07, M7-06, M8-01 | R1-P1-01, R2-C-11, R2-P-06 |
| 068 | M8-06A | SUBTASK | P1 | TODO | M5-01 | R2-C-11, R2-P-06 |
| 069 | M8-06B | SUBTASK | P1 | TODO | M8-01, M8-02, M8-03, M8-04, M8-05 | R2-C-11, R2-P-06 |
| 070 | M8-06C | SUBTASK | P1 | TODO | M3-07, M7-05, M7-06 | R2-C-11, R2-P-06 |
| 071 | M8-06D | SUBTASK | P1 | TODO | M5-05, M5-07, M8-06A, M8-06B, M8-06C | R2-C-11, R2-P-06 |
| 072 | M8-07 | TASK | P1 | TODO | M5-05, M8-06D | R1-P1-01, R1-P2-01, R2-P-06 |
| 073 | M8-08 | TASK | P1 | TODO | M3-07, M4-04, M7-06, M8-03, M8-05, M8-06D | R1-P0-05, R1-P0-06 |
| 074 | BIZ-01 | TASK | P1 | TODO | M1-05 | R1-P1-04, R2-A-05 |
| 075 | BIZ-02 | TASK | P2 | TODO | M3-02, BIZ-01 | R1-P1-04, R2-A-05 |
| 076 | BIZ-03 | TASK | P1 | TODO | M3-04, M3-05A, M3-05B, M3-05C | R1-P1-03 |

# 六、盘查问题—任务—测试追溯矩阵

| 来源问题 | 问题摘要 | 整改任务 | 验收测试 | 覆盖状态 |
|---|---|---|---|---|
| R1-P0-01 | 统一入口公开 TP-001 必然失败路径 | M0-02, M1-04, M8-02 | M0-02-AT-01, M1-04-AT-01, M8-02-AT-01 | COVERED |
| R1-P0-02 | 缺少外部项目注册、装载与运行机制 | M4-01, M4-02, M4-03, M4-04, M8-05 | M4-01-AT-01, M4-02-AT-01, M4-03-AT-01, M4-04-AT-01, M8-05-AT-01 | COVERED |
| R1-P0-03 | Markdown 真源声明与运行控制源不一致 | M3-01, M3-02, M3-03, M3-04, M3-05, M3-06, M7-06, M8-03 | M3-01-AT-01, M3-02-AT-01, M3-03-AT-01, M3-04-AT-01, M3-05-AT-01, M3-06-AT-01, M7-06-AT-01, M8-03-AT-01 | COVERED |
| R1-P0-04 | 完整闭环在 L3 任务规划处中止 | M6-01, M6-02, M6-03, M6-04, M6-05, M6-06 | M6-01-AT-01, M6-02-AT-01, M6-03-AT-01, M6-04-AT-01, M6-05-AT-01, M6-06-AT-01 | COVERED |
| R1-P0-05 | 顶层成功状态掩盖候选、未验证和无发布权 | M1-05, M6-01, M8-08 | M1-05-AT-01, M6-01-AT-01, M8-08-AT-01 | COVERED |
| R1-P0-06 | 正式规则集不存在，生产模式不可运行 | M3-07, M8-08 | M3-07-AT-01, M8-08-AT-01 | COVERED |
| R1-P0-07 | 根级控制文档引用不存在文件 | M7-01, M7-03, M7-05 | M7-01-AT-01, M7-03-AT-01, M7-05-AT-01 | COVERED |
| R1-P1-01 | Python 打包表面成功但实际空包 | M5-01, M5-05, M5-07, M8-06, M8-07 | M5-01-AT-01, M5-05-AT-01, M5-07-AT-01, M8-06-AT-01, M8-07-AT-01 | COVERED |
| R1-P1-02 | 存在三条重叠执行路径 | M4-05, M5-03, M5-06 | M4-05-AT-01, M5-03-AT-01, M5-06-AT-01 | COVERED |
| R1-P1-03 | L2 六项能力未形成六种代码能力 | BIZ-03 | BIZ-03-AT-01 | COVERED |
| R1-P1-04 | L1 指标名称超过实际测量能力 | BIZ-01, BIZ-02 | BIZ-01-AT-01, BIZ-02-AT-01 | COVERED |
| R1-P1-05 | 测试覆盖偏向集成链 | M8-01, M8-02 | M8-01-AT-01, M8-02-AT-01 | COVERED |
| R1-P1-06 | 规则依赖元数据空置 | M7-02, M7-06 | M7-02-AT-01, M7-06-AT-01 | COVERED |
| R1-P1-07 | README 当前状态失真 | M7-01, M7-05 | M7-01-AT-01, M7-05-AT-01 | COVERED |
| R1-P1-08 | 正式正文仍为占位文件 | SCOPE-01, M4-01 | SCOPE-01-AT-01, M4-01-AT-01 | COVERED |
| R1-P2-01 | 发布包包含缓存与构建污染 | M8-07 | M8-07-AT-01 | COVERED |
| R1-P2-02 | 版本与依赖治理未成立 | M5-07 | M5-07-AT-01 | COVERED |
| R1-P2-03 | 存在疑似未使用模块和重复代码 | M5-06 | M5-06-AT-01 | COVERED |
| R1-P2-04 | 标识与状态命名不一致 | M1-05, M2-02, M7-04 | M1-05-AT-01, M2-02-AT-01, M7-04-AT-01 | COVERED |
| R1-P2-05 | 日志目录和运行记录治理不完整 | M2-06, M2-08 | M2-06-AT-01, M2-08-AT-01 | COVERED |
| R2-P0-01 | L2/L3 公开入口未执行 Schema 校验 | M1-01, M1-02, M1-03 | M1-01-AT-01, M1-02-AT-01, M1-03-AT-01 | COVERED |
| R2-P0-02 | 规则解析后关键规则未参与执行 | M3-03, M3-04, M3-05A, M3-05B, M3-05C, M3-06 | M3-03-AT-01, M3-04-AT-01, M3-05A-AT-01, M3-05B-AT-01, M3-05C-AT-01, M3-06-AT-01 | COVERED |
| R2-P0-03 | 运行编号在产生副作用后冲突并遗留 RUNNING | M2-01, M2-02, M2-04A, M2-04B, M2-04C | M2-01-AT-01, M2-02-AT-01, M2-04A-AT-01, M2-04B-AT-01, M2-04C-AT-01 | COVERED |
| R2-P0-04 | 独立阶段入口允许覆盖历史报告 | M2-02 | M2-02-AT-01 | COVERED |
| R2-P0-05 | 混合批次整批阻断导致合法任务丢失 | M2-07 | M2-07-AT-01 | COVERED |
| R2-C-01 | 异常处理不统一并泄漏裸 traceback | M1-03 | M1-03-AT-01 | COVERED |
| R2-C-02 | JSON Schema 约束过弱 | M1-02 | M1-02-AT-01 | COVERED |
| R2-C-03 | 统一入口缺少 target 专属参数契约 | M1-04, M8-02 | M1-04-AT-01, M8-02-AT-01 | COVERED |
| R2-C-04 | 通过修改 sys.path 维持导入 | M5-01 | M5-01-AT-01 | COVERED |
| R2-C-05 | 主流程函数职责高度耦合 | M5-02A, M5-02B, M5-02C | M5-02A-AT-01, M5-02B-AT-01, M5-02C-AT-01 | COVERED |
| R2-C-06 | 运行根目录创建存在并发竞态 | M2-03 | M2-03-AT-01 | COVERED |
| R2-C-07 | 子进程输出无上限写入清单 | M2-06, M5-04 | M2-06-AT-01, M5-04-AT-01 | COVERED |
| R2-C-08 | 输入与输出缺少资源上限 | M5-04 | M5-04-AT-01 | COVERED |
| R2-C-09 | 旧正文检测与新 L1 重复 | M4-05, M5-06 | M4-05-AT-01, M5-06-AT-01 | COVERED |
| R2-C-10 | 测试体系没有真实单元层 | M8-01 | M8-01-AT-01 | COVERED |
| R2-C-11 | 没有自动质量门禁 | M8-06A, M8-06B, M8-06C, M8-06D | M8-06A-AT-01, M8-06B-AT-01, M8-06C-AT-01, M8-06D-AT-01 | COVERED |
| R2-D-01 | Front Matter 依赖图为空壳 | M7-02 | M7-02-AT-01 | COVERED |
| R2-D-02 | 规则文档全部声明不允许作为真源 | M3-01, M7-06 | M3-01-AT-01, M7-06-AT-01 | COVERED |
| R2-D-03 | 核心索引引用不存在基线 | M7-01, M7-03 | M7-01-AT-01, M7-03-AT-01 | COVERED |
| R2-D-04 | 文档引用主要为不可校验裸文件名 | M7-03 | M7-03-AT-01 | COVERED |
| R2-D-05 | README 存在不可直接执行命令 | M7-05 | M7-05-AT-01 | COVERED |
| R2-D-06 | 规则解析依赖章节编号和标题 | M3-01, M7-04 | M3-01-AT-01, M7-04-AT-01 | COVERED |
| R2-D-07 | 文档章节编号冲突 | M7-04 | M7-04-AT-01 | COVERED |
| R2-D-08 | 文本编码、行尾和空白不统一 | M7-04 | M7-04-AT-01 | COVERED |
| R2-A-01 | 系统把解析规则误当执行规则 | M3-06, M8-03 | M3-06-AT-01, M8-03-AT-01 | COVERED |
| R2-A-02 | L3 状态机包含未实现未来阶段 | M6-01 | M6-01-AT-01 | COVERED |
| R2-A-03 | 技术、业务、人工与发布状态混合 | M1-05 | M1-05-AT-01 | COVERED |
| R2-A-04 | Project Harness 缺少身份与能力契约 | M4-01, M4-02 | M4-01-AT-01, M4-02-AT-01 | COVERED |
| R2-A-05 | L1 指标对段落与关键词高度敏感 | BIZ-01, BIZ-02 | BIZ-01-AT-01, BIZ-02-AT-01 | COVERED |
| R2-A-06 | L3 多个校验器职责重复 | M3-05A, M3-05B, M3-05C, M5-06 | M3-05A-AT-01, M3-05B-AT-01, M3-05C-AT-01, M5-06-AT-01 | COVERED |
| R2-A-07 | 未归属任务写入全局共享目录 | M2-09 | M2-09-AT-01 | COVERED |
| R2-P-01 | 没有完整 Preflight | M2-01 | M2-01-AT-01 | COVERED |
| R2-P-02 | 没有事务、补偿和恢复 | M2-04A, M2-04B, M2-04C, M6-06 | M2-04A-AT-01, M2-04B-AT-01, M2-04C-AT-01, M6-06-AT-01 | COVERED |
| R2-P-03 | 运行清单未登记全部实际产物 | M2-05 | M2-05-AT-01 | COVERED |
| R2-P-04 | 有日志协议但没有真实日志系统 | M2-06 | M2-06-AT-01 | COVERED |
| R2-P-05 | 业务阻断与技术失败均归并 FAILED | M1-05, M2-07 | M1-05-AT-01, M2-07-AT-01 | COVERED |
| R2-P-06 | 没有持续集成与发布验收 | M8-06A, M8-06B, M8-06C, M8-06D, M8-07 | M8-06A-AT-01, M8-06B-AT-01, M8-06C-AT-01, M8-06D-AT-01, M8-07-AT-01 | COVERED |
| R2-P-07 | 没有规则晋升与回退流程 | M3-07 | M3-07-AT-01 | COVERED |
| R2-P-08 | 没有运行记录保留和清理策略 | M2-08 | M2-08-AT-01 | COVERED |

所有来源问题当前均为 `COVERED`。后续若某任务被删除或 DEFERRED，必须同步更新该矩阵，且不得留下无承接问题。


# 七、详细任务与修改方向

# M0：基线冻结与复现样本

## M0-01 建立整改前基线清单

```yaml
task_id: "M0-01"
task_type: "TASK"
parent_task: null
milestone: "M0"
severity: "P0"
sequence: 1
status: "TODO"
depends_on: []
source_issues: ["GOV-M0-01"]
owner: "UNASSIGNED"
modules: ["00_工程总控/整改基线", "tests/regression"]
deliverables: ["M0-01 修改产物", "M0-01 自动化验收证据", "M0-01 变更与回滚说明"]
acceptance_tests: ["M0-01-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: false
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

保证后续修改可比较，不因目录迁移或测试变化丢失原始证据。

### 已确认问题

当前归档包含运行记录、缓存、重复实现和失效文档引用，但没有统一的“整改前基线”。

### 修改方向

新增只读基线文件，例如：

```text
00_工程总控/整改基线/BASELINE_2026-06-23.json
```

内容至少包括：

- Python/Markdown/JSON 文件数量；
- 关键入口路径；
- 当前测试数量和耗时；
- 当前规则文件哈希；
- 当前已知失败命令；
- 当前 37/37 通过命令；
- Git commit（若存在）或归档 SHA256；
- 不能确认的环境项。

### 涉及文件

- 新增 `00_工程总控/整改基线/`；
- 不修改业务代码。

### 验收标准

- 基线文件可由脚本重新生成；
- 同一归档重复生成结果一致；
- 基线明确区分“测试通过事实”和“已知故障事实”；
- 不把 `.pytest_cache`、`__pycache__` 计入有效工程产物。

### 禁止项

- 不得用新版本测试结果覆盖旧基线；
- 不得删除原始失败样本。

---

---

## M0-02 固化故障复现样本

```yaml
task_id: "M0-02"
task_type: "TASK"
parent_task: null
milestone: "M0"
severity: "P0"
sequence: 2
status: "TODO"
depends_on: ["M0-01"]
source_issues: ["R1-P0-01"]
owner: "UNASSIGNED"
modules: ["00_工程总控/整改基线", "tests/regression"]
deliverables: ["M0-02 修改产物", "M0-02 自动化验收证据", "M0-02 变更与回滚说明"]
acceptance_tests: ["M0-02-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: false
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

把两轮盘查中的口头/报告问题变成自动化回归样本。

### 修改方向

新增 `测试/回归样本/`，至少固化：

1. 统一入口调用 TP-001 参数失败；
2. L2 输入 `{}` 被判成功；
3. L3 输入 `{}` 被判成功；
4. 损坏 JSON 输出裸 traceback；
5. 64 字符 pipeline ID 留下 `RUNNING` 残骸；
6. 同一 L1 run-id 覆盖旧报告；
7. 合法项与越界项混合时，合法任务被跳过；
8. 修改 L2 Markdown 路由但行为不变；
9. L2 六能力禁止项解析为零；
10. wheel 构建成功但无法导入实际包。

先将这些测试标记为 `xfail(strict=True)`，整改后逐项转为普通通过测试。

### 验收标准

- 每个已确认问题至少有一个确定性测试；
- 测试名称直接表述行为，不使用“测试问题1”；
- 故障修复后删除 `xfail`，不得删除测试本身。

---

# 六、M1：输入契约、CLI 契约与错误语义

---


# SCOPE：项目范围与 Fixture 边界

## SCOPE-01 区分测试 Fixture 与真实创作项目边界

```yaml
task_id: "SCOPE-01"
task_type: "TASK"
parent_task: null
milestone: "SCOPE"
severity: "P0"
sequence: 3
status: "TODO"
depends_on: ["M0-01"]
source_issues: ["R1-P1-08"]
owner: "UNASSIGNED"
modules: ["Project Manifest", "fixtures", "项目状态文档"]
deliverables: ["SCOPE-01 修改产物", "SCOPE-01 自动化验收证据", "SCOPE-01 变更与回滚说明"]
acceptance_tests: ["SCOPE-01-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

防止占位正文和测试项目被误判为真实项目已经具备生产正文。

### 已确认问题

TP-001 的正式章节仍是占位文件。占位对测试夹具可以成立，但若项目类型、正文状态和生产资格未被显式区分，就会造成“测试目录存在”被误读为“正式正文已就绪”。

### 修改方向

Project Manifest 增加：

```yaml
project_kind: fixture | real
formal_source_state: placeholder | active | archived
production_eligibility: false
```

规则：

- `fixture` 永远不参与业务生产就绪统计；
- `formal_source_state=placeholder` 时不得进入发布或正文自动应用；
- 示例项目、回归项目和真实项目使用不同输出根；
- README 明确 fixture 只验证工程契约，不证明作品质量。

### 验收标准

- TP-001/TP-002 明确标记为 fixture；
- fixture 的成功运行不产生生产就绪结论；
- real 项目使用 placeholder 正文时，生产模式明确拒绝；
- 相关状态传播到顶层运行清单。

---


# M1：输入契约、CLI 契约与错误语义

## M1-01 建立统一输入校验服务

```yaml
task_id: "M1-01"
task_type: "TASK"
parent_task: null
milestone: "M1"
severity: "P0"
sequence: 4
status: "TODO"
depends_on: ["M0-02"]
source_issues: ["R2-P0-01"]
owner: "UNASSIGNED"
modules: ["公共组件", "schemas", "CLI", "L1/L2/L3/PIPELINE 入口"]
deliverables: ["M1-01 修改产物", "M1-01 自动化验收证据", "M1-01 变更与回滚说明"]
acceptance_tests: ["M1-01-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

L1/L2/L3/PIPELINE 通过同一个校验入口处理输入。

### 已确认问题

L2/L3 独立入口没有执行正式 Schema 校验，`{}` 会被解释为空任务并返回成功。

### 修改方向

在公共组件中建立：

```text
公共组件/输入校验.py
```

建议接口：

```python
validate_input(
    path: Path,
    schema_name: str,
    expected_schema_version: str,
    expected_lineage: LineageExpectation | None,
    semantic_validator: Callable | None,
) -> ValidatedDocument
```

必须按固定顺序执行：

```text
路径合法
→ 文件存在
→ 文件大小限制
→ UTF-8/UTF-8-SIG 解码
→ JSON 解析
→ 顶层类型
→ Schema 版本
→ JSON Schema
→ 血缘
→ 业务语义
```

### 涉及文件

- `公共组件/结构校验.py`；
- 新增 `公共组件/输入校验.py`；
- `L1运行入口.py`；
- `L2运行入口.py`；
- `L3运行入口.py`；
- `流水线运行.py`。

### 验收标准

以下输入均不得返回 0：

- `{}`；
- `[]`；
- 损坏 JSON；
- 缺 `schema_version`；
- 未知版本；
- 字段类型错误；
- 输入哈希不匹配；
- pipeline/stage 血缘不匹配。

所有入口必须调用同一个公共函数，禁止复制校验逻辑。

---

---

## M1-02 收紧六份核心 JSON Schema

```yaml
task_id: "M1-02"
task_type: "TASK"
parent_task: null
milestone: "M1"
severity: "P0"
sequence: 5
status: "TODO"
depends_on: ["M1-01"]
source_issues: ["R2-C-02", "R2-P0-01"]
owner: "UNASSIGNED"
modules: ["公共组件", "schemas", "CLI", "L1/L2/L3/PIPELINE 入口"]
deliverables: ["M1-02 修改产物", "M1-02 自动化验收证据", "M1-02 变更与回滚说明"]
acceptance_tests: ["M1-02-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

Schema 能真实拦截结构畸形，而不是只检查顶层字段存在。

### 修改方向

重点修改：

- `失败包结构.json`；
- `第一层报告结构.json`；
- `第二层报告结构.json`；
- `第三层任务包结构.json`；
- `流水线清单结构.json`；
- `产物记录结构.json`。

要求：

1. `schema_version` 使用 `const` 或受控 enum；
2. `status`、`final_status`、`stage` 使用 enum；
3. `created_at` 使用 `format: date-time`；
4. 关键对象 `additionalProperties: false`；
5. 所有数组 item 使用 `$defs` 定义；
6. 数量、字符串长度、路径长度设置上限；
7. 哈希使用 `^[a-f0-9]{64}$`；
8. run-id/stage-id 使用统一 pattern；
9. 空数组是否允许必须按业务场景明确；
10. 候选模式、验证状态、发布权限不得缺省。

### 验收标准

- 每个 Schema 至少有一组合法样本和十组非法样本；
- Schema 测试不启动子进程；
- 未知字段默认失败，必要扩展字段放入明确的 `extensions` 对象。

---

---

## M1-03 建立统一错误信封与退出码映射

```yaml
task_id: "M1-03"
task_type: "TASK"
parent_task: null
milestone: "M1"
severity: "P0"
sequence: 6
status: "TODO"
depends_on: ["M1-01"]
source_issues: ["R2-C-01", "R2-P0-01"]
owner: "UNASSIGNED"
modules: ["公共组件", "schemas", "CLI", "L1/L2/L3/PIPELINE 入口"]
deliverables: ["M1-03 修改产物", "M1-03 自动化验收证据", "M1-03 变更与回滚说明"]
acceptance_tests: ["M1-03-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

用户输入错误不再输出裸 traceback，不再由不同 argparse/异常类型随机决定格式。

### 修改方向

统一错误输出结构：

```json
{
  "ok": false,
  "error": {
    "code": "INPUT_SCHEMA_INVALID",
    "message": "...",
    "stage": "L2",
    "run_id": "...",
    "path": "...",
    "details": {},
    "retryable": false
  },
  "exit_code": 21
}
```

异常分层：

- 输入错误；
- Schema 错误；
- 规则错误；
- 血缘错误；
- 权限/边界错误；
- 阶段业务拒绝；
- 超时；
- 内部错误。

仅在 `--debug` 下输出 traceback，默认 stderr 只输出错误信封。

### 涉及文件

- `公共组件/工程异常.py`；
- `公共组件/退出码.py`；
- 各入口 `main()`；
- 统一入口。

### 验收标准

- 损坏 JSON 不出现 `Traceback`；
- 相同错误在独立入口与 PIPELINE 中 code、exit_code 一致；
- 内部错误记录到日志，但终端只显示 request/run correlation ID。

---

---

## M1-04 重构统一入口为子命令 CLI

```yaml
task_id: "M1-04"
task_type: "TASK"
parent_task: null
milestone: "M1"
severity: "P0"
sequence: 7
status: "TODO"
depends_on: ["M1-03"]
source_issues: ["R1-P0-01", "R2-C-03"]
owner: "UNASSIGNED"
modules: ["公共组件", "schemas", "CLI", "L1/L2/L3/PIPELINE 入口"]
deliverables: ["M1-04 修改产物", "M1-04 自动化验收证据", "M1-04 变更与回滚说明"]
acceptance_tests: ["M1-04-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

消除 `parse_known_args` 和跨 target 参数透传。

### 已确认问题

统一入口无条件注入 `--standard-mode`，导致 TP-001 确定性失败；`--chapter`、`--project` 也可能传给不支持的入口。

### 修改方向

将接口改为：

```text
xcue pipeline run ...
xcue l1 run ...
xcue l2 run ...
xcue l3 run ...
xcue project validate ...
xcue rules validate ...
xcue run inspect ...
```

过渡期可保留旧 `--target`，但只能作为兼容适配器，并输出弃用警告；不得再透传未知参数。

### 涉及文件

- `统一运行入口.py`；
- 新增 `cli/` 或临时 `公共组件/命令定义.py`；
- TP-001 入口仅作为测试项目内部命令，不应是统一引擎 target。

### 验收标准

- 每个子命令 `--help` 独立完整；
- 未支持参数由统一错误信封返回；
- 所有 README 命令进入 CLI 冒烟测试；
- `TP-001` 不再因强制参数失败。

---

---

## M1-05 修正状态模型，消除假通过

```yaml
task_id: "M1-05"
task_type: "TASK"
parent_task: null
milestone: "M1"
severity: "P0"
sequence: 8
status: "TODO"
depends_on: ["M1-01", "M1-02", "M1-03"]
source_issues: ["R1-P0-05", "R1-P2-04", "R2-A-03", "R2-P-05"]
owner: "UNASSIGNED"
modules: ["公共组件", "schemas", "CLI", "L1/L2/L3/PIPELINE 入口"]
deliverables: ["M1-05 修改产物", "M1-05 自动化验收证据", "M1-05 变更与回滚说明"]
acceptance_tests: ["M1-05-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

状态可被机器准确解释，外部调用者读取单一字段时不会误判发布或质量结论。

### 修改方向

拆分至少五个维度：

```json
{
  "execution_status": "COMPLETED",
  "screening_result": "NO_HEURISTIC_RISK_FOUND",
  "validation_status": "UNVALIDATED",
  "workflow_status": "HUMAN_REVIEW_REQUIRED",
  "publication_authority": "NONE"
}
```

候选模式禁止返回裸 `PASS`。空 L2/L3 使用：

- `NO_ITEMS`；
- `NOT_APPLICABLE`；
- `SKIPPED_BY_POLICY`。

不得用 `COMPLETED` 表示业务质量通过。

### 涉及文件

- `公共组件/系统状态.py`；
- `公共组件/运行状态.py`；
- L1/L2/L3 报告模型；
- `_最终判定()`；
- 所有 Schema 和测试。

### 验收标准

- 候选模式所有最终状态都含 candidate/heuristic 语义；
- `publication_authority != GRANTED` 时不能出现“发布通过”；
- `UNVALIDATED` 必须传播到顶层清单；
- 空任务不再标为普通完成。

---

# 七、M2：运行事务、不可变证据与部分成功

---


# M2：运行事务、不可变证据与部分成功

## M2-01 建立完整 Preflight，任何副作用前完成检查

```yaml
task_id: "M2-01"
task_type: "TASK"
parent_task: null
milestone: "M2"
severity: "P0"
sequence: 9
status: "TODO"
depends_on: ["M1-01", "M1-02", "M1-05"]
source_issues: ["R2-P-01", "R2-P0-03"]
owner: "UNASSIGNED"
modules: ["pipeline", "运行记录", "Artifact Registry", "logs", "recovery"]
deliverables: ["M2-01 修改产物", "M2-01 自动化验收证据", "M2-01 变更与回滚说明"]
acceptance_tests: ["M2-01-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

避免先创建运行目录、复制正文、写 `RUNNING` 后才发现 ID 或规则不合法。

### 修改方向

新增 `PreflightResult`，在创建 run root 前验证：

- project manifest；
- pipeline run ID；
- stage 标识；
- output path；
- 输入文件；
- Schema；
- 规则集；
- 规则解析；
- Project Harness；
- 磁盘空间下限；
- 同名运行冲突；
- 写权限；
- 资源上限。

阶段 ID 不再使用 `pipeline_id + '-L1'` 表示层级。改为结构字段：

```json
{
  "pipeline_run_id": "...",
  "stage": "L1",
  "attempt": 1
}
```

### 验收标准

- 64 字符合法 pipeline ID 不会在阶段派生时失败；
- Preflight 失败时 `run_root_created=false`；
- 不产生正文快照、空目录和 `RUNNING` 清单；
- 所有预检错误使用统一信封。

---

---

## M2-02 建立不可变 Run/Stage/Attempt 身份

```yaml
task_id: "M2-02"
task_type: "TASK"
parent_task: null
milestone: "M2"
severity: "P0"
sequence: 10
status: "TODO"
depends_on: ["M2-01"]
source_issues: ["R1-P2-04", "R2-P0-03", "R2-P0-04"]
owner: "UNASSIGNED"
modules: ["pipeline", "运行记录", "Artifact Registry", "logs", "recovery"]
deliverables: ["M2-02 修改产物", "M2-02 自动化验收证据", "M2-02 变更与回滚说明"]
acceptance_tests: ["M2-02-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

禁止独立 L1/L2/L3 静默覆盖历史。

### 修改方向

目录建议：

```text
运行记录/<pipeline_run_id>/
  manifest.json
  stages/L1/attempt-001/
  stages/L2/attempt-001/
  stages/L3/attempt-001/
```

规则：

- `pipeline_run_id` 一经创建不可覆盖；
- 相同阶段重试必须创建新 attempt；
- attempt 保存 `parent_attempt` 和 `retry_reason`；
- 正式模式不提供无审计 `--overwrite`；
- 候选模式若提供 overwrite，必须先归档原哈希和操作者信息。

### 涉及文件

- `安全路径.py`；
- `流水线运行.py`；
- L1/L2/L3 输出路径逻辑；
- 运行清单 Schema。

### 验收标准

- 重复 run-id 默认返回 `RUN_ID_CONFLICT`；
- 旧文件哈希保持不变；
- `retry` 生成 attempt-002；
- manifest 能追溯父子 attempt。

---

---

## M2-03 增加运行锁和并发安全

```yaml
task_id: "M2-03"
task_type: "TASK"
parent_task: null
milestone: "M2"
severity: "P1"
sequence: 11
status: "TODO"
depends_on: ["M2-02"]
source_issues: ["R2-C-06"]
owner: "UNASSIGNED"
modules: ["pipeline", "运行记录", "Artifact Registry", "logs", "recovery"]
deliverables: ["M2-03 修改产物", "M2-03 自动化验收证据", "M2-03 变更与回滚说明"]
acceptance_tests: ["M2-03-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

两个进程不能同时写同一 run root。

### 修改方向

使用本地原子占位：

- `mkdir(exist_ok=False)` 创建运行根；或
- `O_CREAT | O_EXCL` 创建 `.run.lock`；
- 锁中写 PID、启动时间、主机标识；
- 正常结束删除活动锁，但保留运行状态；
- stale lock 只能通过显式恢复命令处理。

### 验收标准

- 并发启动相同 run-id 时仅一个成功；
- 另一个返回 `RUN_LOCKED`；
- 不出现交叉写入；
- 进程异常退出后可被恢复管理器识别。

---

---

## M2-04 建立中断、失败和恢复状态

```yaml
task_id: "M2-04"
task_type: "EPIC"
parent_task: null
milestone: "M2"
severity: "P0"
sequence: 12
status: "TODO"
depends_on: ["M2-02"]
source_issues: ["R2-P-02", "R2-P0-03"]
owner: "UNASSIGNED"
modules: ["pipeline", "运行记录", "Artifact Registry", "logs", "recovery"]
deliverables: ["M2-04 修改产物", "M2-04 自动化验收证据", "M2-04 变更与回滚说明"]
acceptance_tests: ["M2-04-AT-01"]
prohibitions: ["不得直接领取 Epic；只能领取其子任务", "不得绕过子任务验收关闭 Epic"]
rollback_required: true
blocks_release: true
execution_policy: "CHILD_TASKS_ONLY"
```

### 任务目标

不再留下永久 `RUNNING` 残骸。

> 本项为 Epic，不可直接交给 Codex。只有全部子任务均为 `ACCEPTED`，本 Epic 才可转为 `READY_FOR_REVIEW`。

### 修改方向

引入状态：

```text
PREFLIGHT_FAILED
RUNNING
STAGE_FAILED
ABORTED
TIMED_OUT
INTERRUPTED
RECOVERY_REQUIRED
COMPLETED
```

每次阶段开始前写 checkpoint；阶段完成后原子提交。新增：

```text
xcue run recover <run-id>
xcue run retry <run-id> --stage L2
xcue run inspect <run-id>
```

恢复只允许：

- 从最近完整 checkpoint 继续；或
- 创建新 attempt；
- 不在原目录中继续覆盖半成品。

### 验收标准

- 模拟 SIGTERM/超时后，运行状态不是永久 `RUNNING`；
- inspect 能指出最后完整阶段；
- retry 不修改旧 attempt；
- 恢复行为有自动化测试。

---

---

## M2-04A 建立中断状态与阶段 Checkpoint

```yaml
task_id: "M2-04A"
task_type: "SUBTASK"
parent_task: "M2-04"
milestone: "M2"
severity: "P0"
sequence: 13
status: "TODO"
depends_on: ["M2-02"]
source_issues: ["R2-P-02", "R2-P0-03"]
owner: "UNASSIGNED"
modules: ["pipeline", "运行记录", "Artifact Registry", "logs", "recovery"]
deliverables: ["M2-04A 修改产物", "M2-04A 自动化验收证据", "M2-04A 变更与回滚说明"]
acceptance_tests: ["M2-04A-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

保证进程中断或超时后，运行状态可被确定识别。

### 修改方向

定义 `PREFLIGHT_FAILED/RUNNING/STAGE_FAILED/ABORTED/TIMED_OUT/INTERRUPTED/RECOVERY_REQUIRED/COMPLETED`，阶段开始前写入 checkpoint，完成后原子提交。

### 验收标准

- SIGTERM、KeyboardInterrupt、超时均产生确定状态；
- 不留下无时间戳、无最后阶段信息的永久 `RUNNING`；
- checkpoint 本身进入 Artifact Registry。

---

## M2-04B 实现 Run Inspect 与 Stale 状态检测

```yaml
task_id: "M2-04B"
task_type: "SUBTASK"
parent_task: "M2-04"
milestone: "M2"
severity: "P0"
sequence: 14
status: "TODO"
depends_on: ["M2-04A"]
source_issues: ["R2-P-02", "R2-P0-03"]
owner: "UNASSIGNED"
modules: ["pipeline", "运行记录", "Artifact Registry", "logs", "recovery"]
deliverables: ["M2-04B 修改产物", "M2-04B 自动化验收证据", "M2-04B 变更与回滚说明"]
acceptance_tests: ["M2-04B-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

提供只读诊断入口，判断运行最后完整阶段和是否需要恢复。

### 修改方向

实现 `xcue run inspect <run-id>`，读取 manifest、锁、checkpoint 和 artifact registry，不修改运行内容；定义 stale lock 判定策略。

### 验收标准

- inspect 可指出最后完整 stage/attempt；
- stale 判定包含 PID、时间和主机证据；
- inspect 对损坏清单返回结构化错误，不自动修复。

---

## M2-04C 实现 Retry 与 Recover 新 Attempt 机制

```yaml
task_id: "M2-04C"
task_type: "SUBTASK"
parent_task: "M2-04"
milestone: "M2"
severity: "P0"
sequence: 15
status: "TODO"
depends_on: ["M2-04A", "M2-04B"]
source_issues: ["R2-P-02", "R2-P0-03"]
owner: "UNASSIGNED"
modules: ["pipeline", "运行记录", "Artifact Registry", "logs", "recovery"]
deliverables: ["M2-04C 修改产物", "M2-04C 自动化验收证据", "M2-04C 变更与回滚说明"]
acceptance_tests: ["M2-04C-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

恢复和重试不得覆盖旧 attempt 或在半成品目录继续写入。

### 修改方向

实现 `xcue run retry` 与 `xcue run recover`。任何继续执行都创建新 attempt，记录 `parent_attempt`、`retry_reason` 和起始 checkpoint。

### 验收标准

- retry 生成 attempt-002；
- recover 不修改 attempt-001；
- 无完整 checkpoint 时拒绝 recover；
- 恢复失败有独立状态和错误信封。

---

## M2-05 建立 Artifact Registry，覆盖全部产物

```yaml
task_id: "M2-05"
task_type: "TASK"
parent_task: null
milestone: "M2"
severity: "P0"
sequence: 16
status: "TODO"
depends_on: ["M2-02"]
source_issues: ["R2-P-03"]
owner: "UNASSIGNED"
modules: ["pipeline", "运行记录", "Artifact Registry", "logs", "recovery"]
deliverables: ["M2-05 修改产物", "M2-05 自动化验收证据", "M2-05 变更与回滚说明"]
acceptance_tests: ["M2-05-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

顶层清单能够发现分项 Markdown 任务被删除或修改。

### 修改方向

每个实际生成文件都注册：

```json
{
  "artifact_id": "...",
  "kind": "l3_task_markdown",
  "path": "...",
  "sha256": "...",
  "size_bytes": 123,
  "producer_stage": "L3",
  "producer_attempt": 1,
  "input_artifact_ids": ["..."],
  "created_at": "...",
  "retention_class": "audit"
}
```

不允许仅登记汇总 JSON 而遗漏分项任务、diff、日志、快照和回填文件。

### 涉及文件

- 接入现有 `公共组件/产物血缘.py`，或删除后重写；
- `流水线运行.py`；
- L3 输出模块；
- 清单 Schema。

### 验收标准

- 删除任一登记产物后，完整性检查失败；
- 修改任一文件后哈希校验失败；
- 所有 L3 Markdown 任务均可从 registry 枚举；
- 无未登记的正式运行产物。

---

---

## M2-06 日志与清单分离

```yaml
task_id: "M2-06"
task_type: "TASK"
parent_task: null
milestone: "M2"
severity: "P1"
sequence: 17
status: "TODO"
depends_on: ["M2-05"]
source_issues: ["R1-P2-05", "R2-C-07", "R2-P-04"]
owner: "UNASSIGNED"
modules: ["pipeline", "运行记录", "Artifact Registry", "logs", "recovery"]
deliverables: ["M2-06 修改产物", "M2-06 自动化验收证据", "M2-06 变更与回滚说明"]
acceptance_tests: ["M2-06-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

避免完整 stdout/stderr 无上限嵌入清单。

### 修改方向

每个阶段独立日志：

```text
logs/L1-attempt-001.stdout.log
logs/L1-attempt-001.stderr.log
```

清单仅记录：

- 路径；
- 哈希；
- 字节数；
- 最后 N 行；
- 是否截断；
- 是否含敏感内容。

设置：

- 单日志上限；
- 轮转/截断；
- 正文片段脱敏策略；
- debug 和 normal 两种级别。

### 验收标准

- 子进程输出超限时不会耗尽内存；
- 单个 manifest 序列化后不得超过 1 MiB；超出时必须把正文日志和大字段拆为独立 artifact；
- 错误仍可通过 tail 定位；
- 完整日志进入 Artifact Registry。

---

---

## M2-07 将整批状态改为 item-level 状态

```yaml
task_id: "M2-07"
task_type: "TASK"
parent_task: null
milestone: "M2"
severity: "P0"
sequence: 18
status: "TODO"
depends_on: ["M1-02", "M1-05"]
source_issues: ["R2-P-05", "R2-P0-05"]
owner: "UNASSIGNED"
modules: ["pipeline", "运行记录", "Artifact Registry", "logs", "recovery"]
deliverables: ["M2-07 修改产物", "M2-07 自动化验收证据", "M2-07 变更与回滚说明"]
acceptance_tests: ["M2-07-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

合法任务、待重路由项、外部阻断项分离。

### 修改方向

L2 输出至少分为：

```json
{
  "ready_for_l3": [],
  "needs_reroute": [],
  "blocked_external": [],
  "invalid_items": []
}
```

每项必须有：

- `item_id`；
- 来源失败项；
- 当前状态；
- 目标模块；
- 阻断原因；
- 是否可重试；
- 下一步。

顶层聚合状态：

```text
ALL_COMPLETED
PARTIAL_SUCCESS_WITH_BLOCKED_ITEMS
ALL_BLOCKED
NO_ITEMS
FAILED_SYSTEM
```

L3 只消费 `ready_for_l3`。

### 验收标准

- 混合批次中的合法项继续进入 L3；
- 越界项单独记录；
- 单项状态可追溯到 L1 原失败项；
- 一个业务项失败不改变其他项的产物。

---

# 八、M3：唯一规则控制面

---

## M2-08 建立运行记录保留、归档与安全清理策略

```yaml
task_id: "M2-08"
task_type: "TASK"
parent_task: null
milestone: "M2"
severity: "P1"
sequence: 19
status: "TODO"
depends_on: ["M2-05", "M2-06"]
source_issues: ["R1-P2-05", "R2-P-08"]
owner: "UNASSIGNED"
modules: ["pipeline", "运行记录", "Artifact Registry", "logs", "recovery"]
deliverables: ["M2-08 修改产物", "M2-08 自动化验收证据", "M2-08 变更与回滚说明"]
acceptance_tests: ["M2-08-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

让运行记录可控增长，同时保证审计证据不会被误删。

### 已确认问题

现有运行记录没有正式保留期限、归档等级、安全清理命令和引用保护。长期运行会造成目录膨胀；直接手工删除又会破坏 attempt、产物血缘和验收证据。

### 修改方向

建立 `retention policy`：

- `audit`：默认长期保留，不允许自动清理；
- `release`：随发布版本保留；
- `temporary`：达到期限后允许清理；
- `cache`：可重建，允许优先清理。

新增只读预览与显式执行命令：

```text
xcue run cleanup --dry-run
xcue run cleanup --apply --policy temporary
```

清理前必须检查：

- 运行是否仍为活动状态；
- 产物是否被其他 run/attempt 引用；
- 是否属于规则冻结、发布验收或回滚证据；
- 是否存在法律/人工指定保留标记；
- 删除清单是否完整登记。

### 验收标准

- dry-run 与 apply 输出相同候选清单；
- 活动运行、审计产物和被引用产物不得删除；
- 每次清理生成不可覆盖的删除清单与哈希；
- 清理后 Artifact Registry 完整性检查通过；
- 可通过备份样本完成一次恢复演练。

---

## M2-09 取消全局未归属目录并建立检疫隔离机制

```yaml
task_id: "M2-09"
task_type: "TASK"
parent_task: null
milestone: "M2"
severity: "P0"
sequence: 20
status: "TODO"
depends_on: ["M2-02"]
source_issues: ["R2-A-07"]
owner: "UNASSIGNED"
modules: ["pipeline", "运行记录", "Artifact Registry", "logs", "recovery"]
deliverables: ["M2-09 修改产物", "M2-09 自动化验收证据", "M2-09 变更与回滚说明"]
acceptance_tests: ["M2-09-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

禁止缺少运行归属的任务进入正式流水线或被其他运行误消费。

### 已确认问题

无法确定 `project_id`、`pipeline_run_id` 或来源阶段时，任务会落入共享“未归属运行”目录。该目录破坏项目隔离和运行血缘，可能被后续流程误认为可继续任务。

### 修改方向

正式链路采用“拒绝优先”：

- 缺少 `pipeline_run_id`：拒绝；
- 缺少 `project_ref`：拒绝；
- 来源 artifact 不存在：拒绝；
- 仅调试模式允许写入独立 `quarantine/`；
- quarantine 产物不得进入正式 Artifact Registry 的可消费集合；
- 从 quarantine 重新绑定必须生成新的审计事件，不得原地改写。

### 验收标准

- 正式模式不存在全局“未归属运行”输出；
- 缺归属输入返回 `LINEAGE_REQUIRED`；
- quarantine 文件不会被 L2/L3 自动发现或消费；
- 人工重新绑定生成新 artifact 与 parent reference。

---


# M3：唯一规则控制面

## M3-01 明确规则真源战略并修改声明

```yaml
task_id: "M3-01"
task_type: "TASK"
parent_task: null
milestone: "M3"
severity: "P0"
sequence: 21
status: "TODO"
depends_on: ["M1-01", "M1-02", "M1-03", "M1-05", "M2-01", "M2-02", "M2-05", "M2-07"]
source_issues: ["R1-P0-03", "R2-D-02", "R2-D-06"]
owner: "UNASSIGNED"
modules: ["rules", "rule loader", "rule executor", "rule evidence"]
deliverables: ["M3-01 修改产物", "M3-01 自动化验收证据", "M3-01 变更与回滚说明"]
acceptance_tests: ["M3-01-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

终止“Markdown 宣称真源、Python 决定行为”的双真源。

### 推荐方向

采用：

```text
YAML/JSON 结构化规则 = 运行真源
Markdown = 解释、设计依据与示例
Python = 通用执行器
```

不建议继续从自由 Markdown 章节标题和代码块中解析正式规则。

### 规则文件建议

```text
rules/
  l1/gates.yaml
  l1/thresholds.yaml
  l15/routes.yaml
  l2/capabilities.yaml
  l2/prohibitions.yaml
  l3/permissions.yaml
  l3/execution_order.yaml
  l3/prohibitions.yaml
```

每个规则包含：

- rule_id；
- version；
- status；
- effective_from；
- inputs；
- condition；
- action；
- severity；
- runtime_enforced；
- tests；
- supersedes；
- rationale_doc。

### 验收标准

- 根文档不再笼统称所有 Markdown 为运行真源；
- 规则加载器只加载结构化文件；
- Markdown 修改不会暗中改变行为；
- 结构化规则变化必须引起行为测试变化。

---

---

## M3-02 先迁移 L1 阈值、正则和状态映射

```yaml
task_id: "M3-02"
task_type: "TASK"
parent_task: null
milestone: "M3"
severity: "P0"
sequence: 22
status: "TODO"
depends_on: ["M3-01"]
source_issues: ["R1-P0-03"]
owner: "UNASSIGNED"
modules: ["rules", "rule loader", "rule executor", "rule evidence"]
deliverables: ["M3-02 修改产物", "M3-02 自动化验收证据", "M3-02 变更与回滚说明"]
acceptance_tests: ["M3-02-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

选择最小范围验证规则控制面，不一次迁移全部规则。

### 修改方向

从以下 Python 中移出：

- E/V/C/I 阈值；
- 关键词/正则；
- 门槛比较规则；
- 失败类型映射；
- 状态转换。

执行器只接收 `L1RuleSet` 对象，不得保留业务 fallback。

### 验收标准

- 将阈值从 3 改为 4，固定样本结果发生预期变化；
- 删除一个规则，系统明确报告规则缺失，不自动使用 Python 默认值；
- 每个 L1 结果记录命中的 rule_id 和 rule version。

---

---

## M3-03 迁移 L1.5/L2 路由并删除 fallback 优先覆盖

```yaml
task_id: "M3-03"
task_type: "TASK"
parent_task: null
milestone: "M3"
severity: "P0"
sequence: 23
status: "TODO"
depends_on: ["M3-01"]
source_issues: ["R1-P0-03", "R2-P0-02"]
owner: "UNASSIGNED"
modules: ["rules", "rule loader", "rule executor", "rule evidence"]
deliverables: ["M3-03 修改产物", "M3-03 自动化验收证据", "M3-03 变更与回滚说明"]
acceptance_tests: ["M3-03-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

文档/结构化路由真正决定 L2 模块归属。

### 已确认问题

`FALLBACK_FAILURE_TO_MODULE` 优先于文档解析路由。

### 修改方向

- 将路由迁移到 `routes.yaml`；
- 删除业务级 `FALLBACK_FAILURE_TO_MODULE`；
- 未匹配路由必须进入 `ROUTE_NOT_FOUND` 或人工复核；
- 通用代码 fallback 只能处理技术异常，不能替代业务路由。

### 验收标准

- 修改 route 后运行结果同步变化；
- Python 代码扫描不存在同义业务路由表；
- 每项输出记录 `route_rule_id`；
- 冲突路由在加载阶段失败。

---

---

## M3-04 结构化 L2 禁止项

```yaml
task_id: "M3-04"
task_type: "TASK"
parent_task: null
milestone: "M3"
severity: "P0"
sequence: 24
status: "TODO"
depends_on: ["M3-01"]
source_issues: ["R1-P0-03", "R2-P0-02"]
owner: "UNASSIGNED"
modules: ["rules", "rule loader", "rule executor", "rule evidence"]
deliverables: ["M3-04 修改产物", "M3-04 自动化验收证据", "M3-04 变更与回滚说明"]
acceptance_tests: ["M3-04-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

修复六个能力禁止项解析为零的问题。

### 修改方向

禁止项不再依赖“第 15/16 节”标题和 Markdown 列表。统一规则结构：

```yaml
- rule_id: L2-PROHIBIT-001
  capability: L2-01
  operation: DELETE_FORMAL_TEXT
  severity: BLOCK
  condition: ...
  message: ...
```

L2 运行前必须输出：

- loaded prohibition count；
- enforced prohibition count；
- matched prohibition IDs。

### 验收标准

- 六个能力至少各有可验证禁止项；
- 删除禁止项会改变对应行为测试；
- 禁止项加载为零时，不得静默运行正式模式。

---

---

## M3-05 让 L3 权限、执行顺序和禁止项真实控制执行

```yaml
task_id: "M3-05"
task_type: "EPIC"
parent_task: null
milestone: "M3"
severity: "P0"
sequence: 25
status: "TODO"
depends_on: ["M3-01"]
source_issues: ["R1-P0-03", "R2-A-06", "R2-P0-02"]
owner: "UNASSIGNED"
modules: ["rules", "rule loader", "rule executor", "rule evidence"]
deliverables: ["M3-05 修改产物", "M3-05 自动化验收证据", "M3-05 变更与回滚说明"]
acceptance_tests: ["M3-05-AT-01"]
prohibitions: ["不得直接领取 Epic；只能领取其子任务", "不得绕过子任务验收关闭 Epic"]
rollback_required: true
blocks_release: true
execution_policy: "CHILD_TASKS_ONLY"
```

### 任务目标

解析对象从报告装饰升级为执行控制面。

> 本项为 Epic，不可直接交给 Codex。只有全部子任务均为 `ACCEPTED`，本 Epic 才可转为 `READY_FOR_REVIEW`。

### 修改方向

1. `execution_order.yaml` 决定校验器顺序；
2. `permissions.yaml` 决定可读/可写路径和操作；
3. `prohibitions.yaml` 决定阻断行为；
4. 校验器注册表只负责实现，不负责业务顺序；
5. 未注册 rule handler 在加载阶段失败。

### 验收标准

- 调整执行顺序后，调用顺序测试变化；
- 删除某权限后，原可执行任务被规范阻断；
- Python 中删除 `AUTH_SOURCE_PARTS` 等业务硬编码；
- 报告记录每条 enforced rule 的结果。

---

---

## M3-05A 让 L3 权限规则控制可读写边界

```yaml
task_id: "M3-05A"
task_type: "SUBTASK"
parent_task: "M3-05"
milestone: "M3"
severity: "P0"
sequence: 26
status: "TODO"
depends_on: ["M3-01"]
source_issues: ["R2-A-06", "R2-P0-02"]
owner: "UNASSIGNED"
modules: ["rules", "rule loader", "rule executor", "rule evidence"]
deliverables: ["M3-05A 修改产物", "M3-05A 自动化验收证据", "M3-05A 变更与回滚说明"]
acceptance_tests: ["M3-05A-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

权限规则不再只是报告摘要，而是所有 handler 的强制前置条件。

### 修改方向

建立统一 PermissionEvaluator；所有任务在读取、写入、删除、移动前均请求授权。权限从结构化规则和项目清单合成。

### 验收标准

- 删除写权限后原任务被阻断；
- handler 不能绕过 evaluator 直接写文件；
- 每次权限决策记录 rule_id、target 和结果。

---

## M3-05B 让 L3 执行顺序规则控制校验器调用

```yaml
task_id: "M3-05B"
task_type: "SUBTASK"
parent_task: "M3-05"
milestone: "M3"
severity: "P0"
sequence: 27
status: "TODO"
depends_on: ["M3-01"]
source_issues: ["R2-A-06", "R2-P0-02"]
owner: "UNASSIGNED"
modules: ["rules", "rule loader", "rule executor", "rule evidence"]
deliverables: ["M3-05B 修改产物", "M3-05B 自动化验收证据", "M3-05B 变更与回滚说明"]
acceptance_tests: ["M3-05B-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

执行顺序由规则集决定，注册表不再暗含业务顺序。

### 修改方向

校验器注册表只提供实现映射；`execution_order.yaml` 提供阶段、前后依赖和失败策略。

### 验收标准

- 修改顺序规则后调用记录按预期变化；
- 循环依赖在加载时失败；
- 未注册 handler 不得跳过。

---

## M3-05C 让 L3 禁止项控制阻断与路由

```yaml
task_id: "M3-05C"
task_type: "SUBTASK"
parent_task: "M3-05"
milestone: "M3"
severity: "P0"
sequence: 28
status: "TODO"
depends_on: ["M3-01"]
source_issues: ["R2-A-06", "R2-P0-02"]
owner: "UNASSIGNED"
modules: ["rules", "rule loader", "rule executor", "rule evidence"]
deliverables: ["M3-05C 修改产物", "M3-05C 自动化验收证据", "M3-05C 变更与回滚说明"]
acceptance_tests: ["M3-05C-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

禁止项必须在操作执行前产生可追溯的阻断决定。

### 修改方向

所有禁止项结构化，并在任务授权之后、实际操作之前执行。禁止项只产生规范阻断或重路由，不直接伪造系统错误。

### 验收标准

- 删除或修改禁止项会改变对应行为测试；
- 命中禁止项记录 rule_id；
- 正式模式禁止项加载为零时拒绝运行。

---

## M3-06 增加 parsed/enforced/observed 三层规则证据

```yaml
task_id: "M3-06"
task_type: "TASK"
parent_task: null
milestone: "M3"
severity: "P1"
sequence: 29
status: "TODO"
depends_on: ["M3-02", "M3-03", "M3-04", "M3-05A", "M3-05B", "M3-05C"]
source_issues: ["R1-P0-03", "R2-A-01", "R2-P0-02"]
owner: "UNASSIGNED"
modules: ["rules", "rule loader", "rule executor", "rule evidence"]
deliverables: ["M3-06 修改产物", "M3-06 自动化验收证据", "M3-06 变更与回滚说明"]
acceptance_tests: ["M3-06-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

避免“解析到了”被误认为“执行了”。

### 修改方向

每次运行记录：

```json
{
  "parsed_rules": [...],
  "enforced_rules": [...],
  "matched_rules": [...],
  "skipped_rules": [{"id": "...", "reason": "..."}]
}
```

规则集总哈希之外，还要记录单规则版本和哈希。

### 验收标准

- `enforced_rules` 必须是 `parsed_rules` 子集；
- runtime_enforced 规则若未进入执行器，运行失败；
- 报告可回答“本次判定由哪条规则产生”。

---

---

## M3-07 建立规则晋升、冻结和回退流程

```yaml
task_id: "M3-07"
task_type: "TASK"
parent_task: null
milestone: "M3"
severity: "P1"
sequence: 30
status: "TODO"
depends_on: ["M3-06"]
source_issues: ["R1-P0-06", "R2-P-07"]
owner: "UNASSIGNED"
modules: ["rules", "rule loader", "rule executor", "rule evidence"]
deliverables: ["M3-07 修改产物", "M3-07 自动化验收证据", "M3-07 变更与回滚说明"]
acceptance_tests: ["M3-07-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

生产模式不再靠批量改状态获得正式规则。

### 修改方向

规则状态：

```text
DRAFT
CANDIDATE
VALIDATED
ACTIVE
FROZEN
DEPRECATED
RETIRED
```

晋升条件至少包括：

- Schema 通过；
- 行为测试；
- 负样本测试；
- 规则依赖完整；
- 无冲突；
- 人工审批记录；
- 版本与回退目标。

先冻结最小规则集，不批量冻结全部 24 份文档。

### 验收标准

- 生产模式只加载 ACTIVE/FROZEN；
- 每条正式规则绑定测试 ID；
- 回退到前一版本不修改历史运行；
- 候选规则不能混入生产哈希。

---

# 九、M4：项目中立化与 Project Harness

---


# M4：项目中立化与 Project Harness

## M4-01 定义 Project Manifest Schema

```yaml
task_id: "M4-01"
task_type: "TASK"
parent_task: null
milestone: "M4"
severity: "P0"
sequence: 31
status: "TODO"
depends_on: ["M1-02", "SCOPE-01"]
source_issues: ["R1-P0-02", "R1-P1-08", "R2-A-04"]
owner: "UNASSIGNED"
modules: ["projects", "Project Manifest", "Harness", "70_测试项目"]
deliverables: ["M4-01 修改产物", "M4-01 自动化验收证据", "M4-01 变更与回滚说明"]
acceptance_tests: ["M4-01-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

项目通过清单接入，而不是通过引擎硬编码路径。

### 建议字段

```yaml
schema_version: xcue.project/1.0
project_id: TP-001
project_version: 0.1.0
project_root: .
chapter_sources:
  candidate: candidates/
  formal: chapters/
output_root: .xcue/runs/
ruleset_profile: candidate-default
allowed_capabilities: [L1, L2, L3_PLANNING]
encoding: utf-8
permissions:
  readable: []
  writable: []
  protected: []
```

还应包含：

- 项目身份；
- 正文真源；
- 候选区；
- 输出区；
- 规则兼容版本；
- 权限边界；
- 项目状态；
- 可用能力；
- 项目级扩展。

### 验收标准

- manifest 有正式 Schema；
- 路径必须解析在 project root 内；
- candidate/formal 不能指向同一文件；
- protected 区域不能被输出目录覆盖。

---

---

## M4-02 建立 Project Loader 与 Harness Validator

```yaml
task_id: "M4-02"
task_type: "TASK"
parent_task: null
milestone: "M4"
severity: "P0"
sequence: 32
status: "TODO"
depends_on: ["M4-01"]
source_issues: ["R1-P0-02", "R2-A-04"]
owner: "UNASSIGNED"
modules: ["projects", "Project Manifest", "Harness", "70_测试项目"]
deliverables: ["M4-02 修改产物", "M4-02 自动化验收证据", "M4-02 变更与回滚说明"]
acceptance_tests: ["M4-02-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

替代当前只检查三个目录存在的弱 Harness。

### 修改方向

验证：

- project_id 唯一且合法；
- manifest 版本兼容；
- 根路径存在；
- 真源路径存在；
- 输出目录可写；
- 规则 profile 存在；
- 权限矩阵无重叠冲突；
- 候选/正式/输出边界互斥；
- 当前引擎版本满足要求；
- 运行模式与项目能力兼容。

### 验收标准

- 缺目录、错版本、权限冲突分别返回明确错误；
- Harness 校验不依赖 TP-001 名称；
- 项目对象通过统一数据模型传给 L1/L2/L3。

---

---

## M4-03 移除引擎中的 TP-001 固定路径和默认内容

```yaml
task_id: "M4-03"
task_type: "TASK"
parent_task: null
milestone: "M4"
severity: "P0"
sequence: 33
status: "TODO"
depends_on: ["M4-02"]
source_issues: ["R1-P0-02"]
owner: "UNASSIGNED"
modules: ["projects", "Project Manifest", "Harness", "70_测试项目"]
deliverables: ["M4-03 修改产物", "M4-03 自动化验收证据", "M4-03 变更与回滚说明"]
acceptance_tests: ["M4-03-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

引擎本体与测试项目彻底分离。

### 修改方向

扫描并移除：

- `70_测试项目/TP-001_CleanHarness_IR_Runtime` 固定路径；
- TP-001 默认正文；
- TP-001 默认 project name；
- 统一入口中的 TP-001 target；
- 任何特定小说名/角色名/章节名。

TP-001 只作为 acceptance fixture 存在。

### 验收标准

- 删除 `70_测试项目/TP-001...` 后，`xcue --help`、规则校验和项目校验仍可运行；
- 运行 TP-001 通过 manifest；
- 代码搜索不再出现 TP-001 路径常量。

---

---

## M4-04 建立第二个最小测试项目

```yaml
task_id: "M4-04"
task_type: "TASK"
parent_task: null
milestone: "M4"
severity: "P0"
sequence: 34
status: "TODO"
depends_on: ["M4-03"]
source_issues: ["R1-P0-02"]
owner: "UNASSIGNED"
modules: ["projects", "Project Manifest", "Harness", "70_测试项目"]
deliverables: ["M4-04 修改产物", "M4-04 自动化验收证据", "M4-04 变更与回滚说明"]
acceptance_tests: ["M4-04-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

证明项目中立性，而不是仅声明中立。

### 修改方向

新增 `TP-002_MinimalHarness`：

- 不复制 TP-001 engine；
- 只包含 manifest、候选正文、正式正文占位、输出目录；
- 项目名和路径结构与 TP-001 不同；
- 至少包含一个合法样本和一个非法样本。

### 验收标准

- 不修改引擎代码即可运行 TP-001 与 TP-002；
- 两项目产物完全隔离；
- 一个项目损坏不影响另一个；
- 规则集可独立选择。

---

---

## M4-05 收缩/隔离旧正文检测与 TP-001 内置 engine

```yaml
task_id: "M4-05"
task_type: "TASK"
parent_task: null
milestone: "M4"
severity: "P1"
sequence: 35
status: "TODO"
depends_on: ["M4-04"]
source_issues: ["R1-P1-02", "R2-C-09"]
owner: "UNASSIGNED"
modules: ["projects", "Project Manifest", "Harness", "70_测试项目"]
deliverables: ["M4-05 修改产物", "M4-05 自动化验收证据", "M4-05 变更与回滚说明"]
acceptance_tests: ["M4-05-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

建立唯一主链，避免三套实现继续漂移。

### 修改方向

- `正文检测/` 变成兼容适配器，只调用新 L1；或迁入 `legacy/`；
- TP-001 的 `tp001_engine.py` 与拆分模块二选一；
- 所有 legacy 入口默认不出现在主 CLI；
- 写明弃用版本和删除条件。

### 验收标准

- 旧入口不再包含复制的检测算法；
- 主测试不依赖 legacy；
- 同一功能只有一份业务实现。

---

# 十、M5：代码工程形态重构

---


# M5：代码工程形态重构

## M5-01 建立真实 Python 包

```yaml
task_id: "M5-01"
task_type: "TASK"
parent_task: null
milestone: "M5"
severity: "P1"
sequence: 36
status: "TODO"
depends_on: ["M1-04", "M1-05", "M2-02", "M3-01", "M4-05"]
source_issues: ["R1-P1-01", "R2-C-04"]
owner: "UNASSIGNED"
modules: ["src/xcue", "pyproject.toml", "tests", "build/release"]
deliverables: ["M5-01 修改产物", "M5-01 自动化验收证据", "M5-01 变更与回滚说明"]
acceptance_tests: ["M5-01-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

消除 15 处 `sys.path.insert()` 和空 wheel。

### 修改方向

建议结构：

```text
src/xcue/
  cli/
  core/
  projects/
  rules/
  pipeline/
  stages/l1/
  stages/l2/
  stages/l3/
  artifacts/
  recovery/
tests/
```

第一步只迁移公共组件和 CLI，确保每批迁移可运行；不要一次搬全部文件。

### 验收标准

- 生产代码不再修改 `sys.path`；
- `python -c "import xcue"` 成功；
- 从任意 cwd 调用 CLI 均成功；
- IDE/pytest/正式运行使用同一导入路径。

---

---

## M5-02 拆分 248 行流水线函数

```yaml
task_id: "M5-02"
task_type: "EPIC"
parent_task: null
milestone: "M5"
severity: "P1"
sequence: 37
status: "TODO"
depends_on: ["M5-01", "M2-01", "M2-02", "M2-05", "M2-07"]
source_issues: ["R2-C-05"]
owner: "UNASSIGNED"
modules: ["src/xcue", "pyproject.toml", "tests", "build/release"]
deliverables: ["M5-02 修改产物", "M5-02 自动化验收证据", "M5-02 变更与回滚说明"]
acceptance_tests: ["M5-02-AT-01"]
prohibitions: ["不得直接领取 Epic；只能领取其子任务", "不得绕过子任务验收关闭 Epic"]
rollback_required: true
blocks_release: false
execution_policy: "CHILD_TASKS_ONLY"
```

### 任务目标

分离编排、IO、阶段执行、状态归并和恢复。

> 本项为 Epic，不可直接交给 Codex。只有全部子任务均为 `ACCEPTED`，本 Epic 才可转为 `READY_FOR_REVIEW`。

### 修改方向

建立：

- `PreflightService`；
- `RunRepository`；
- `StageExecutor`；
- `ArtifactRegistry`；
- `StatusReducer`；
- `RecoveryManager`。

流水线主函数只负责顺序编排，不直接：

- 构造所有路径；
- 写 JSON；
- 计算所有哈希；
- 解释所有退出码；
- 捕获所有异常。

### 验收标准

- 主编排函数逻辑行不超过 100，圈复杂度不超过 10；超出必须提交 ADR 并由独立验收接受；
- 每个服务有单元测试；
- 状态归并可在不启动子进程情况下测试。

---

---

## M5-02A 抽取 PreflightService 与 RunRepository

```yaml
task_id: "M5-02A"
task_type: "SUBTASK"
parent_task: "M5-02"
milestone: "M5"
severity: "P1"
sequence: 38
status: "TODO"
depends_on: ["M5-01", "M2-01", "M2-02", "M2-05"]
source_issues: ["R2-C-05"]
owner: "UNASSIGNED"
modules: ["src/xcue", "pyproject.toml", "tests", "build/release"]
deliverables: ["M5-02A 修改产物", "M5-02A 自动化验收证据", "M5-02A 变更与回滚说明"]
acceptance_tests: ["M5-02A-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

先从主流水线移出预检、运行身份和持久化职责。

### 验收标准

- 两个服务均可独立单测；
- 主流程不直接创建运行目录或写 manifest；
- 原有行为回归通过。

---

## M5-02B 抽取 StageExecutor、ArtifactRegistry 与 StatusReducer

```yaml
task_id: "M5-02B"
task_type: "SUBTASK"
parent_task: "M5-02"
milestone: "M5"
severity: "P1"
sequence: 39
status: "TODO"
depends_on: ["M5-01", "M2-05", "M2-07"]
source_issues: ["R2-C-05"]
owner: "UNASSIGNED"
modules: ["src/xcue", "pyproject.toml", "tests", "build/release"]
deliverables: ["M5-02B 修改产物", "M5-02B 自动化验收证据", "M5-02B 变更与回滚说明"]
acceptance_tests: ["M5-02B-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

分离阶段执行、产物登记和状态归并。

### 验收标准

- 状态归并不启动子进程；
- StageExecutor 不自行决定业务最终状态；
- 所有产物通过 registry 写入。

---

## M5-02C 重建瘦编排器并接入 RecoveryManager

```yaml
task_id: "M5-02C"
task_type: "SUBTASK"
parent_task: "M5-02"
milestone: "M5"
severity: "P1"
sequence: 40
status: "TODO"
depends_on: ["M5-02A", "M5-02B", "M2-04C"]
source_issues: ["R2-C-05"]
owner: "UNASSIGNED"
modules: ["src/xcue", "pyproject.toml", "tests", "build/release"]
deliverables: ["M5-02C 修改产物", "M5-02C 自动化验收证据", "M5-02C 变更与回滚说明"]
acceptance_tests: ["M5-02C-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

主编排器只表达执行顺序和服务协作。

### 验收标准

- 主编排函数逻辑行不超过 100；
- 圈复杂度不超过 10，超出必须有 ADR；
- 无直接 JSON 写入、路径拼装和业务规则表。

---

## M5-03 统一阶段接口，不再默认使用子进程耦合内部模块

```yaml
task_id: "M5-03"
task_type: "TASK"
parent_task: null
milestone: "M5"
severity: "P1"
sequence: 41
status: "TODO"
depends_on: ["M5-01", "M5-02C"]
source_issues: ["R1-P1-02"]
owner: "UNASSIGNED"
modules: ["src/xcue", "pyproject.toml", "tests", "build/release"]
deliverables: ["M5-03 修改产物", "M5-03 自动化验收证据", "M5-03 变更与回滚说明"]
acceptance_tests: ["M5-03-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

内部调用使用 Python API，外部 CLI 仅作适配器。

### 修改方向

定义：

```python
class Stage:
    def validate_input(...): ...
    def run(...): ...
    def validate_output(...): ...
```

PIPELINE 直接调用 Stage API。只有需要隔离或明确超时的外部执行器才使用子进程。

### 验收标准

- 单元测试可直接调用 L1/L2/L3；
- CLI 与 API 输出一致；
- TP-001/TP-002 默认 acceptance 流水线中，L1/L2/L3 内部调用不得启动阶段子进程；仅外部隔离执行器允许子进程，并须在测试中计数；
- 阶段 timeout 有明确边界。

---

---

## M5-04 建立资源限制

```yaml
task_id: "M5-04"
task_type: "TASK"
parent_task: null
milestone: "M5"
severity: "P1"
sequence: 42
status: "TODO"
depends_on: ["M1-01", "M5-01"]
source_issues: ["R2-C-07", "R2-C-08"]
owner: "UNASSIGNED"
modules: ["src/xcue", "pyproject.toml", "tests", "build/release"]
deliverables: ["M5-04 修改产物", "M5-04 自动化验收证据", "M5-04 变更与回滚说明"]
acceptance_tests: ["M5-04-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

避免大文件、大 JSON 和无限日志造成不稳定。

### 修改方向

配置项至少包括：

- 输入文件最大字节；
- 正文最大字符；
- 段落最大数量；
- JSON 最大深度和数组长度；
- 单阶段输出数量；
- 单日志最大字节；
- 单次运行总产物容量；
- 阶段 timeout。

候选模式可宽松，生产模式必须强制。

### 验收标准

- 超限在完整读取/处理前被拒绝；
- 超限错误可区分资源类型；
- 限制记录在运行清单中。

---

---

## M5-05 建立真实打包和 console script

```yaml
task_id: "M5-05"
task_type: "TASK"
parent_task: null
milestone: "M5"
severity: "P1"
sequence: 43
status: "TODO"
depends_on: ["M5-01", "M5-03"]
source_issues: ["R1-P1-01"]
owner: "UNASSIGNED"
modules: ["src/xcue", "pyproject.toml", "tests", "build/release"]
deliverables: ["M5-05 修改产物", "M5-05 自动化验收证据", "M5-05 变更与回滚说明"]
acceptance_tests: ["M5-05-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

终止“pip install 成功但空包”的假安装。

### 修改方向

- 配置 package discovery；
- 版本不再为 `0.0.0`；
- `pytest` 移入开发依赖；
- 添加 console script：`xcue = xcue.cli:main`；
- wheel 构建后在全新虚拟环境执行导入和 CLI 测试；
- 生成 `SOURCES.txt` 验证实际模块入包。

### 验收标准

- wheel 包含 `xcue` 代码；
- 全新 venv 安装后 `xcue --help` 成功；
- 不依赖仓库 cwd；
- wheel 内容测试进入 CI。

---

---

## M5-06 清理重复、未使用和遗留模块

```yaml
task_id: "M5-06"
task_type: "TASK"
parent_task: null
milestone: "M5"
severity: "P2"
sequence: 44
status: "TODO"
depends_on: ["M4-05", "M5-01", "M5-03"]
source_issues: ["R1-P1-02", "R1-P2-03", "R2-A-06", "R2-C-09"]
owner: "UNASSIGNED"
modules: ["src/xcue", "pyproject.toml", "tests", "build/release"]
deliverables: ["M5-06 修改产物", "M5-06 自动化验收证据", "M5-06 变更与回滚说明"]
acceptance_tests: ["M5-06-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

降低维护分叉。

### 重点核验

- `正文检测/` 重复逻辑；
- `tp001_engine.py`；
- `日志记录校验.py`；
- `产物血缘.py`；
- 重复正文切分；
- 重复状态和报告模型。

### 修改方向

对每个疑似模块做三选一：

- 接入主链；
- 迁入 legacy 并设置删除版本；
- 删除并补回归测试。

### 验收标准

- 无“可能以后用”而保留的孤立模块；
- 静态导入检查无 unresolved import；除声明的 CLI 入口、插件和测试 fixture 外，生产模块不得出现零入度孤立节点；
- 删除后完整测试通过。

---

# 十一、M6：最小执行—diff—回流闭环

---

## M5-07 建立 Python 版本、依赖锁定与可复现构建

```yaml
task_id: "M5-07"
task_type: "TASK"
parent_task: null
milestone: "M5"
severity: "P1"
sequence: 45
status: "TODO"
depends_on: ["M5-01", "M5-05"]
source_issues: ["R1-P1-01", "R1-P2-02"]
owner: "UNASSIGNED"
modules: ["src/xcue", "pyproject.toml", "tests", "build/release"]
deliverables: ["M5-07 修改产物", "M5-07 自动化验收证据", "M5-07 变更与回滚说明"]
acceptance_tests: ["M5-07-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

使开发、测试和发布环境具有明确版本边界与可重复安装结果。

### 已确认问题

当前没有正式支持的 Python 版本范围、依赖约束、开发依赖分组和可复现构建策略。即使 wheel 修复，也无法证明不同机器得到同一依赖集合和构建结果。

### 修改方向

至少建立：

- 单一项目版本来源；
- 支持的 Python 最低/最高版本；
- runtime、test、dev 依赖分组；
- 锁文件或 constraints 文件；
- 构建后依赖清单；
- 干净虚拟环境安装脚本；
- 两次构建产物内容差异检查。

### 验收标准

- 不支持的 Python 版本在安装前明确失败；
- 全新环境可按锁定依赖安装；
- runtime 安装不携带 pytest 等开发依赖；
- 相同源码与环境下连续构建的 wheel 内容一致，时间戳差异须被规范化或记录；
- 版本号只从一个位置读取。

---


# M6：最小执行—Diff—回流闭环

## M6-01 重新定义 L3 当前能力边界

```yaml
task_id: "M6-01"
task_type: "TASK"
parent_task: null
milestone: "M6"
severity: "P0"
sequence: 46
status: "TODO"
depends_on: ["M1-05"]
source_issues: ["R1-P0-04", "R1-P0-05", "R2-A-02"]
owner: "UNASSIGNED"
modules: ["L3 task planning", "executor", "diff/apply", "rollback"]
deliverables: ["M6-01 修改产物", "M6-01 自动化验收证据", "M6-01 变更与回滚说明"]
acceptance_tests: ["M6-01-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

在真实执行器完成前，停止把任务规划称为执行完成。

### 修改方向

当前 L3 明确命名为：

```text
L3 Task Planning
```

状态：

```text
TASK_PLAN_CREATED
AWAITING_EXECUTOR
NOT_EXECUTED
```

未来状态与当前状态分开，不要求每次运行都出现 `EXECUTION_COMPLETED`、`ACCEPTED`、`ROLLED_BACK`。

### 验收标准

- 报告不再暗示任务已执行；
- 未执行任务不能进入验收通过；
- workflow status 清晰传播到顶层。

---

---

## M6-02 定义可执行任务 Schema

```yaml
task_id: "M6-02"
task_type: "TASK"
parent_task: null
milestone: "M6"
severity: "P1"
sequence: 47
status: "TODO"
depends_on: ["M2-05", "M3-05A", "M3-05B", "M3-05C", "M4-02", "M6-01"]
source_issues: ["R1-P0-04"]
owner: "UNASSIGNED"
modules: ["L3 task planning", "executor", "diff/apply", "rollback"]
deliverables: ["M6-02 修改产物", "M6-02 自动化验收证据", "M6-02 变更与回滚说明"]
acceptance_tests: ["M6-02-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

让任务从自然语言建议变成可验证执行请求。

### 建议字段

```json
{
  "task_id": "...",
  "task_type": "NORMALIZE_FRONT_MATTER",
  "target_artifact": "...",
  "preconditions": [],
  "operations": [],
  "expected_postconditions": [],
  "rollback_strategy": "RESTORE_SNAPSHOT",
  "required_approval": true,
  "origin_gate": "L1-00",
  "origin_item_id": "..."
}
```

任务分为：

- 确定性工程任务；
- 文档治理任务；
- 正文建议任务；
- 禁止自动执行任务。

### 验收标准

- 未知 task_type 被拒绝；
- 每种任务有 handler；
- 自然语言正文改写不得伪装成确定性任务。

---

---

## M6-03 先实现确定性工程执行器

```yaml
task_id: "M6-03"
task_type: "TASK"
parent_task: null
milestone: "M6"
severity: "P1"
sequence: 48
status: "TODO"
depends_on: ["M2-02", "M2-05", "M2-07", "M3-05A", "M3-05B", "M3-05C", "M4-02", "M5-03", "M6-02"]
source_issues: ["R1-P0-04"]
owner: "UNASSIGNED"
modules: ["L3 task planning", "executor", "diff/apply", "rollback"]
deliverables: ["M6-03 修改产物", "M6-03 自动化验收证据", "M6-03 变更与回滚说明"]
acceptance_tests: ["M6-03-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

先闭合低风险任务，不直接自动改写小说正文。

### 首批允许任务

- Front Matter 补字段；
- 路径/引用修正；
- 编码和行尾规范化；
- 生成缺失目录；
- 报告字段补全；
- 清单重建；
- 格式校验修复。

### 禁止首批自动执行

- 删除正式正文；
- 批量改写章节；
- 更改角色设定；
- 自动发布；
- 将候选正文直接覆盖正式正文。

### 验收标准

- 至少一种任务完成真实执行；
- 执行前后均有快照和哈希；
- 失败不污染原文件；
- 执行器仅写 manifest 授权路径。

---

---

## M6-04 建立 diff、审批和应用机制

```yaml
task_id: "M6-04"
task_type: "EPIC"
parent_task: null
milestone: "M6"
severity: "P1"
sequence: 49
status: "TODO"
depends_on: ["M6-03"]
source_issues: ["R1-P0-04"]
owner: "UNASSIGNED"
modules: ["L3 task planning", "executor", "diff/apply", "rollback"]
deliverables: ["M6-04 修改产物", "M6-04 自动化验收证据", "M6-04 变更与回滚说明"]
acceptance_tests: ["M6-04-AT-01"]
prohibitions: ["不得直接领取 Epic；只能领取其子任务", "不得绕过子任务验收关闭 Epic"]
rollback_required: true
blocks_release: false
execution_policy: "CHILD_TASKS_ONLY"
```

### 任务目标

任务执行不直接覆盖真源。

> 本项为 Epic，不可直接交给 Codex。只有全部子任务均为 `ACCEPTED`，本 Epic 才可转为 `READY_FOR_REVIEW`。

### 修改方向

流程：

```text
生成任务
→ 沙箱执行
→ 生成 diff
→ 自动后置校验
→ 人工/策略审批
→ 原子应用
→ 登记新产物
```

正文类任务默认只产生 patch，不自动应用。

### 验收标准

- diff 可重复生成；
- 审批前正式文件哈希不变；
- 应用后登记 old/new hash；
- 拒绝审批不会留下半应用状态。

---

---

## M6-04A 建立授权沙箱执行

```yaml
task_id: "M6-04A"
task_type: "SUBTASK"
parent_task: "M6-04"
milestone: "M6"
severity: "P1"
sequence: 50
status: "TODO"
depends_on: ["M2-04C", "M2-05", "M3-05A", "M4-02", "M6-03"]
source_issues: ["GOV-M6-04A"]
owner: "UNASSIGNED"
modules: ["L3 task planning", "executor", "diff/apply", "rollback"]
deliverables: ["M6-04A 修改产物", "M6-04A 自动化验收证据", "M6-04A 变更与回滚说明"]
acceptance_tests: ["M6-04A-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

执行器只在隔离副本中产生候选结果。

### 验收标准

- 正式文件在沙箱阶段哈希不变；
- 沙箱路径不越出 run root；
- 失败时沙箱可安全清理且保留审计摘要。

---

## M6-04B 生成确定性 Diff 与后置校验

```yaml
task_id: "M6-04B"
task_type: "SUBTASK"
parent_task: "M6-04"
milestone: "M6"
severity: "P1"
sequence: 51
status: "TODO"
depends_on: ["M6-04A"]
source_issues: ["GOV-M6-04B"]
owner: "UNASSIGNED"
modules: ["L3 task planning", "executor", "diff/apply", "rollback"]
deliverables: ["M6-04B 修改产物", "M6-04B 自动化验收证据", "M6-04B 变更与回滚说明"]
acceptance_tests: ["M6-04B-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

同一输入和任务生成可重复 diff，并验证预期后置条件。

### 验收标准

- 相同输入生成相同 diff；
- diff 包含 old/new hash；
- 后置校验失败时不得进入审批。

---

## M6-04C 建立审批记录与拒绝路径

```yaml
task_id: "M6-04C"
task_type: "SUBTASK"
parent_task: "M6-04"
milestone: "M6"
severity: "P1"
sequence: 52
status: "TODO"
depends_on: ["M6-04B", "M3-05A", "M3-05C"]
source_issues: ["GOV-M6-04C"]
owner: "UNASSIGNED"
modules: ["L3 task planning", "executor", "diff/apply", "rollback"]
deliverables: ["M6-04C 修改产物", "M6-04C 自动化验收证据", "M6-04C 变更与回滚说明"]
acceptance_tests: ["M6-04C-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

应用动作必须引用不可变审批记录。

### 验收标准

- 审批记录包含审批者、时间、diff hash 和范围；
- 拒绝审批不修改正式文件；
- 过期 diff 不能使用旧审批应用。

---

## M6-04D 实现多文件原子应用

```yaml
task_id: "M6-04D"
task_type: "SUBTASK"
parent_task: "M6-04"
milestone: "M6"
severity: "P1"
sequence: 53
status: "TODO"
depends_on: ["M6-04C", "M2-05"]
source_issues: ["GOV-M6-04D"]
owner: "UNASSIGNED"
modules: ["L3 task planning", "executor", "diff/apply", "rollback"]
deliverables: ["M6-04D 修改产物", "M6-04D 自动化验收证据", "M6-04D 变更与回滚说明"]
acceptance_tests: ["M6-04D-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

全部文件校验通过后才提交，否则完整回退。

### 验收标准

- 中途注入失败后正式文件全部恢复；
- 应用结果登记 old/new artifact；
- 不存在部分应用却标记完成。

---

## M6-05 建立原闸门回流复验

```yaml
task_id: "M6-05"
task_type: "TASK"
parent_task: null
milestone: "M6"
severity: "P1"
sequence: 54
status: "TODO"
depends_on: ["M1-01", "M2-02", "M2-05", "M3-06", "M6-04D"]
source_issues: ["R1-P0-04"]
owner: "UNASSIGNED"
modules: ["L3 task planning", "executor", "diff/apply", "rollback"]
deliverables: ["M6-05 修改产物", "M6-05 自动化验收证据", "M6-05 变更与回滚说明"]
acceptance_tests: ["M6-05-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

闭合“修复后是否真的解决原问题”。

### 修改方向

每个任务保留：

- origin_gate；
- origin_failure_id；
- origin_rule_id；
- expected_resolution。

执行应用后自动回到原闸门，而不是直接进入下一层。结果：

```text
RESOLVED
NOT_RESOLVED
REGRESSION_INTRODUCED
NEW_FAILURES_FOUND
```

### 验收标准

- 修复后原失败项重新检测；
- 新运行不覆盖旧运行；
- 回流失败生成新 attempt；
- 报告能比较前后证据。

---

---

## M6-06 建立回滚和失败隔离

```yaml
task_id: "M6-06"
task_type: "TASK"
parent_task: null
milestone: "M6"
severity: "P1"
sequence: 55
status: "TODO"
depends_on: ["M2-04C", "M2-05", "M6-04D"]
source_issues: ["R1-P0-04", "R2-P-02"]
owner: "UNASSIGNED"
modules: ["L3 task planning", "executor", "diff/apply", "rollback"]
deliverables: ["M6-06 修改产物", "M6-06 自动化验收证据", "M6-06 变更与回滚说明"]
acceptance_tests: ["M6-06-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

应用失败时恢复，不依赖手工复制。

### 修改方向

- 每次应用前快照；
- 多文件任务采用事务目录；
- 全部后置校验通过才 commit；
- 任一文件失败则 rollback；
- 回滚也登记产物和状态；
- 不复用“成功”状态表示已回滚。

### 验收标准

- 模拟中途失败后原文件哈希恢复；
- rollback 有独立状态与证据；
- 不出现部分文件已改、部分未改而仍标完成。

---

# 十二、M7：文档治理与工程导航

---


# M7：文档治理与工程导航

## M7-01 重写根级当前状态页

```yaml
task_id: "M7-01"
task_type: "TASK"
parent_task: null
milestone: "M7"
severity: "P0"
sequence: 56
status: "TODO"
depends_on: ["M1-05"]
source_issues: ["R1-P0-07", "R1-P1-07", "R2-D-03"]
owner: "UNASSIGNED"
modules: ["README", "INDEX", "AGENTS", "Markdown 控制文档"]
deliverables: ["M7-01 修改产物", "M7-01 自动化验收证据", "M7-01 变更与回滚说明"]
acceptance_tests: ["M7-01-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

README、INDEX、AGENTS 不再描述失真。

### 修改方向

根级只保留三类入口：

1. 当前状态与边界；
2. 当前任务与里程碑；
3. 运行与验收命令。

明确写出：

- 已实现；
- 未实现；
- 候选能力；
- 生产阻断；
- 唯一主入口；
- legacy 位置。

### 验收标准

- 不再写“全部仍处于 Markdown 文件态”；
- 不引用不存在的当前基线文件；
- 在干净副本中，仅按根级 README、INDEX、AGENTS 执行 `python scripts/verify_docs_quickstart.py`，应完成安装检查、候选运行和边界检查并返回 0；

---

---

## M7-02 补全 Front Matter 依赖图

```yaml
task_id: "M7-02"
task_type: "TASK"
parent_task: null
milestone: "M7"
severity: "P1"
sequence: 57
status: "TODO"
depends_on: ["M3-01"]
source_issues: ["R1-P1-06", "R2-D-01"]
owner: "UNASSIGNED"
modules: ["README", "INDEX", "AGENTS", "Markdown 控制文档"]
deliverables: ["M7-02 修改产物", "M7-02 自动化验收证据", "M7-02 变更与回滚说明"]
acceptance_tests: ["M7-02-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

上游依赖、下游引用、替代关系不再全部为空。

### 修改方向

不要给全部 102 份 Markdown 强加同一模板。只治理真正参与工程控制的文档和规则。

字段必须引用稳定 ID，不引用易变文件名：

```yaml
upstream: [XCUE-L1-00]
downstream: [XCUE-L15-001]
supersedes: []
```

增加：

- 引用对象存在检查；
- 循环依赖检查；
- deprecated/superseded 一致性检查。

### 验收标准

- 核心规则依赖不为空；
- 依赖图可生成；
- 删除被引用规则时 CI 失败。

---

---

## M7-03 将裸文件名引用改为可校验链接

```yaml
task_id: "M7-03"
task_type: "TASK"
parent_task: null
milestone: "M7"
severity: "P1"
sequence: 58
status: "TODO"
depends_on: ["M7-01"]
source_issues: ["R1-P0-07", "R2-D-03", "R2-D-04"]
owner: "UNASSIGNED"
modules: ["README", "INDEX", "AGENTS", "Markdown 控制文档"]
deliverables: ["M7-03 修改产物", "M7-03 自动化验收证据", "M7-03 变更与回滚说明"]
acceptance_tests: ["M7-03-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

普通链接检查器能发现失效路径。

### 修改方向

- 现存文件使用真实相对链接；
- 待建文件使用结构化 task ID，不伪装成链接；
- 图片统一 `_images/`；
- 文档移动必须更新链接或保留重定向说明。

### 验收标准

- 根级文档所有链接可打开；
- Markdown 链接检查进入自动化测试；
- 不再引用不存在日志作为现有证据。

---

---

## M7-04 统一文档编码、行尾和章节编号

```yaml
task_id: "M7-04"
task_type: "TASK"
parent_task: null
milestone: "M7"
severity: "P2"
sequence: 59
status: "TODO"
depends_on: ["M0-01"]
source_issues: ["R1-P2-04", "R2-D-06", "R2-D-07", "R2-D-08"]
owner: "UNASSIGNED"
modules: ["README", "INDEX", "AGENTS", "Markdown 控制文档"]
deliverables: ["M7-04 修改产物", "M7-04 自动化验收证据", "M7-04 变更与回滚说明"]
acceptance_tests: ["M7-04-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

降低解析器和跨平台差异。

### 修改方向

- UTF-8 无 BOM；
- LF 行尾；
- 删除行尾空格；
- 修复 L2-01 重复“第 18 节”；
- rule ID 命名空间统一；
- 文档解析不再依赖自然语言章节序号。

### 验收标准

- 格式检查脚本零错误；
- Windows/Linux 读取结果一致；
- 不因章节编号调整导致规则消失。

---

---

## M7-05 让文档命令成为可执行测试

```yaml
task_id: "M7-05"
task_type: "TASK"
parent_task: null
milestone: "M7"
severity: "P1"
sequence: 60
status: "TODO"
depends_on: ["M1-04", "M7-01"]
source_issues: ["R1-P0-07", "R1-P1-07", "R2-D-05"]
owner: "UNASSIGNED"
modules: ["README", "INDEX", "AGENTS", "Markdown 控制文档"]
deliverables: ["M7-05 修改产物", "M7-05 自动化验收证据", "M7-05 变更与回滚说明"]
acceptance_tests: ["M7-05-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

README 不再存在缺参数、按原文必然失败的命令。

### 修改方向

把文档代码块标注为：

- `tested-command`；
- `example-only`；
- `pseudo-code`。

CI 只执行 `tested-command`，但所有正式运行命令必须属于该类。

### 验收标准

- README/工程执行层 README 中的正式命令逐条通过；
- 命令示例与 CLI help 一致；
- 示例路径来自 fixture，不依赖个人机器。

---

---

## M7-06 建立文档—规则—测试映射表

```yaml
task_id: "M7-06"
task_type: "TASK"
parent_task: null
milestone: "M7"
severity: "P1"
sequence: 61
status: "TODO"
depends_on: ["M3-06", "M7-02"]
source_issues: ["R1-P0-03", "R1-P1-06", "R2-D-02"]
owner: "UNASSIGNED"
modules: ["README", "INDEX", "AGENTS", "Markdown 控制文档"]
deliverables: ["M7-06 修改产物", "M7-06 自动化验收证据", "M7-06 变更与回滚说明"]
acceptance_tests: ["M7-06-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

每条正式规则能找到设计依据和验证证据。

### 修改方向

自动生成：

| rule_id | runtime source | rationale doc | test IDs | status | last verified |
|---|---|---|---|---|---|

不人工重复维护多个表，映射从结构化规则与测试元数据生成。

### 验收标准

- ACTIVE/FROZEN 规则无测试映射时 CI 失败；
- 文档中的规则状态与结构化规则一致；
- 过期文档明确标记 archived。

---

# 十三、M8：测试、CI、发布和生产候选验收

---


# M8：测试、CI、发布与生产候选验收

## M8-01 建立测试金字塔

```yaml
task_id: "M8-01"
task_type: "TASK"
parent_task: null
milestone: "M8"
severity: "P0"
sequence: 62
status: "TODO"
depends_on: ["M5-03"]
source_issues: ["R1-P1-05", "R2-C-10"]
owner: "UNASSIGNED"
modules: ["tests", "CI", "release scripts", "Windows regression"]
deliverables: ["M8-01 修改产物", "M8-01 自动化验收证据", "M8-01 变更与回滚说明"]
acceptance_tests: ["M8-01-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

解决 37 个测试主要是子进程集成测试、unit 为 0 的问题。

### 分层目标

1. Unit：纯函数、Schema、状态归并、规则匹配、路径；
2. Integration：L1/L2/L3 API 与文件系统；
3. CLI：子命令契约；
4. Acceptance：TP-001、TP-002 完整运行；
5. Adversarial：损坏输入、越界、并发、中断、超限。

### 验收标准

- CI 基准环境中 `python -m pytest -q -m unit` 总耗时不超过 15 秒；超时需拆分快慢标记，不得删除测试；
- 默认测试不必启动全部 acceptance；
- 完整验收单独运行；
- 每个 P0 故障有回归测试。

---

---

## M8-02 增加公开 CLI 合同测试

```yaml
task_id: "M8-02"
task_type: "TASK"
parent_task: null
milestone: "M8"
severity: "P0"
sequence: 63
status: "TODO"
depends_on: ["M1-03", "M1-04"]
source_issues: ["R1-P0-01", "R1-P1-05", "R2-C-03"]
owner: "UNASSIGNED"
modules: ["tests", "CI", "release scripts", "Windows regression"]
deliverables: ["M8-02 修改产物", "M8-02 自动化验收证据", "M8-02 变更与回滚说明"]
acceptance_tests: ["M8-02-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

所有公开命令都被自动执行。

### 测试范围

- `--help`；
- 缺参数；
- 未知参数；
- 非法路径；
- 非法 run-id；
- 候选/生产模式；
- project validate；
- rules validate；
- run inspect/retry/recover。

### 验收标准

- CLI 输出格式稳定；
- 错误信封可 JSON 解析；
- 不出现裸 argparse 栈或 Python traceback。

---

---

## M8-03 增加规则行为突变测试

```yaml
task_id: "M8-03"
task_type: "TASK"
parent_task: null
milestone: "M8"
severity: "P0"
sequence: 64
status: "TODO"
depends_on: ["M3-02", "M3-03", "M3-04", "M3-05A", "M3-05B", "M3-05C"]
source_issues: ["R1-P0-03", "R2-A-01"]
owner: "UNASSIGNED"
modules: ["tests", "CI", "release scripts", "Windows regression"]
deliverables: ["M8-03 修改产物", "M8-03 自动化验收证据", "M8-03 变更与回滚说明"]
acceptance_tests: ["M8-03-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

证明结构化规则不是装饰。

### 修改方向

测试采用临时规则集：

- 改阈值，结果变化；
- 改路由，目标模块变化；
- 删除禁止项，行为变化；
- 制造冲突，加载失败；
- 修改执行顺序，调用记录变化。

### 验收标准

- 测试不修改正式规则文件；
- 每类规则至少有一个“改规则即改行为”测试。

---

---

## M8-04 增加并发、中断和恢复测试

```yaml
task_id: "M8-04"
task_type: "TASK"
parent_task: null
milestone: "M8"
severity: "P1"
sequence: 65
status: "TODO"
depends_on: ["M2-03", "M2-04C"]
source_issues: ["GOV-M8-04"]
owner: "UNASSIGNED"
modules: ["tests", "CI", "release scripts", "Windows regression"]
deliverables: ["M8-04 修改产物", "M8-04 自动化验收证据", "M8-04 变更与回滚说明"]
acceptance_tests: ["M8-04-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

证明运行事务有效。

### 验收标准

- 同 run-id 双进程只有一个获得锁；
- 超时状态被记录；
- 中断后 inspect 识别最后 checkpoint；
- retry 生成新 attempt；
- 旧产物哈希不变。

---

---

## M8-05 增加双项目隔离验收

```yaml
task_id: "M8-05"
task_type: "TASK"
parent_task: null
milestone: "M8"
severity: "P0"
sequence: 66
status: "TODO"
depends_on: ["M4-02", "M4-04"]
source_issues: ["R1-P0-02"]
owner: "UNASSIGNED"
modules: ["tests", "CI", "release scripts", "Windows regression"]
deliverables: ["M8-05 修改产物", "M8-05 自动化验收证据", "M8-05 变更与回滚说明"]
acceptance_tests: ["M8-05-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

证明项目中立性。

### 验收标准

- TP-001 与 TP-002 连续/并发运行；
- 产物路径和 project_id 不串线；
- 项目 A 权限不能读取项目 B 正文；
- 删除 TP-001 不影响 TP-002 项目校验。

---

---

## M8-06 建立 CI 与质量门禁

```yaml
task_id: "M8-06"
task_type: "EPIC"
parent_task: null
milestone: "M8"
severity: "P1"
sequence: 67
status: "TODO"
depends_on: ["M5-07", "M7-06", "M8-01"]
source_issues: ["R1-P1-01", "R2-C-11", "R2-P-06"]
owner: "UNASSIGNED"
modules: ["tests", "CI", "release scripts", "Windows regression"]
deliverables: ["M8-06 修改产物", "M8-06 自动化验收证据", "M8-06 变更与回滚说明"]
acceptance_tests: ["M8-06-AT-01"]
prohibitions: ["不得直接领取 Epic；只能领取其子任务", "不得绕过子任务验收关闭 Epic"]
rollback_required: true
blocks_release: false
execution_policy: "CHILD_TASKS_ONLY"
```

### 任务目标

本地测试不再完全依赖维护者自觉。

> 本项为 Epic，不可直接交给 Codex。只有全部子任务均为 `ACCEPTED`，本 Epic 才可转为 `READY_FOR_REVIEW`。

### 建议门禁

- Python 编译；
- formatter/linter；
- 类型检查；
- unit；
- integration；
- Schema 样本；
- 文档链接；
- 规则依赖；
- wheel build/install/import；
- 干净归档检查。

### 验收标准

- 任一 P0 回归测试失败则禁止合并；
- 不要求服务器或 API，CI 只执行本地工程逻辑；
- Windows 至少增加一次实机或 CI runner 回归。

---

---

## M8-06A 建立编译、格式、Lint 与类型门禁

```yaml
task_id: "M8-06A"
task_type: "SUBTASK"
parent_task: "M8-06"
milestone: "M8"
severity: "P1"
sequence: 68
status: "TODO"
depends_on: ["M5-01"]
source_issues: ["R2-C-11", "R2-P-06"]
owner: "UNASSIGNED"
modules: ["tests", "CI", "release scripts", "Windows regression"]
deliverables: ["M8-06A 修改产物", "M8-06A 自动化验收证据", "M8-06A 变更与回滚说明"]
acceptance_tests: ["M8-06A-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

建立快速静态质量门禁。

### 验收标准

- 命令固定写入 CI 配置；
- 任一门禁失败返回非零；
- 配置文件进入版本控制。

---

## M8-06B 建立 Unit、Integration、CLI 与 Acceptance 门禁

```yaml
task_id: "M8-06B"
task_type: "SUBTASK"
parent_task: "M8-06"
milestone: "M8"
severity: "P1"
sequence: 69
status: "TODO"
depends_on: ["M8-01", "M8-02", "M8-03", "M8-04", "M8-05"]
source_issues: ["R2-C-11", "R2-P-06"]
owner: "UNASSIGNED"
modules: ["tests", "CI", "release scripts", "Windows regression"]
deliverables: ["M8-06B 修改产物", "M8-06B 自动化验收证据", "M8-06B 变更与回滚说明"]
acceptance_tests: ["M8-06B-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

按层运行测试并阻断 P0 回归。

### 验收标准

- unit 与 acceptance 分开执行；
- P0 回归失败禁止合并；
- 每层有明确最长运行时间预算。

---

## M8-06C 建立文档、Schema 与规则一致性门禁

```yaml
task_id: "M8-06C"
task_type: "SUBTASK"
parent_task: "M8-06"
milestone: "M8"
severity: "P1"
sequence: 70
status: "TODO"
depends_on: ["M3-07", "M7-05", "M7-06"]
source_issues: ["R2-C-11", "R2-P-06"]
owner: "UNASSIGNED"
modules: ["tests", "CI", "release scripts", "Windows regression"]
deliverables: ["M8-06C 修改产物", "M8-06C 自动化验收证据", "M8-06C 变更与回滚说明"]
acceptance_tests: ["M8-06C-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

文档链接、规则依赖和正式规则测试映射自动校验。

### 验收标准

- 失效链接、循环规则依赖、无测试正式规则均使 CI 失败；
- 不执行 example-only 与 pseudo-code。

---

## M8-06D 建立 Wheel 安装、干净归档与 Windows 回归门禁

```yaml
task_id: "M8-06D"
task_type: "SUBTASK"
parent_task: "M8-06"
milestone: "M8"
severity: "P1"
sequence: 71
status: "TODO"
depends_on: ["M5-05", "M5-07", "M8-06A", "M8-06B", "M8-06C"]
source_issues: ["R2-C-11", "R2-P-06"]
owner: "UNASSIGNED"
modules: ["tests", "CI", "release scripts", "Windows regression"]
deliverables: ["M8-06D 修改产物", "M8-06D 自动化验收证据", "M8-06D 变更与回滚说明"]
acceptance_tests: ["M8-06D-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

验证发布产物在干净环境可安装、导入和运行。

### 验收标准

- 全新虚拟环境安装 wheel 后 `xcue --help` 成功；
- 发布归档无缓存和本机路径；
- 至少一次 Windows 实机或 Windows CI runner 通过。

---

## M8-07 建立干净发布包

```yaml
task_id: "M8-07"
task_type: "TASK"
parent_task: null
milestone: "M8"
severity: "P1"
sequence: 72
status: "TODO"
depends_on: ["M5-05", "M8-06D"]
source_issues: ["R1-P1-01", "R1-P2-01", "R2-P-06"]
owner: "UNASSIGNED"
modules: ["tests", "CI", "release scripts", "Windows regression"]
deliverables: ["M8-07 修改产物", "M8-07 自动化验收证据", "M8-07 变更与回滚说明"]
acceptance_tests: ["M8-07-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

发布归档不再包含缓存和历史污染。

### 修改方向

发布脚本从干净文件清单生成，不直接压缩工作目录。排除：

- `.pytest_cache`；
- `__pycache__`；
- `.pyc`；
- 临时运行记录；
- egg-info；
- 本机路径；
- 调试日志。

### 验收标准

- 解包后可安装、可运行测试；
- 发布包内容清单有哈希；
- 不含缓存和个人环境路径。

---

---

## M8-08 冻结最小生产候选规则集

```yaml
task_id: "M8-08"
task_type: "TASK"
parent_task: null
milestone: "M8"
severity: "P1"
sequence: 73
status: "TODO"
depends_on: ["M3-07", "M4-04", "M7-06", "M8-03", "M8-05", "M8-06D"]
source_issues: ["R1-P0-05", "R1-P0-06"]
owner: "UNASSIGNED"
modules: ["tests", "CI", "release scripts", "Windows regression"]
deliverables: ["M8-08 修改产物", "M8-08 自动化验收证据", "M8-08 变更与回滚说明"]
acceptance_tests: ["M8-08-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: true
execution_policy: "DIRECT"
```

### 任务目标

让生产模式首次具备可信的最小规则，而不是批量宣布全部规则正式。

### 建议范围

只冻结：

- 项目 manifest 校验；
- 输入 Schema；
- 路径/权限边界；
- 运行身份和证据；
- L1 最小技术护栏；
- L2/L3 必要路由与禁止项。

读者投入、市场体验等未校准指标继续保持 candidate/heuristic。

### 验收标准

- 每条规则有测试、版本、哈希、审批；
- 生产模式能在 TP-001/TP-002 上运行；
- 生产成功仍不自动授予正文发布权限；
- 规则回退演练通过。

---

# 十四、业务指标与 L2 能力的专项任务

---


# BIZ：业务指标与 L2 能力专项

## BIZ-01 收缩 E/V/C/I 的业务命名

```yaml
task_id: "BIZ-01"
task_type: "TASK"
parent_task: null
milestone: "BIZ"
severity: "P1"
sequence: 74
status: "TODO"
depends_on: ["M1-05"]
source_issues: ["R1-P1-04", "R2-A-05"]
owner: "UNASSIGNED"
modules: ["L1 指标", "L2 能力定义", "人工标注集"]
deliverables: ["BIZ-01 修改产物", "BIZ-01 自动化验收证据", "BIZ-01 变更与回滚说明"]
acceptance_tests: ["BIZ-01-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

防止启发式关键词和段落密度被描述为真实读者行为预测。

### 修改方向

在完成数据校准前改名为：

- engagement proxy；
- value-delivery proxy；
- cognitive-load proxy；
- continuation-intent proxy。

中文报告明确写“启发式代理信号”。

### 验收标准

- 不再使用“证明读者愿意追读”等强结论；
- 报告包含适用边界、样本类型和未验证声明。

---

---

## BIZ-02 建立小型人工标注验证集

```yaml
task_id: "BIZ-02"
task_type: "TASK"
parent_task: null
milestone: "BIZ"
severity: "P2"
sequence: 75
status: "TODO"
depends_on: ["M3-02", "BIZ-01"]
source_issues: ["R1-P1-04", "R2-A-05"]
owner: "UNASSIGNED"
modules: ["L1 指标", "L2 能力定义", "人工标注集"]
deliverables: ["BIZ-02 修改产物", "BIZ-02 自动化验收证据", "BIZ-02 变更与回滚说明"]
acceptance_tests: ["BIZ-02-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

判断 L1 指标是否具有最低限度的区分能力。

### 修改方向

建立按平台/类型分层的小样本，记录：

- 人工编辑标签；
- 读者退出点；
- 各代理指标；
- 假阳性、假阴性；
- 阈值敏感性。

这不是训练大模型，也不需要 API。

### 验收标准

- 给出精确率、召回率或至少混淆矩阵；
- 验证集不少于 60 个样本，至少覆盖 3 类文本；20% 样本由两名标注者重叠标注；正式晋升前须在未参与调参的保留集上同时达到 precision ≥ 0.65、recall ≥ 0.65，并报告混淆矩阵。门槛只能在查看保留集结果前通过版本化 ADR 修改；未达标则保持 heuristic/candidate。

---

---

## BIZ-03 决定 L2 六能力是真能力还是路由模板

```yaml
task_id: "BIZ-03"
task_type: "TASK"
parent_task: null
milestone: "BIZ"
severity: "P1"
sequence: 76
status: "TODO"
depends_on: ["M3-04", "M3-05A", "M3-05B", "M3-05C"]
source_issues: ["R1-P1-03"]
owner: "UNASSIGNED"
modules: ["L1 指标", "L2 能力定义", "人工标注集"]
deliverables: ["BIZ-03 修改产物", "BIZ-03 自动化验收证据", "BIZ-03 变更与回滚说明"]
acceptance_tests: ["BIZ-03-AT-01"]
prohibitions: ["不得扩大到未列入本任务的业务能力", "不得删除既有失败样本规避验收"]
rollback_required: true
blocks_release: false
execution_policy: "DIRECT"
```

### 任务目标

解决九千余行文档与六个七行包装器之间的能力错位。

### 两种可选方向

**方向 A：真实定位为六类修复路由模板。**

- 改名；
- 收缩文档；
- 不声称独立算法；
- 输出结构化建议与边界。

**方向 B：实现六种独立能力。**

每个能力必须有：

- 独立输入特征；
- 独立判定/生成逻辑；
- 独立输出 Schema；
- 独立正负样本；
- 独立失败边界。

### 推荐

当前先选择方向 A。原因：项目底层契约尚未稳定，此时实现六套复杂算法会放大返工。

### 验收标准

- 名称与真实代码能力一致；
- 不再用文档体量证明执行能力。

---

---



# 八、首轮串行执行批次

以下批次不得并行。前一批全部 `ACCEPTED` 后，下一批才可进入 `IN_PROGRESS`。

## BATCH-0A

- 任务：M0-01, M0-02
- 进入条件：所有前置依赖均为 `ACCEPTED`
- 完成条件：本批所有任务均为 `ACCEPTED`

```powershell
python -m pytest -q tests/regression/test_confirmed_failures.py
python -m pytest -q
```
## BATCH-0B

- 任务：SCOPE-01
- 进入条件：所有前置依赖均为 `ACCEPTED`
- 完成条件：本批所有任务均为 `ACCEPTED`

```powershell
python -m pytest -q tests/unit/test_project_scope.py
```
## BATCH-1A

- 任务：M1-01, M1-02, M1-03
- 进入条件：所有前置依赖均为 `ACCEPTED`
- 完成条件：本批所有任务均为 `ACCEPTED`

```powershell
python -m pytest -q tests/unit/test_input_validation.py tests/unit/test_schemas.py tests/unit/test_error_envelope.py
python -m pytest -q tests/regression/test_invalid_input_contracts.py
```
## BATCH-1B

- 任务：M1-04, M1-05
- 进入条件：所有前置依赖均为 `ACCEPTED`
- 完成条件：本批所有任务均为 `ACCEPTED`

```powershell
python -m pytest -q tests/cli/test_cli_contract.py tests/unit/test_status_model.py
python -m xcue --help
python -m xcue pipeline run --help
python -m xcue l1 run --help
python -m xcue l2 run --help
python -m xcue l3 run --help
```
## BATCH-2A

- 任务：M2-01, M2-02
- 进入条件：所有前置依赖均为 `ACCEPTED`
- 完成条件：本批所有任务均为 `ACCEPTED`

```powershell
python -m pytest -q tests/integration/test_preflight.py tests/integration/test_run_identity.py
```
## BATCH-2B

- 任务：M2-07, M2-09
- 进入条件：所有前置依赖均为 `ACCEPTED`
- 完成条件：本批所有任务均为 `ACCEPTED`

```powershell
python -m pytest -q tests/integration/test_partial_success.py tests/integration/test_quarantine.py
```


## 首轮停止条件

出现以下任一情况，立即将当前任务置为 `BLOCKED` 并提交证据：

- 修复输入校验需要改变 L1 业务算法；
- 重构 CLI 同时要求迁移全部目录；
- 需要删除或覆盖历史运行记录；
- 测试通过依赖放宽 Schema；
- 需要重新引入隐式业务 fallback；
- 无法在新 attempt 中重试；
- 任务实际范围超出元数据列出的 modules 与 deliverables。

# 九、总依赖与里程碑门禁

```text
M0 + SCOPE
  → M1 输入、错误、CLI、状态
    → M2 运行事务、证据、部分成功
      → M3 规则控制面
      → M4 项目中立化
        → M5 Python 工程形态
          → M6 最小执行闭环
M7 文档治理按其明确依赖穿插执行
M8 在 M2—M7 对应门禁完成后执行
BIZ 不得阻断工程内核，但阻断业务判断权升级
```

禁止使用“某里程碑基本完成”作为依赖。唯一允许的判断是具体 task ID 是否为 `ACCEPTED`。

# 十、v1.1 计划书自身验收门槛

- [x] 所有任务具备 status；
- [x] 所有依赖为明确 task ID；
- [x] 建立完整问题追溯矩阵；
- [x] 补齐保留清理、未归属隔离、版本依赖、Fixture 边界；
- [x] 修正 M6 依赖链；
- [x] 严重度与执行顺序分离；
- [x] 首批拆分为串行子批次；
- [x] 首批验收命令为完整命令；
- [x] 过大任务拆成 Epic 与子任务；
- [x] 模糊验收指标已在相关任务中改为数值或确定行为；
- [x] 定义成熟度层级；
- [x] 每项任务包含 deliverables、modules、prohibitions 和 rollback 要求；
- [x] 存在版本变更记录；
- [x] JSON 台账通过依赖引用和 DAG 无环校验。

# 十一、最终工程验收门槛

只有以下全部成立，XC-UE 才可达到 `ENGINEERING_CORE_READY`：

- 非法输入在所有入口一致失败；
- 默认错误输出无裸 traceback；
- CLI 不透传未知 target 参数；
- 技术、业务、人工和发布状态分离；
- Preflight 失败不创建运行根；
- run/stage/attempt 不可覆盖；
- 中断可识别、可检查、可新 attempt 重试；
- 所有正式产物进入 Artifact Registry；
- 混合批次支持 item-level 部分成功；
- 结构化规则可通过行为突变测试证明真实生效；
- Python 不保留同义业务 fallback；
- 引擎不包含 TP-001 固定路径；
- 第二项目无需改引擎即可接入；
- 生产代码不修改 `sys.path`；
- wheel 可在全新环境安装、导入并运行 CLI；
- 至少一种确定性任务完成沙箱、diff、审批、应用、回流和回滚；
- 文档当前链接有效；
- unit/integration/CLI/acceptance 分层成立；
- CI 覆盖构建、测试、规则、文档、发布包和 Windows 回归；
- 最小正式规则集具备行为测试与回退证据。

达到上述条件后仍无自动发布权。业务指标必须完成 BIZ-01/02；正文自动修改必须按任务类型单独取得 `AUTO_EDIT_APPROVED`。

# 十二、版本变更与回退

- v1.0 保留为历史设计稿，不覆盖；
- v1.1 JSON 台账与 Markdown 计划书成对发布；
- 任何任务状态变更必须记录变更人、时间、原因和前后值；
- 若 v1.1 结构本身出现错误，回退到上一台账版本，不修改已产生的运行证据；
- 后续版本使用 v1.2、v1.3，不在 v1.1 文件上无痕覆盖。

# 十三、当前允许执行范围

在本计划书通过独立验收前，只允许执行：

```text
BATCH-0A：M0-01、M0-02
```

其余任务保持 `TODO`。

# 十四、结论

v1.1 已将 v1.0 从“整改设计稿”修正为“具备机读台账、明确依赖、问题追溯和分批门禁的待验收执行计划”。

当前文档状态仍是 `PENDING_ACCEPTANCE`，不能自行宣布冻结。独立验收通过后，才可将状态改为：

```text
FROZEN_FOR_EXECUTION
```
