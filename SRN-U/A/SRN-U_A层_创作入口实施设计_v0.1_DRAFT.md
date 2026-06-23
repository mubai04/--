# SRN-U A层｜创作入口实施设计

> 文件定位：A层唯一实施设计与新对话接续文件  
> 当前状态：DRAFT｜等待实际实现验证  
> 上游依据：M0-01 至 M0-06 v1.0 FROZEN  
> 目标实现文件：`runtime/a_entry.py`  
> 原则：先纵向跑通A—H，不再继续制造M系列说明文件

---

# 1. A层唯一目标

A层只做一件事：

> 把用户的真实创作需求，转换为一份可被人工批准、可交给B层建立初始状态的 ProjectSeed。

A层不负责：

- 写正文；
- 生成章节蓝图；
- 决定下一章剧情；
- 建立 NarrativeState；
- 模拟读者；
- 预测平台推荐；
- 扩写完整世界观；
- 自动批准重大创作方向。

---

# 2. A层最小运行链

```text
原始创作输入
→ G0：项目与来源检查
→ ProjectBrief
→ A层编译
→ ProjectSeed.candidate
→ 人工批准 / 退回修改 / 拒绝
→ ProjectSeed.approved
→ G1：项目种子启动闸门
→ 交给B-INIT
```

A层有两个动作：

```text
compile
approve
```

不再拆成更多子模块。

---

# 3. 目标代码文件

第一版只建立一个代码文件：

```text
runtime/a_entry.py
```

该文件内部包含：

```text
1. ProjectBrief最小结构
2. ProjectSeed最小结构
3. G0输入检查
4. ProjectBrief校验
5. ProjectSeed编译
6. G1启动校验
7. 人工批准与版本更新
8. A层运行入口
```

暂时不拆成：

```text
a_validator.py
a_compiler.py
a_approval.py
a_router.py
```

只有在单文件已经真实运行、职责明显膨胀后才允许拆分。

---

# 4. A层运行入口

目标函数：

```python
run_a_layer(
    raw_input,
    source_ref,
    project_id=None,
    action="compile",
    previous_brief=None,
    previous_seed=None,
    human_decision=None,
)
```

参数含义：

| 参数 | 含义 |
|---|---|
| `raw_input` | 用户原始创作需求，文本或字典 |
| `source_ref` | 原始输入来源标识 |
| `project_id` | 已有项目标识；新项目可以为空 |
| `action` | `compile` 或 `approve` |
| `previous_brief` | 修改既有ProjectBrief时使用 |
| `previous_seed` | 修改既有ProjectSeed时使用 |
| `human_decision` | `approve` / `revise` / `reject` |

A层不得从聊天上下文中暗中补充关键条件。未提供的信息必须：

```text
写入 UNKNOWN
或
进入 open_questions
```

---

# 5. 运行结果

`run_a_layer()`返回一个运行信封：

```yaml
layer: A
action: compile
gate:
  current: G1
  result: PASS
project_id: NOVEL-0001
project_brief: {}
project_seed: {}
issues: []
next_action: human_approve
evidence_refs:
  - USER-INPUT-001
```

运行信封不是第十类核心数据对象，不写入正式真源。

正式保存的对象只有：

```text
ProjectBrief
ProjectSeed
```

允许的 `next_action`：

```text
human_approve
revise_brief
supply_sources
B_INIT
stop
```

---

# 6. G0｜项目与来源检查

## 6.1 新项目

当：

```text
project_id为空
operation_mode=create_new
```

A层入口应：

```text
生成唯一project_id
→ 记录source_ref
→ 创建ProjectBrief
```

第一版项目标识可采用：

```text
NOVEL-YYYYMMDD-序号
```

## 6.2 既有项目

当：

```text
operation_mode=continue_existing
或
operation_mode=revise_existing
```

必须满足：

```text
project_id存在
source_refs存在
既有材料可读取
```

否则：

```text
gate_result = BLOCKED
next_action = supply_sources
```

## 6.3 G0硬失败

```text
跨项目对象混入
来源无法识别
既有项目没有project_id
续写或修订没有既有材料
同名对象出现多个当前真源
```

---

# 7. ProjectBrief最小结构

```yaml
object_id:
object_type: ProjectBrief
schema_version: "1.0"
object_version: "1"
project_id:
status: ready
created_at:
updated_at:

operation_mode:
target_platform:
genre:
target_reader:
core_emotion:
idea_statement:
length_target:
must_have: []
must_avoid: []
style_preference:
commercial_goal:
open_questions: []
source_refs: []
```

