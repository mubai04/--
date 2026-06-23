# SRN-U M0-02｜九类核心数据对象

> 文档编号：SRN-U-M0-02  
> 正式版本：v1.0  
> 文档状态：**FROZEN｜已冻结**  
> 冻结日期：2026-06-21  
> 工程阶段：M0｜框架与协议锁定  
> 上游基线：SRN-U-M0-01 v1.0 FROZEN  
> 文档用途：定义 SRN-U 第一阶段必须使用的九类核心数据对象、对象边界、最小字段、状态流转、引用关系和硬校验规则  
> 适用范围：M0 与 M1；M2 以后如需扩展字段，必须保持向后兼容或经过正式变更审查  
> 验收结果：PASS（经修订后通过）

---

## 1. 设计目标

SRN-U 的数据对象不是为了提前建设复杂数据库，而是为了回答五个基础问题：

1. 系统收到的创作需求是什么？
2. 当前小说项目已经被批准的核心定义是什么？
3. 小说当前真实处于什么状态？
4. 本轮准备选择和执行什么剧情？
5. 生成结果是否通过验收，并如何继承到下一章？

第一阶段只保留九类核心对象：

```text
1. ProjectBrief
2. ProjectSeed
3. NarrativeState
4. CharacterState
5. CandidatePath
6. ChapterBlueprint
7. ChapterDraft
8. AuditReport
9. StateSnapshot
```

这些对象组成最小数据流：

```text
ProjectBrief
→ ProjectSeed
→ NarrativeState
→ CandidatePath
→ ChapterBlueprint
→ ChapterDraft
→ AuditReport
→ StateSnapshot
```

其中 `CharacterState` 由 `NarrativeState` 引用和管理。

---

## 2. 共同设计原则

### 2.1 项目隔离

所有对象必须携带 `project_id`。

不同 `project_id` 的对象禁止互相引用。任何跨项目引用都属于硬错误。

### 2.2 事实、计划、候选与文本分离

不同对象承担不同身份：

```text
ProjectBrief：原始创作需求
ProjectSeed：已批准的项目种子
NarrativeState：当前有效事实与状态
CandidatePath：尚未执行的候选路径
ChapterBlueprint：已批准但尚未发生的章节计划
ChapterDraft：已生成但尚未成为事实的正文
AuditReport：对指定版本产物的检查结果
StateSnapshot：通过验收后冻结的事实快照
```

禁止把候选路径、章纲或草稿直接写入当前事实。

### 2.3 来源可追溯

对象中的关键字段必须能够指向来源：

```text
人工输入
上游对象
已批准正文
人工裁决
系统推演
审计结果
```

系统推演产生的内容必须显式标记，不能伪装成人工确认事实。

### 2.4 未知允许存在

不能确认的字段允许使用：

```text
UNKNOWN
UNDECIDED
DISPUTED
NOT_APPLICABLE
```

禁止为了填满字段而自行补全事实。

### 2.5 版本不可覆盖

对象修改后必须产生新版本。

旧版本可以标记为 `superseded`，但不能静默覆盖或删除。

### 2.6 状态回写受闸门控制

只有满足以下条件，章节结果才能进入正式叙事状态：

```text
ChapterDraft 已明确版本
+
AuditReport.result = PASS
+
已完成状态变更提取
+
已生成 StateSnapshot
```

`REWRITE`、`REPLAN`、`BLOCKED` 均禁止状态回写。

---

## 3. 公共元数据

九类对象共享以下最小元数据。

| 字段 | 含义 | 必填 |
|---|---|---|
| `object_id` | 对象唯一标识 | 是 |
| `object_type` | 对象类型 | 是 |
| `schema_version` | 数据结构版本 | 是 |
| `object_version` | 当前对象内容版本 | 是 |
| `project_id` | 所属小说项目 | 是 |
| `status` | 当前工作流状态 | 是 |
| `created_at` | 创建时间 | 是 |
| `updated_at` | 最后更新时间 | 是 |
| `source_refs` | 来源对象或人工输入引用 | 是 |
| `notes` | 补充说明 | 否 |

说明：

- 后文 YAML 仅作为业务结构示例，不是完整可直接投产的数据实例。
- 为避免样例重复，`notes` 可以省略；`created_at` 与 `updated_at` 在正式实现中仍为必填。
- 本冻结版示例已补入时间字段，以避免“必填字段在示例中缺失”的歧义。

第一阶段不强制规定具体标识格式，但建议：

```text
PB-0001        ProjectBrief
PS-0001        ProjectSeed
NS-CH0003      NarrativeState
CS-CHAR-001    CharacterState
CP-CH0004-A    CandidatePath
CB-CH0004      ChapterBlueprint
CD-CH0004-V01  ChapterDraft
AR-CH0004-V01  AuditReport
SS-CH0004      StateSnapshot
```

---

# 4. 对象一：ProjectBrief

## 4.1 对象职责

`ProjectBrief` 保存用户或创作者最初提供的创作需求。

它回答：

> 想写什么、写给谁、希望获得什么效果、有哪些明确限制？

它不是小说设定，也不是已经批准的项目方案。

## 4.2 最小字段

| 字段 | 含义 | 必填 |
|---|---|---|
| `operation_mode` | `create_new` / `continue_existing` / `revise_existing` | 是 |
| `target_platform` | 目标平台或发布环境 | 否 |
| `genre` | 题材类型 | 是 |
| `target_reader` | 目标读者 | 否 |
| `core_emotion` | 希望主要售卖的情绪 | 是 |
| `idea_statement` | 一句话创意 | 是 |
| `length_target` | 预期篇幅 | 否 |
| `must_have` | 必须包含的内容 | 否 |
| `must_avoid` | 禁止内容或作者禁区 | 否 |
| `style_preference` | 文风与阅读体验偏好 | 否 |
| `commercial_goal` | 商业目标 | 否 |
| `open_questions` | 尚未决定的问题 | 否 |

## 4.3 状态

```text
draft
ready
locked
superseded
invalid
```

只有 `ready` 或 `locked` 的 ProjectBrief 才能进入 ProjectSeed 生成。

## 4.4 硬校验

- `operation_mode`、`genre`、`core_emotion`、`idea_statement` 均为必填；无法确定时必须显式使用 `UNKNOWN`，不能静默缺失。
- `must_have` 与 `must_avoid` 出现直接冲突时，状态必须设为 `invalid`。
- 模糊内容可以保留为 `open_questions`，不能擅自决定。
- `create_new` 模式不得把尚未发生的设想写成小说事实。
- `continue_existing` 或 `revise_existing` 模式必须通过 `source_refs` 引用既有正文、设定或状态材料；既有事实随后由状态编译流程进入 NarrativeState，不能直接塞进 ProjectBrief。

## 4.5 最小示例

```yaml
object_id: PB-0001
object_type: ProjectBrief
schema_version: "1.0"
object_version: "1"
project_id: NOVEL-TEST-001
status: ready
created_at: 2026-06-21T00:00:00Z
updated_at: 2026-06-21T00:00:00Z
operation_mode: create_new
target_platform: 番茄
genre: 规则怪谈
target_reader: 偏好快节奏和强规则冲突的读者
core_emotion: 紧张中的偷赢感
idea_statement: 梦只能被遗忘，一个组织负责处理梦境泄漏
length_target: 100万字
must_have:
  - 现实世界与梦世界并行
must_avoid:
  - 系统面板式倒计时
open_questions:
  - 主角的职业尚未确定
source_refs:
  - USER-INPUT-001
```

---

# 5. 对象二：ProjectSeed

## 5.1 对象职责

`ProjectSeed` 是经过选择和批准的最小小说种子。

它回答：

> 这部小说究竟卖什么、靠什么持续运转、第一阶段为什么能够启动？

它必须比 ProjectBrief 更具体，但不能膨胀成完整世界百科。

## 5.2 最小字段

| 字段 | 含义 | 必填 |
|---|---|---|
| `project_title` | 项目工作名 | 是 |
| `one_sentence_promise` | 一句话卖点 | 是 |
| `content_source` | 持续提供剧情的核心内容源 | 是 |
| `lead_structure` | 单主角 / 双主角 / 群像等主导结构 | 是 |
| `lead_core` | 一个或多个核心人物的身份、欲望与缺口 | 是 |
| `primary_opposition` | 主要阻碍或对手压力 | 是 |
| `minimum_world_rules` | 启动故事所需最小规则 | 是 |
| `long_term_conflict` | 能支撑长篇的核心冲突 | 是 |
| `stage_one_goal` | 第一阶段目标 | 是 |
| `opening_hook` | 开篇吸引点 | 是 |
| `continuation_reason` | 读者继续读的理由 | 是 |
| `approved_constraints` | 已批准约束 | 是 |
| `rejected_directions` | 已明确拒绝的方向 | 否 |

## 5.3 状态

```text
candidate
approved
locked
superseded
rejected
```

只有 `approved` 或 `locked` 的 ProjectSeed 才能建立初始 NarrativeState。

## 5.4 硬校验

- `lead_structure` 必须明确支持单主角、双主角或群像，不能默认所有小说只有一个主角。
- `content_source` 必须能够解释作品如何持续产生新冲突。
- `long_term_conflict` 不能只是“主角不断升级”这类空泛表达。
- `minimum_world_rules` 只保留启动第一阶段所需规则。
- `opening_hook` 必须与核心卖点一致，不能是一次性欺骗性开头。
- 不得把尚未批准的候选设定写入 ProjectSeed。

## 5.5 最小示例

```yaml
object_id: PS-0001
object_type: ProjectSeed
schema_version: "1.0"
object_version: "1"
project_id: NOVEL-TEST-001
status: approved
created_at: 2026-06-21T00:00:00Z
updated_at: 2026-06-21T00:00:00Z
project_title: 梦只能被遗忘
one_sentence_promise: 当梦境泄漏进现实，处理员必须让所有知情者重新遗忘
content_source:
  primary: 不同梦境泄漏事件
  secondary: 组织内部对“应该遗忘什么”的权力斗争
lead_structure: 单主角
lead_core:
  identity: 新入职的梦境处理员
  desire: 查清自己为什么记得被全城遗忘的那场事故
  deficiency: 无法确定自己的记忆是否真实
primary_opposition:
  external: 失控梦境与违规知情者
  internal: 组织可能正在篡改主角记忆
minimum_world_rules:
  - 梦境被多人记住后会在现实中获得实体
  - 处理完成后相关记忆必须被清除
  - 主角保留某些本应被清除的记忆
long_term_conflict: 主角一边处理梦境泄漏，一边确认组织是否在用遗忘维持更大的谎言
stage_one_goal: 完成第一次独立处理，并发现自己的档案被删除
opening_hook: 一名陌生人准确说出主角昨夜已经忘掉的梦
continuation_reason: 每次案件都会改变读者对梦、现实和组织的理解
approved_constraints:
  - 现实与梦世界并行
  - 不使用系统面板
source_refs:
  - PB-0001
```

---

# 6. 对象三：NarrativeState

## 6.1 对象职责

`NarrativeState` 是当前创作轮次的规范叙事状态。

它回答：

> 到目前为止，故事真实发生了什么，当前有哪些有效约束和未解决问题？

NarrativeState 是规划和续写的唯一当前状态入口。

## 6.2 最小字段