## 7.1 必须输入

以下字段不得静默缺失：

```text
operation_mode
genre
core_emotion
idea_statement
```

无法确定时写：

```text
UNKNOWN
```

但如果 `idea_statement = UNKNOWN`，ProjectBrief只能保持：

```text
status = draft
```

不得进入ProjectSeed编译。

## 7.2 ProjectBrief校验

硬校验：

```text
operation_mode必须合法
must_have与must_avoid不得直接冲突
续写/修订必须有source_refs
原始输入不得被系统暗中改写
```

软问题：

```text
项目名未定
平台未定
目标读者较宽
篇幅未定
次要文风未定
```

软问题进入 `open_questions`，不自动阻断。

---

# 8. ProjectSeed最小结构

```yaml
object_id:
object_type: ProjectSeed
schema_version: "1.0"
object_version: "1"
project_id:
status: candidate
created_at:
updated_at:

project_title:
one_sentence_promise:
content_source:
lead_structure:
lead_core:
primary_opposition:
minimum_world_rules: []
long_term_conflict:
stage_one_goal:
opening_hook:
continuation_reason:
approved_constraints: []
rejected_directions: []
source_refs: []
```

A层第一次编译只能产生：

```text
ProjectSeed.status = candidate
```

不得直接自动产生：

```text
approved
locked
```

---

# 9. ProjectSeed编译规则

## 9.1 project_title

来源：

```text
用户明确名称
或
系统生成工作名
```

系统生成时必须标记为：

```text
工作名
```

不得假装是用户最终决定。

## 9.2 one_sentence_promise

必须同时回答：

```text
主角或核心人物面对什么
核心异常或机制是什么
读者将持续获得什么体验
```

禁止空话：

```text
主角一路变强
主角改变命运
这是一个波澜壮阔的故事
```

## 9.3 content_source

必须说明剧情如何持续产生，而不是描述结果。

合格：

```text
不同梦境泄漏事件
每次换壳带来的身份与污染冲突
不同职业委托及其规则代价
```

不合格：

```text
主角不断升级
主角一路打脸
剧情越来越精彩
```

## 9.4 lead_structure与lead_core

必须支持：

```text
单主角
双主角
群像
```

`lead_core`至少包含：

```text
identity
desire
deficiency
```

## 9.5 primary_opposition

至少包含一种持续阻力：

```text
具体对手
组织压力
制度规则
环境危险
人物内部冲突
```

禁止只写：

```text
困难很多
敌人很强
世界很危险
```

## 9.6 minimum_world_rules

只保留启动第一阶段必需规则。

第一版建议：

```text
1—5条
```

超过5条时，A层应警告：

```text
项目种子可能已经膨胀成世界百科
```

但不因此自动BLOCKED。

## 9.7 long_term_conflict

必须同时包含：

```text
持续对立双方
无法一次解决的根因
冲突升级方式
```

## 9.8 stage_one_goal

必须是可执行阶段结果，不是抽象愿望。

合格：

```text
完成第一次独立任务，并发现自己的档案被删除
```

不合格：

```text
成长
变强
探索世界
```

## 9.9 opening_hook

必须与 `one_sentence_promise` 同源。

禁止：

```text
用与核心故事无关的爆炸、追杀或倒计时骗开篇
```

## 9.10 continuation_reason

回答：

> 第一章之后，读者为什么仍有稳定的新内容可读？

必须来自：

```text
content_source
long_term_conflict
人物未解决欲望
```

---

# 10. G1｜项目种子启动闸门

ProjectSeed只有满足以下条件才可进入人工批准：

```text
one_sentence_promise具体
content_source可持续
lead_structure明确
lead_core完整
primary_opposition成立
minimum_world_rules足以启动
long_term_conflict可持续
stage_one_goal可执行
opening_hook与核心卖点一致
approved_constraints没有冲突
```

## 10.1 G1结果

### 可批准

```text
gate.result = PASS
ProjectSeed.status = candidate
next_action = human_approve
```

### 需要修改

```text
gate.result = BLOCKED
ProjectSeed.status = rejected
next_action = revise_brief
```

### 需要补既有材料

```text
gate.result = BLOCKED
next_action = supply_sources
```

---

# 11. 人工批准

人工决策：

```text
approve
revise
reject
```

## approve

```text
ProjectSeed.candidate
→ 创建新object_version
→ ProjectSeed.approved
→ next_action = B_INIT
```

必须记录：

```text
批准内容
批准时间
批准来源
被接受的未决风险
```

## revise

```text
ProjectSeed保持candidate
→ 返回A层重新编译
```