| 字段 | 含义 | 必填 |
|---|---|---|
| `current_chapter` | 当前已批准章节位置 | 是 |
| `timeline_position` | 当前故事时间 | 是 |
| `current_locations` | 当前有效地点状态 | 是 |
| `stage_goal` | 当前阶段目标 | 是 |
| `active_conflicts` | 正在活动的冲突 | 是 |
| `confirmed_facts` | 已确认事实 | 是 |
| `world_rules` | 当前生效的世界规则 | 是 |
| `character_refs` | CharacterState 引用 | 是 |
| `open_threads` | 活动或冻结支线 | 是 |
| `obligations` | 尚未兑现的叙事债务 | 是 |
| `irreversible_changes` | 已发生不可逆变化 | 是 |
| `resource_state` | 关键资源状态 | 否 |
| `relationship_refs` | 关系状态引用或摘要 | 否 |
| `symbol_state` | 核心符号当前状态 | 否 |
| `unknowns` | 当前无法确认的内容 | 否 |
| `disputes` | 来源冲突或争议状态 | 否 |
| `next_pressure` | 下一轮必须处理的压力 | 是 |

## 6.3 状态

```text
initial
active
blocked
superseded
archived
```

`blocked` 表示存在关键冲突，禁止进入 CandidatePath 生成。

## 6.4 硬校验

- 所有 confirmed_facts 必须有来源。
- 世界规则冲突未解决时，NarrativeState 必须为 `blocked`。
- 未来计划不得出现在 confirmed_facts。
- 已废弃候选路径不得出现在当前事实中。
- 不可逆变化不得被后续状态静默删除。
- CharacterState 引用的项目必须与 NarrativeState 相同。
- unknowns 允许保留，但不得被当成确定前提使用。

## 6.5 最小示例

```yaml
object_id: NS-CH0001
object_type: NarrativeState
schema_version: "1.0"
object_version: "1"
project_id: NOVEL-TEST-001
status: active
created_at: 2026-06-21T00:00:00Z
updated_at: 2026-06-21T00:00:00Z
current_chapter: 1
timeline_position: 第一天凌晨
current_locations:
  protagonist: 城南旧公寓
stage_goal: 主角完成第一次梦境泄漏处理
active_conflicts:
  - 陌生人掌握主角已经遗忘的梦
confirmed_facts:
  - 主角收到组织的临时召回通知
  - 陌生人说出了梦中才存在的门牌号
world_rules:
  - 被多人记住的梦会实体化
character_refs:
  - CS-PROTAGONIST-001
open_threads:
  - 陌生人身份
  - 主角为何保留残余记忆
obligations:
  - 解释门牌号的来源
irreversible_changes:
  - 主角已经知道自己的遗忘过程可能失败
unknowns:
  - 陌生人是否属于组织
next_pressure: 在天亮前阻止更多人记住同一个梦
source_refs:
  - PS-0001
  - CD-CH0001-V01
  - AR-CH0001-V01
```

---

# 7. 对象四：CharacterState

## 7.1 对象职责

`CharacterState` 保存一个角色在当前时间点的动态状态。

它回答：

> 这个角色现在想做什么、知道什么、能做什么、付出了什么、与谁处于什么关系？

人物卡描述稳定特征，CharacterState 描述当前变化。第一阶段只定义动态状态。

对于次要或暂时退场角色，`current_desire` 可以使用 `UNKNOWN` 或 `NOT_APPLICABLE`；处于 `active` 状态的角色必须有可解释的 `current_goal`。

## 7.2 最小字段

| 字段 | 含义 | 必填 |
|---|---|---|
| `character_id` | 角色稳定标识 | 是 |
| `name` | 当前称呼 | 是 |
| `current_role` | 当前身份或职能 | 是 |
| `current_goal` | 当前主动目标 | 是 |
| `current_desire` | 更深层欲望 | 是 |
| `current_fear` | 当前主要恐惧 | 否 |
| `knowledge_confirmed` | 角色确认知道的内容 | 是 |
| `knowledge_suspected` | 角色怀疑但未确认的内容 | 否 |
| `knowledge_false` | 角色错误相信的内容 | 否 |
| `knowledge_forbidden` | 当前绝不应知道的内容 | 否 |
| `resources` | 当前资源 | 否 |
| `abilities` | 当前可用能力及来源 | 否 |
| `injuries_costs` | 伤害、代价与限制 | 否 |
| `relationship_positions` | 对关键角色的当前关系 | 否 |
| `commitments` | 已作出的承诺 | 否 |
| `irreversible_changes` | 人物不可逆变化 | 否 |
| `voice_markers` | 当前语言与观察倾向 | 否 |

## 7.3 状态

```text
active
inactive
missing
dead
superseded
archived
```

`dead` 不等于对象删除。死亡角色的知识、承诺和后果仍需保留。

## 7.4 硬校验

- abilities 必须能追溯来源。
- 角色行动不得使用 knowledge_forbidden 中的信息。
- current_goal 必须与已批准正文中的最近状态一致。
- injuries_costs 不能无来源消失。
- relationship_positions 发生重大变化时必须有事件依据。
- 角色核心欲望如被修改，必须经过人工审批或明确剧情事件。

## 7.5 最小示例

```yaml
object_id: CS-PROTAGONIST-001
object_type: CharacterState
schema_version: "1.0"
object_version: "1"
project_id: NOVEL-TEST-001
status: active
created_at: 2026-06-21T00:00:00Z
updated_at: 2026-06-21T00:00:00Z
character_id: CHAR-001
name: 林昼
current_role: 临时梦境处理员
current_goal: 在天亮前控制旧公寓的梦境泄漏
current_desire: 找回被组织删除的事故记忆
current_fear: 自己记得的一切都是被植入的
knowledge_confirmed:
  - 梦境被多人记住后会实体化
  - 自己的记忆清除不完整
knowledge_suspected:
  - 陌生人可能认识事故前的自己
knowledge_false:
  - 组织不知道自己的清除失败
knowledge_forbidden:
  - 组织删除档案的真实原因
resources:
  记忆封存针: 1
abilities:
  - name: 识别梦境污染
    source: 组织基础训练
injuries_costs:
  - 每次主动回忆都会加重耳鸣
relationship_positions:
  陌生人: 高度戒备
commitments:
  - 向上级承诺不单独进入梦境核心
irreversible_changes:
  - 已承认自己存在异常记忆残留
voice_markers:
  - 遇到恐惧时优先观察出口和门锁
source_refs:
  - PS-0001
  - CD-CH0001-V01
  - AR-CH0001-V01
```

---

# 8. 对象五：CandidatePath

## 8.1 对象职责

`CandidatePath` 是当前叙事前沿上的一条候选推进方案。

它回答：

> 在当前状态下，谁可以采取什么行动，这条路径需要什么前提，会造成什么后果？

CandidatePath 不是事实，也不是章纲。

## 8.2 最小字段

| 字段 | 含义 | 必填 |
|---|---|---|
| `planning_round` | 所属规划轮次 | 是 |
| `actor` | 主要行动者 | 是 |
| `action` | 核心行动 | 是 |
| `goal_served` | 服务的阶段目标 | 是 |
| `preconditions` | 成立前提 | 是 |
| `required_resources` | 所需资源 | 否 |
| `immediate_effects` | 即时后果 | 是 |
| `h3_effects` | 三章内可能后果 | 否 |
| `h10_risks` | 十章尺度风险 | 否 |
| `irreversible_commitment` | 可能造成的不可逆变化 | 否 |
| `threads_closed` | 可关闭的问题或支线 | 否 |
| `threads_opened` | 新增问题或支线 | 否 |
| `obligations_paid` | 兑现的叙事债务 | 否 |
| `obligations_created` | 新增债务 | 否 |
| `hard_gate_result` | 硬约束检查结果 | 是 |
| `tradeoffs` | 主要收益与代价 | 是 |
| `uncertainties` | 关键未知与假设 | 否 |
| `decision_reason` | 选择或淘汰理由 | 否 |

## 8.3 状态

```text
candidate
invalid
rejected
selected
latent
expired
executed
```

只有 `status = selected` 的 CandidatePath 可以生成 ChapterBlueprint。

`hard_gate_result` 只允许：

```text
PASS
FAIL
BLOCKED
```

`FAIL` 表示路径本身不合法；`BLOCKED` 表示因输入冲突或关键资料缺失而暂时无法判断。

## 8.4 硬校验

- preconditions 必须来自 NarrativeState 或明确假设。
- 硬闸门失败时必须标记为 `invalid`，不能进入评分比较。
- 不得通过新增无来源能力、资源或知识使路径成立。
- `status = selected` 时必须记录 `decision_reason`。
- 同一 planning_round 只能有一条主路径为 selected。
- latent 路径必须有明确触发条件，不能无限保留。

## 8.5 最小示例

```yaml
object_id: CP-CH0002-A
object_type: CandidatePath
schema_version: "1.0"
object_version: "1"
project_id: NOVEL-TEST-001
status: selected
created_at: 2026-06-21T00:00:00Z
updated_at: 2026-06-21T00:00:00Z
planning_round: ROUND-CH0002
actor: 林昼
action: 违背命令，跟随陌生人进入尚未实体化完成的梦境楼层
goal_served: 控制梦境泄漏并查明门牌号来源
preconditions:
  - 陌生人愿意带路
  - 梦境入口尚未封闭
required_resources:
  - 记忆封存针
immediate_effects:
  - 林昼获得接近梦境核心的机会
  - 违反组织命令
h3_effects:
  - 上级开始调查林昼
  - 陌生人与林昼形成暂时合作
h10_risks:
  - 主角可能提前暴露记忆清除失败
irreversible_commitment:
  - 林昼留下未经授权进入梦境核心的记录
threads_closed:
  - 门牌号是否真实存在
threads_opened:
  - 陌生人为什么能够自由进出梦境
obligations_created:
  - 解释组织为何禁止进入核心
hard_gate_result: PASS
tradeoffs:
  benefit: 同时推进案件与主角身世
  cost: 提前建立组织内部风险
uncertainties:
  - 陌生人的合作意图无法确认
decision_reason: 人物动机成立，推进两条核心冲突，且代价能够形成后续压力
source_refs:
  - NS-CH0001
  - CS-PROTAGONIST-001
```

---

# 9. 对象六：ChapterBlueprint

## 9.1 对象职责

`ChapterBlueprint` 把已选路径转换为可执行章节计划。

它回答：

> 本章从什么状态出发，通过哪些场景和选择，抵达什么新状态？

ChapterBlueprint 是计划，不是已发生事实。

## 9.2 最小字段

| 字段 | 含义 | 必填 |
|---|---|---|
| `chapter_number` | 章节编号 | 是 |
| `selected_path_ref` | 已选择路径引用 | 是 |
| `start_state_ref` | 起始 NarrativeState | 是 |
| `chapter_goal` | 本章唯一主目标 | 是 |
| `start_condition` | 开场状态 | 是 |
| `end_condition` | 目标结束状态 | 是 |
| `main_actor` | 主要行动者 | 是 |
| `primary_resistance` | 核心阻力 | 是 |
| `critical_choice` | 关键选择 | 是 |
| `irreversible_change` | 本章不可逆变化 | 是 |
| `scene_sequence` | 场景顺序 | 是 |
| `information_plan` | 信息隐藏、暗示、释放安排 | 是 |
| `pacing_trajectory` | 节奏状态序列 | 是 |
| `payoff` | 当章兑现 | 否 |
| `ending_pressure` | 章末留下的有效压力 | 是 |
| `must_preserve` | 正文不得破坏的内容 | 是 |
| `must_avoid` | 正文禁止出现的内容 | 否 |
| `acceptance_checks` | 本章验收检查项 | 是 |