不得原地覆盖旧版本。

## reject

```text
ProjectSeed.status = rejected
→ next_action = stop
```

---

# 12. A层禁止行为

A层禁止：

```text
自动把ProjectSeed设为approved
擅自替用户决定核心卖点
为了平台数据修改用户禁止项
生成完整世界观百科
生成第一章章纲
生成角色当前状态
生成正文
决定CandidatePath
把候选设定写成已发生事实
从其他小说复制项目种子
用总分替代具体G1判断
```

---

# 13. A层最小错误分类

第一版只保留五种错误，不扩大分类体系：

```text
A_INPUT_MISSING
A_INPUT_CONFLICT
A_SOURCE_MISSING
A_SEED_INVALID
A_APPROVAL_REQUIRED
```

错误结构：

```yaml
code:
field:
message:
evidence:
repair_action:
```

示例：

```yaml
code: A_INPUT_CONFLICT
field: must_have / must_avoid
message: 同一项目同时要求和禁止系统面板
evidence:
  - PB-0001.must_have[0]
  - PB-0001.must_avoid[0]
repair_action: 由用户选择保留一项
```

---

# 14. A层最小测试

第一版实现后只测以下10项：

| 编号 | 测试 | 预期 |
|---|---|---|
| A-T01 | 新项目无project_id | 自动分配后继续 |
| A-T02 | create_new完整输入 | 生成PB.ready与PS.candidate |
| A-T03 | idea_statement缺失 | PB.draft，不生成PS |
| A-T04 | must_have与must_avoid冲突 | BLOCKED |
| A-T05 | continue_existing无source_refs | BLOCKED |
| A-T06 | content_source只写“不断变强” | PS.rejected |
| A-T07 | opening_hook与卖点无关 | PS.rejected |
| A-T08 | 合法candidate等待人工批准 | 不得进入B |
| A-T09 | 人工approve | 新版本PS.approved，进入B_INIT |
| A-T10 | 人工revise | 保留旧版本，重新编译 |

A层通过标准：

```text
10项全部有实际结果
不存在自动批准
不存在跨项目污染
不存在原始输入被覆盖
approved ProjectSeed能够被B-INIT读取
```

---

# 15. A层产物保存位置

第一版只需要：

```text
runs/<project_id>/A/
├─ input.txt
├─ project_brief.yaml
├─ project_seed.yaml
└─ run_log.yaml
```

说明：

- `input.txt`保存原始输入，不允许覆盖；
- `project_brief.yaml`保存当前ProjectBrief版本；
- `project_seed.yaml`保存当前ProjectSeed版本；
- 旧版本进入同目录下的 `history/`；
- `run_log.yaml`只记录运行与审批，不是核心数据对象。

不得先建立复杂数据库。

---

# 16. 与B层的唯一交接

A层只向B层交付：

```yaml
handoff:
  from: A
  to: B_INIT
  project_id:
  project_seed_ref:
  project_seed_version:
  gate: G1
  gate_result: PASS
  approval_ref:
```

B层只接受：

```text
ProjectSeed.status = approved
或
ProjectSeed.status = locked
```

否则拒绝启动。

---

# 17. A层完成判定

A层不是“文件写完”就算完成。

必须同时满足：

```text
runtime/a_entry.py可以运行
10项最小测试有actual_result
至少生成一份真实ProjectBrief
至少生成一份真实ProjectSeed.candidate
人工批准后生成ProjectSeed.approved新版本
approved版本成功交给B_INIT
所有产物可追溯到原始输入
```

---

# 18. 新对话接续任务

在新对话中只执行以下任务：

> 根据本文件实现 `runtime/a_entry.py`，使用Python、本地文件、无API、单文件优先。先完成A-T01至A-T10，不设计B—H，不新增M系列文档。实现中若遇到阻断字段，只做最小修正并明确记录，不重新扩张架构。

新对话需要同时提供：

```text
1. 本文件
2. M0-02 v1.0 FROZEN
3. M0-03 v1.0 FROZEN
4. M0-04 v1.0 FROZEN
```

M0-01、M0-05、M0-06作为背景基线，不是实现A层的必需输入。

---

# 19. 当前结论

A层第一版不是一组新文档，而是：

```text
一个Python文件
两个正式对象
两个动作
两个闸门
十个测试
一条B层交接
```

执行边界：

```text
原始需求
→ ProjectBrief
→ ProjectSeed.candidate
→ 人工批准
→ ProjectSeed.approved
→ B_INIT
```

除这条链外，第一版A层不做任何扩展。