## 9.3 状态

```text
draft
review_ready
approved
replan_required
superseded
cancelled
```

只有 `approved` 的 ChapterBlueprint 可以进入 ChapterDraft 生成。

## 9.4 硬校验

- 必须引用一条 selected CandidatePath。
- chapter_goal 只能有一个主目标；可有次级作用，但不得并列多个主目标。
- end_condition 必须与 start_condition 存在可追溯状态变化。
- critical_choice 必须由角色作出或明确承受。
- irreversible_change 可以较小，但不能完全为空。
- information_plan 不能让角色使用其不知道的信息。
- ending_pressure 必须来自本章后果，不能凭空新增无关危机。

## 9.5 最小示例

```yaml
object_id: CB-CH0002
object_type: ChapterBlueprint
schema_version: "1.0"
object_version: "1"
project_id: NOVEL-TEST-001
status: approved
created_at: 2026-06-21T00:00:00Z
updated_at: 2026-06-21T00:00:00Z
chapter_number: 2
selected_path_ref: CP-CH0002-A
start_state_ref: NS-CH0001
chapter_goal: 林昼确认门牌号在梦境中真实存在
start_condition: 旧公寓梦境入口正在缩小，组织命令林昼立即撤离
end_condition: 林昼进入不存在的十三层，并留下违规记录
main_actor: 林昼
primary_resistance: 入口即将关闭且上级禁止进入
critical_choice: 服从命令撤离，或跟随陌生人进入核心
irreversible_change: 林昼主动违反第一次正式命令
scene_sequence:
  - 场景1：组织开始封锁公寓
  - 场景2：陌生人指出电梯中不存在的十三层
  - 场景3：林昼在封锁完成前做出选择
  - 场景4：电梯门打开，里面出现梦中的门牌号
information_plan:
  hide:
    - 陌生人的真实身份
  hint:
    - 组织人员看不到十三层按钮
  reveal:
    - 门牌号确实存在于梦境核心
  delay:
    - 主角为何记得这里
pacing_trajectory:
  - 压缩
  - 延迟
  - 加速
  - 悬停
payoff:
  - 第一章门牌号承诺得到局部兑现
ending_pressure: 电梯门关闭后，组织系统显示林昼仍站在一楼
must_preserve:
  - 林昼不知道组织删除档案的原因
  - 记忆封存针只有一支
must_avoid:
  - 陌生人直接解释全部真相
acceptance_checks:
  - 主角必须主动做出违规选择
  - 本章必须确认门牌号存在
  - 章末异常必须由已建立规则产生
source_refs:
  - CP-CH0002-A
```

---

# 10. 对象七：ChapterDraft

## 10.1 对象职责

`ChapterDraft` 保存依据指定 ChapterBlueprint 生成的正文版本。

它回答：

> 这一版正文具体写了什么，它依据哪个蓝图，当前处于什么审阅状态？

ChapterDraft 在通过验收前不属于正式事实。草稿版本统一使用公共字段 `object_version`，不再设置第二套 `draft_version`。

## 10.2 最小字段

| 字段 | 含义 | 必填 |
|---|---|---|
| `chapter_number` | 章节编号 | 是 |
| `blueprint_ref` | 对应 ChapterBlueprint | 是 |
| `text` | 正文内容 | 是 |
| `generation_mode` | 初稿、局部重写、人工修改等 | 是 |
| `changed_ranges` | 相对上一版修改的位置 | 否 |
| `preserved_constraints` | 已遵守的关键约束 | 否 |
| `known_deviations` | 生成时已发现的偏差 | 否 |
| `word_count` | 字数 | 否 |
| `author_interventions` | 人工修改记录 | 否 |

## 10.3 状态

```text
generated
review_ready
rewrite_required
replan_required
approved
discarded
superseded
```

只有 `approved` 的 ChapterDraft 才能参与状态回写。

## 10.4 硬校验

- 必须引用 approved ChapterBlueprint。
- 草稿版本必须明确，AuditReport 只能审计指定版本。
- 正文不能自行修改 ProjectSeed 或 NarrativeState 中的硬事实。
- 发生计划外但合理的新事实时，必须记录为 known_deviations，等待审计裁决。
- 局部重写必须记录 changed_ranges。
- 草稿不得因为“读起来不错”而自动设为 approved。

## 10.5 最小示例

```yaml
object_id: CD-CH0002-V01
object_type: ChapterDraft
schema_version: "1.0"
object_version: "1"
project_id: NOVEL-TEST-001
status: review_ready
created_at: 2026-06-21T00:00:00Z
updated_at: 2026-06-21T00:00:00Z
chapter_number: 2
blueprint_ref: CB-CH0002
generation_mode: initial_generation
text: |
  （此处存放完整章节正文）
preserved_constraints:
  - 林昼未获知组织删除档案的原因
  - 记忆封存针未被额外增加
known_deviations:
  - 陌生人在生成中表现出比蓝图更强的熟悉感，需要审计是否提前泄露
word_count: 2380
source_refs:
  - CB-CH0002
```

---

# 11. 对象八：AuditReport

## 11.1 对象职责

`AuditReport` 对指定对象版本进行独立检查，并决定下一步路由。

它回答：

> 哪里出了什么问题、证据是什么、影响多大、应该局部重写、重新规划还是阻断？

## 11.2 最小字段

| 字段 | 含义 | 必填 |
|---|---|---|
| `target_ref` | 被审计对象及精确版本 | 是 |
| `audit_scope` | 审计范围 | 是 |
| `result` | PASS / REWRITE / REPLAN / BLOCKED | 是 |
| `findings` | 问题清单 | 是 |
| `hard_gate_findings` | 硬约束问题 | 否 |
| `soft_findings` | 语言、节奏等软问题 | 否 |
| `evidence_refs` | 证据位置 | 是 |
| `root_causes` | 根因判断 | 否 |
| `impact_range` | 影响范围 | 是 |
| `allowed_changes` | 允许修改内容 | 是 |
| `protected_content` | 禁止修改内容 | 是 |
| `repair_route` | 修复入口 | 否 |
| `retest_requirements` | 复验要求 | 是 |
| `confidence` | 审计置信度 | 是 |
| `unknowns` | 无法判断的内容 | 否 |

## 11.3 结果定义

### PASS

```text
允许进入状态变更提取和 StateSnapshot
```

### REWRITE

```text
正文局部问题
→ 保留 ChapterBlueprint
→ 定向修改 ChapterDraft
→ 生成新草稿版本
→ 重新审计
```

### REPLAN

```text
章纲或路径错误
→ 禁止局部文字修补掩盖结构问题
→ 返回 ChapterBlueprint 或 CandidatePath
```

### BLOCKED

```text
事实、人物、规则、来源或状态存在关键冲突
→ 停止推进
→ 等待补输入或人工裁决
```

## 11.4 硬校验

- target_ref 必须指向精确版本。
- result 必须与 findings 严重程度一致。
- 发现硬约束错误时，不得给 PASS。
- allowed_changes 与 protected_content 不得直接冲突。
- REWRITE 必须指出具体修改范围。
- REPLAN 必须说明退回到 ChapterBlueprint 还是 CandidatePath。
- BLOCKED 必须列出解除阻断所需条件。
- 审计器不能直接修改目标对象。

## 11.5 最小示例

```yaml
object_id: AR-CH0002-V01
object_type: AuditReport
schema_version: "1.0"
object_version: "1"
project_id: NOVEL-TEST-001
status: final
created_at: 2026-06-21T00:00:00Z
updated_at: 2026-06-21T00:00:00Z
target_ref: CD-CH0002-V01
audit_scope:
  - 因果
  - 角色知识
  - 信息释放
  - 重复
  - 章末推进
result: REWRITE
findings:
  - id: F-001
    type: 信息提前泄露
    location: 第31至34段
    description: 陌生人的说法让读者几乎确认其属于组织，超过蓝图允许的暗示程度
    severity: medium
soft_findings:
  - id: F-002
    type: 重复解释
    location: 第18段
    description: 动作已经表现林昼犹豫，后一句再次直接说明“他犹豫了”
    severity: low
evidence_refs:
  - CD-CH0002-V01#P31-P34
  - CD-CH0002-V01#P18
root_causes:
  - 对陌生人熟悉度的生成约束不清
impact_range: 仅影响当前章节，不影响已批准历史状态
allowed_changes:
  - 第18段删除直接情绪说明
  - 第31至34段降低陌生人对组织流程的显性熟悉度
protected_content:
  - 林昼必须主动进入十三层
  - 门牌号必须得到局部确认
repair_route: ChapterDraft 局部重写
retest_requirements:
  - 重新检查信息泄露
  - 重新检查章末异常是否仍成立
confidence: 0.91
source_refs:
  - CD-CH0002-V01
  - CB-CH0002
```

---

# 12. 对象九：StateSnapshot

## 12.1 对象职责

`StateSnapshot` 是一个章节通过验收并完成状态回写后的不可变记录。

它回答：

> 在某个批准节点，正文、状态、人物、决策和审计结果共同构成了什么正式事实版本？

StateSnapshot 是回滚和追溯的基础。

## 12.2 最小字段

| 字段 | 含义 | 必填 |
|---|---|---|
| `chapter_number` | 对应章节 | 是 |
| `approved_draft_ref` | 已批准正文版本 | 是 |
| `audit_report_ref` | PASS 审计报告 | 是 |
| `previous_snapshot_ref` | 上一个快照 | 否 |
| `narrative_state_ref` | 新 NarrativeState | 是 |
| `character_state_refs` | 新 CharacterState 集合 | 是 |
| `state_changes` | 本章造成的状态变更 | 是 |
| `facts_added` | 新增正式事实 | 是 |
| `facts_revised` | 经正式裁决修改的事实 | 否 |
| `obligations_updated` | 债务变化 | 否 |
| `threads_updated` | 支线变化 | 否 |
| `irreversible_changes` | 新增不可逆变化 | 否 |
| `decision_record_refs` | 路径选择记录 | 是 |
| `rollback_scope` | 回滚时应恢复的范围 | 是 |

## 12.3 状态

```text
frozen
superseded
invalidated
archived
```

快照业务内容创建后不得原地修改。若需要标记 `superseded`、`invalidated` 或 `archived`，必须产生新的 `object_version`，且原快照内容保持可追溯。

## 12.4 硬校验

- approved_draft_ref 必须指向 approved ChapterDraft。
- audit_report_ref 的 result 必须为 PASS。
- NarrativeState 与 CharacterState 必须属于同一 project_id。
- state_changes 必须能追溯到已批准正文。
- 不得把章纲中的未执行计划写入快照事实。
- rollback_scope 必须能够恢复正文、状态与决策记录。
- 新快照必须引用 previous_snapshot_ref，初始快照除外。

## 12.5 最小示例

```yaml
object_id: SS-CH0002
object_type: StateSnapshot
schema_version: "1.0"
object_version: "1"
project_id: NOVEL-TEST-001
status: frozen
created_at: 2026-06-21T00:00:00Z
updated_at: 2026-06-21T00:00:00Z
chapter_number: 2
approved_draft_ref: CD-CH0002-V02
audit_report_ref: AR-CH0002-V02
previous_snapshot_ref: SS-CH0001
narrative_state_ref: NS-CH0002
character_state_refs:
  - CS-PROTAGONIST-002
state_changes:
  - 林昼从一楼进入梦境十三层
  - 林昼产生一次未经授权的违规记录
facts_added:
  - 门牌号在梦境核心真实存在
  - 组织系统未能记录林昼的实际位置
obligations_updated:
  - 第一章门牌号承诺：局部兑现
  - 新增：解释组织系统为何无法定位林昼
threads_updated:
  - 陌生人身份：继续活动
  - 主角记忆残留：继续活动
irreversible_changes:
  - 林昼主动违反正式命令
decision_record_refs:
  - CP-CH0002-A
rollback_scope:
  - 章节2正文
  - 章节2后新增状态
  - 章节2后产生的路径规划
source_refs:
  - CD-CH0002-V02
  - AR-CH0002-V02
```

---

# 13. 九类对象关系

```text
ProjectBrief
    │ 生成并批准
    ▼
ProjectSeed
    │ 初始化
    ├──────────────► 初始 CharacterState
    └──────────────► 初始 NarrativeState
                          │ 引用当前 CharacterState
                          ▼
                    CandidatePath
                          │ 选择一条
                          ▼
                   ChapterBlueprint
                          │ 执行
                          ▼
                     ChapterDraft
                          │ 审计
                          ▼
                     AuditReport
                   ┌──────┼───────────┬───────────┐
                   │      │           │           │
                 PASS  REWRITE     REPLAN      BLOCKED
                   │      │           │           │
                   │      └─回草稿    └─回蓝图/路径
                   │
                   ▼
          状态变更提取与增量编译
                   │
          ┌────────┴─────────┐
          ▼                  ▼
新 CharacterState      新 NarrativeState
          └────────┬─────────┘
                   ▼
              StateSnapshot
                   │
                   ▼
             下一轮规划入口
```

### 13.1 引用无环规则

同一快照生成周期内，业务对象引用必须形成有向无环关系：

```text
上一 StateSnapshot / ProjectSeed
→ 已批准 ChapterDraft + PASS AuditReport
→ 新 CharacterState
→ 新 NarrativeState
→ 新 StateSnapshot
```

允许 `NarrativeState` 引用当前 `CharacterState`；禁止当前 `CharacterState` 反向引用同版本 `NarrativeState`，从而形成循环依赖。

---

# 14. 对象权限边界

| 对象 | 可以影响什么 | 禁止直接影响什么 |
|---|---|---|
| ProjectBrief | ProjectSeed 候选 | NarrativeState、正文事实 |
| ProjectSeed | 初始状态与项目约束 | 已发布章节事实 |
| NarrativeState | 路径生成与章纲约束 | 自动生成正文 |
| CharacterState | 人物可行动空间 | 自行改变项目卖点 |
| CandidatePath | 路径选择 | 直接写入事实 |
| ChapterBlueprint | 正文生成约束 | 自动成为已发生事实 |
| ChapterDraft | 审计与修订 | 未经PASS进入状态 |
| AuditReport | 路由修复与验收 | 直接修改被审计对象 |
| StateSnapshot | 冻结某一批准节点的状态、正文、审计与决策组合 | 被原地覆盖 |

---

# 15. 最小工作流

## 15.1 从零启动

```text
ProjectBrief.ready
→ ProjectSeed.approved
→ 初始 NarrativeState
→ 初始 CharacterState
```

## 15.2 写一章

```text
NarrativeState.active
→ CandidatePath.candidate
→ CandidatePath.selected
→ ChapterBlueprint.approved
→ ChapterDraft.review_ready
→ AuditReport
```

## 15.3 审计分流

```text
PASS
→ ChapterDraft.approved
→ 状态变更提取
→ StateSnapshot.frozen

REWRITE
→ 新 ChapterDraft 版本
→ 新 AuditReport

REPLAN
→ 新 ChapterBlueprint 或 CandidatePath
→ 原草稿 superseded

BLOCKED
→ 停止推进
→ 补输入或人工裁决
```

---

# 16. 跨对象硬闸门

以下任一命中，系统必须阻断：

1. 不同 project_id 的对象互相引用。
2. CandidatePath 未 selected 就生成 ChapterBlueprint。
3. ChapterBlueprint 未 approved 就生成正式 ChapterDraft。
4. AuditReport 没有指向精确草稿版本。
5. AuditReport 为 REWRITE、REPLAN 或 BLOCKED，却进行状态回写。
6. ChapterDraft 未 approved 就进入 StateSnapshot。
7. StateSnapshot 引用非 PASS 审计。
8. NarrativeState 把计划或候选路径当成已发生事实。
9. CharacterState 使用角色不应知道的信息。
10. 快照被原地修改而没有生成新版本。
11. 来源缺失却把推测标记为确认事实。
12. 已发生不可逆变化在后续状态中无依据消失。
13. 同一快照周期内出现 NarrativeState 与 CharacterState 的同版本循环引用。
14. 同一业务含义被两套字段重复表达并可能产生冲突，例如 `status` 与第二套决策状态。

---

# 17. 当前不建立的对象

M0 与 M1 暂不单独建立：

```text
WorldBible
StyleProfile
ReaderModel
PlatformModel
InformationLedger
CausalLedger
ThreadLedger
ObligationLedger
SymbolLedger
RelationshipGraph
LifecycleReport
```

这些能力暂时作为 `NarrativeState`、`CharacterState`、`ChapterBlueprint` 或 `AuditReport` 的内部字段存在。

只有满足以下条件时，才允许拆成独立对象：

1. 内部字段过大，已经无法稳定维护；
2. 被至少两个核心模块独立读写；
3. 有明确生命周期；
4. 有独立验收需求；
5. 拆分后能降低而不是增加系统复杂度。

---

# 18. M1最小使用范围

根据 M0-01 v1.0 FROZEN，M1不能跳过“路径选择、正文审计、状态回写”。因此九类对象在M1均必须出现，但允许使用最小形态：

```text
ProjectBrief       必须
ProjectSeed        必须
NarrativeState     必须，允许初始简化状态
CharacterState     必须，至少包含核心人物
CandidatePath      必须，允许单候选模式
ChapterBlueprint   必须
ChapterDraft       必须
AuditReport        必须
StateSnapshot      必须
```

单候选模式只表示暂时不比较多条路径，不表示可以把 CandidatePath 与 ChapterBlueprint 合并。

M1结束时必须生成 StateSnapshot，否则“单章创作闭环”并未真正闭合。

---

# 19. 本文件验收标准

本文件满足以下条件才可冻结：

1. 九类对象均有唯一职责，不存在两个对象处理同一身份。
2. 事实、计划、候选、草稿和快照被明确分离。
3. 对象之间形成从创作输入到状态继承的完整数据链。
4. 每个对象都有最小字段，而不是无边界字段集合。
5. 每个对象都有明确状态。
6. 每个对象都有硬校验规则。
7. 审计结果能够明确路由到 PASS、REWRITE、REPLAN、BLOCKED。
8. 未通过审计的正文不能进入正式状态。
9. StateSnapshot 可支持追溯和回滚。
10. 当前未提前扩展为复杂数据库或几十种对象。
11. 所有设计与 M0-01 v1.0 FROZEN 一致。
12. M1 可以基于这些对象建立最小单章闭环。

---


# 20. 验收与冻结记录

## 20.1 验收结果

```text
结果：PASS
性质：经修订后通过
正式版本：v1.0
冻结日期：2026-06-21
```

## 20.2 验收中发现并修正的问题

1. **公共必填字段与示例不一致**  
   已为示例补入 `created_at`、`updated_at`，并明确样例与投产实例的区别。

2. **ProjectBrief只支持从零创作**  
   新增 `operation_mode`，支持新建、续写既有项目和修订既有项目。

3. **ProjectSeed默认单主角**  
   将 `protagonist_core` 改为 `lead_structure + lead_core`，支持单主角、双主角和群像。

4. **CandidatePath存在双重身份字段**  
   删除重复的 `path_id` 与 `decision_status`，统一使用 `object_id + status`。

5. **ChapterDraft存在双重版本字段**  
   删除 `draft_version`，统一使用 `object_version`。

6. **StateSnapshot存在双重标识与双重冻结字段**  
   删除 `snapshot_id` 与 `freeze_status`，统一使用 `object_id + status`。

7. **示例形成同版本循环引用**  
   修正 NarrativeState 与 CharacterState 的来源引用，增加引用无环规则。

8. **M1允许跳过路径和状态对象**  
   该设计违反 M0-01 的冻结基线。现已改为九类对象在M1均必须出现，但允许最小实现。

9. **NarrativeState与StateSnapshot边界不够明确**  
   现明确：NarrativeState 是当前可供规划读取的规范状态；StateSnapshot 是不可变检查点和回滚入口。

## 20.3 十二项验收结果

| 验收项 | 结果 |
|---|---|
| 九类对象职责唯一 | PASS |
| 事实、计划、候选、草稿、快照分离 | PASS |
| 数据链完整 | PASS |
| 字段保持最小范围 | PASS |
| 对象状态明确 | PASS |
| 硬校验完整 | PASS |
| 四类审计路由明确 | PASS |
| 未通过审计不得回写 | PASS |
| 快照支持追溯与回滚 | PASS |
| 未提前扩展复杂数据库 | PASS |
| 与 M0-01 v1.0 一致 | PASS |
| M1可据此建立单章闭环 | PASS |

## 20.4 冻结范围

本次冻结：

- 九类核心对象的身份与边界
- 公共元数据
- 最小字段
- 状态集合
- 硬校验
- 对象关系
- 跨对象闸门
- M1最小使用范围

本次不冻结：

- 具体数据库类型
- JSON Schema / YAML Schema实现
- 文件目录结构
- API接口
- 编程语言类定义
- 字段长度、枚举编码与存储格式
- M2以后拆分出的账本对象

## 20.5 已知上游风险

M0-01要求章节蓝图包含“不可逆变化”。本文件按上游冻结基线保留该要求。若M1实测证明该要求对过渡章、余波章或纯关系章过强，必须通过正式变更申请同时审查M0-01与M0-02，不能在下游静默放宽。


# 21. 当前结论

九类对象分别承担：

```text
ProjectBrief       保存原始创作需求
ProjectSeed        保存已批准小说种子
NarrativeState     保存当前规范叙事状态
CharacterState     保存角色当前动态状态
CandidatePath      保存尚未执行的剧情方案
ChapterBlueprint   保存已批准章节计划
ChapterDraft       保存具体正文版本
AuditReport        保存独立检查和修复路由
StateSnapshot      保存通过验收后的不可变检查点；它不替代 NarrativeState
```

最小可信链条为：

```text
需求
→ 项目种子
→ 当前状态
→ 候选路径
→ 章节计划
→ 正文草稿
→ 独立审计
→ 冻结快照
→ 新状态
```

当前文件只定义数据契约，不代表对象已经程序化实现。


---

## 22. 冻结后的变更规则

本文件已冻结为 v1.0。

后续修改必须满足：

```text
提出变更原因
→ 标明受影响对象与字段
→ 检查对M0-01和下游文件的影响
→ 更新测试案例
→ 升级文档版本
→ 保留旧冻结版
```

禁止直接覆盖本文件。
