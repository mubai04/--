# SRN-U M0-05｜最小闭环测试案例与验收样本

> 文档编号：SRN-U-M0-05  
> 正式版本：v1.0  
> 文档状态：**FROZEN｜已冻结**  
> 冻结日期：2026-06-21  
> 验收结果：PASS（经修订后通过）  
> 工程阶段：M0｜框架与协议锁定  
> 上游基线：  
> - SRN-U-M0-01 v1.0 FROZEN  
> - SRN-U-M0-02 v1.0 FROZEN  
> - SRN-U-M0-03 v1.0 FROZEN  
> - SRN-U-M0-04 v1.0 FROZEN  
> 文档用途：建立 SRN-U 最小单章闭环的测试夹具、黄金路径、失败样本、审计结果样本、原子提交测试和M1最低验收集  
> 适用范围：M0验收与M1实现前测试设计  
> 说明：本文中的小说内容仅是测试夹具，不属于SRN-U通用核心

---

# 1. 测试目标

M0-05 不验证“小说是否好看”。

它验证的是：

1. 九类核心对象能否形成完整数据链；
2. A—H八层能否按契约交接；
3. G0—G8九个主闸门能否正确阻断和放行；
4. PASS、REWRITE、REPLAN、BLOCKED能否正确路由；
5. 未通过正文是否会被错误写入状态；
6. 新旧状态能否原子切换；
7. StateSnapshot能否支持追溯和回滚；
8. 高层错误是否会被错误地交给低层润色。

测试通过不代表作品具备商业价值，也不代表正文达到签约水平。

---

# 2. 测试夹具

## 2.1 测试项目

```text
project_id：NOVEL-TEST-001
项目名：梦只能被遗忘
题材：现实异象 / 规则悬疑
测试目标：完成第一章最小闭环，并生成第一份冻结快照
```

## 2.2 最小项目规则

```text
R1：被多人记住的梦会在现实中获得实体。
R2：梦境泄漏处理完成后，相关记忆必须被清除。
R3：主角林昼的记忆清除存在异常残留。
R4：主角当前不知道组织删除自己档案的真实原因。
R5：记忆封存针是一次性资源，初始数量为1。
```

## 2.3 核心人物

```text
姓名：林昼
当前身份：临时梦境处理员
当前目标：在天亮前控制旧公寓的梦境泄漏
深层欲望：找回被组织删除的事故记忆
当前限制：主动回忆会加重耳鸣
知识边界：不知道组织删除档案的原因
资源：记忆封存针 ×1
```

## 2.4 第一章测试目标

```text
主目标：
林昼确认陌生人掌握了自己残余梦境中的门牌号1307，并发现该梦境信息开始侵入现实。

必须发生：
- 陌生人说出门牌号“1307”
- 林昼发现现实公寓只有12层
- 组织发来撤离命令
- 林昼在撤离确认前提交“无新增异常”，没有上报门牌号

必须保留：
- 林昼不知道陌生人的真实身份
- 林昼不知道档案删除原因
- 封存针数量仍为1

章末压力：
电梯显示屏短暂出现“13”，但监控记录中没有这一帧。
```

---

# 3. 测试对象最小链

## 3.1 测试夹具表达规则

本文中的 YAML 主要用于表达测试断言，不重复抄写M0-02中的全部公共元数据。

除“缺失字段测试”明确删除某字段外，每个正向样本默认同时满足：

```text
object_type 正确
schema_version = 1.0
object_version 明确
created_at / updated_at 合法
source_refs 可追溯
M0-02规定的其他必填字段已由有效基础夹具补齐
```

因此：

- 正向样本中未显示的必填字段，视为由基础有效夹具提供；
- 负向样本只改变该测试明确指出的字段；
- 不得利用“样本省略字段”掩盖本应失败的问题；
- AuditReport 的对象 `status` 枚举仍属于上游已知缺口，本文只断言 `result`，不自行新增状态语义。

M0-05验证对象身份、关键业务字段与交接，不替代未来的完整Schema测试。

```text
PB-0001
→ PS-0001
→ NS-INIT-0001 / CS-LINZHOU-0001
→ CP-CH0001-A
→ CB-CH0001
→ CD-CH0001-V01
→ AR-CH0001-V01
→ NS-CH0001 / CS-LINZHOU-0002
→ SS-CH0001
```

---

# 4. 黄金路径测试

## T05-GOLD-01｜完整单章闭环

### 前置条件

- 当前不存在同名活动项目；
- project_id已分配；
- 所有对象属于NOVEL-TEST-001；
- 无历史快照；
- ProjectBrief状态为ready。

### G0预期

```text
PASS
→ project_id = NOVEL-TEST-001
→ A层
```

### 输入

```yaml
ProjectBrief:
  object_id: PB-0001
  project_id: NOVEL-TEST-001
  operation_mode: create_new
  genre: 现实异象 / 规则悬疑
  core_emotion: 紧张中的偷赢感
  idea_statement: 梦被多人记住后会进入现实，一个记忆清除失败的处理员开始怀疑组织
  status: ready
```

### 预期A层输出

```yaml
ProjectSeed:
  object_id: PS-0001
  project_id: NOVEL-TEST-001
  status: approved
  one_sentence_promise: 处理梦境泄漏的人，必须先决定哪些记忆应该被世界遗忘
  content_source:
    - 不同梦境泄漏事件
    - 组织内部对记忆处置权的争夺
  lead_structure: 单主角
  stage_one_goal: 完成第一次独立处理并发现自己的档案异常
```

### G1预期

```text
PASS
→ B-INIT
```

### B-INIT预期输出

```yaml
NarrativeState:
  object_id: NS-INIT-0001
  project_id: NOVEL-TEST-001
  status: active
  current_chapter: 0
  stage_goal: 完成第一次独立处理
  confirmed_facts:
    - 林昼是临时梦境处理员
    - 封存针数量为1
  next_pressure: 旧公寓出现梦境泄漏警报
```

```yaml
CharacterState:
  object_id: CS-LINZHOU-0001
  project_id: NOVEL-TEST-001
  status: active
  current_goal: 在天亮前控制泄漏
  knowledge_confirmed:
    - 昨夜被清除的梦仍残留门牌号1307
  knowledge_forbidden:
    - 组织删除档案的原因
  resources:
    记忆封存针: 1
```

### G2预期

```text
PASS
→ C层
```

### C层预期输出

```yaml
CandidatePath:
  object_id: CP-CH0001-A
  project_id: NOVEL-TEST-001
  status: selected
  actor: 林昼
  action: 在撤离确认前隐瞒门牌号，先验证陌生人为何知道1307
  preconditions:
    - 陌生人说出1307
    - 林昼记得梦中出现过1307
  hard_gate_result: PASS
  tradeoffs:
    benefit: 同时推进案件与主角记忆异常
    cost: 主角承担隐瞒信息的风险
```

### G3预期

```text
PASS
→ D层
```

### D层预期输出

```yaml
ChapterBlueprint:
  object_id: CB-CH0001
  project_id: NOVEL-TEST-001
  status: approved
  chapter_goal: 林昼确认陌生人掌握梦中的1307，并发现它开始侵入现实
  critical_choice: 在撤离确认前提交“无新增异常”，隐瞒1307
  irreversible_change: 林昼形成一条无法撤销的虚假现场回报记录
  ending_pressure: 电梯显示13，但监控中没有记录
```

### G4预期

```text
PASS
→ E层 / F层
```

### E层正文最小样本

```text
陌生人隔着门说：“十三楼，零七室。”

林昼没有回答。

旧公寓的楼层表贴在电梯边，从一排到十二。最下面是物业盖的蓝章，日期是三年前。

他却记得十三楼。

不是这里的十三楼。

是昨夜那个已经被清掉的梦里，电梯门打开时，正对着一块掉漆的门牌：1307。

手机震了一下。

组织发来的撤离命令只有六个字：污染未明，立即退出。

林昼把门牌号从上报栏里删掉，勾选“无新增异常”。

他按下提交。

回执跳出来：现场报告已记录，无法撤回。

电梯显示屏闪了一下。

12。

13。

再回到12。

他抬头看向墙角监控。回放里，数字从12直接跳回了12。
```

### E层预期对象

```yaml
ChapterDraft:
  object_id: CD-CH0001-V01
  project_id: NOVEL-TEST-001
  object_version: "1"
  status: review_ready
  chapter_number: 1
  blueprint_ref: CB-CH0001
  generation_mode: initial_generation
  text_ref: 本节“E层正文最小样本”
  known_deviations: []
  preserved_constraints:
    - 林昼不知道陌生人的真实身份
    - 林昼不知道组织删除档案的原因
    - 记忆封存针仍为1
  source_refs:
    - CB-CH0001
```

### F层预期

```text
CONTINUE
```

不得触发：

```text
知识泄漏
章节目标偏离
人物动机偏离
```

### G5预期

```text
PASS
→ G层正式审计
```

### G层预期审计

```yaml
AuditReport:
  object_id: AR-CH0001-V01
  project_id: NOVEL-TEST-001
  object_version: "1"
  target_ref: CD-CH0001-V01
  audit_scope:
    - 因果
    - 人物动机
    - 知识边界
    - 状态连续性
    - 重复与AI味
    - 章末推进
  result: PASS
  hard_gate_findings: []
  findings:
    - type: 轻度节奏风险
      severity: low
      disposition: accepted
  evidence_refs:
    - CD-CH0001-V01#P01-P18
  impact_range: 不影响事实、路径与状态回写
  allowed_changes: []
  protected_content:
    - 虚假现场回报记录
    - 电梯显示13但监控无记录
  retest_requirements: []
  confidence: 0.88
  unknowns: []
  source_refs:
    - CD-CH0001-V01
    - CB-CH0001
```

### G6预期

```text
PASS
→ H-P1
→ CD-CH0001-V01：review_ready → approved
```

### B-UPDATE预期输出

```yaml
NarrativeState:
  object_id: NS-CH0001
  project_id: NOVEL-TEST-001
  status: initial
  current_chapter: 1
  confirmed_facts:
    - 陌生人知道门牌号1307
    - 现实公寓公开楼层只有12层
    - 林昼记得梦中存在1307
    - 电梯显示屏曾出现13
    - 监控没有记录13
    - 林昼向组织提交了“无新增异常”的不可撤回现场报告
    - 林昼未向组织上报1307
  irreversible_changes:
    - 林昼形成一条无法撤销的虚假现场回报记录
  next_pressure: 在组织抵达前确认1307是否正在现实中实体化
```

```yaml
CharacterState:
  object_id: CS-LINZHOU-0002
  project_id: NOVEL-TEST-001
  status: active
  current_goal: 在组织接管现场前找到1307
  resources:
    记忆封存针: 1
  commitments:
    - 继续承担隐瞒1307所产生的调查风险
```

### G7预期

```text
PASS
→ 形成预提交状态包
```

预提交断言：

```text
旧 NarrativeState 仍为 active
新 NarrativeState 为 initial
新 NarrativeState.character_refs 指向 CS-LINZHOU-0002
当前规划仍只读取旧 active NarrativeState
尚未创建本轮 frozen StateSnapshot
```

CharacterState 的“当前版本”由 active NarrativeState 的引用决定；新角色状态在提交前不得被当前规划读取。

### G8预期原子提交

```text
1. 创建 SS-CH0001，status = frozen
2. NS-INIT-0001：active → superseded
3. NS-CH0001：initial → active
4. CS-LINZHOU-0001：active → superseded
5. CS-LINZHOU-0002保持active，并由NS-CH0001引用
6. CP-CH0001-A：selected → executed
7. 第一章工作流：已批准并已回写状态
```

### H层预期快照

```yaml
StateSnapshot:
  object_id: SS-CH0001
  project_id: NOVEL-TEST-001
  object_version: "1"
  status: frozen
  chapter_number: 1
  approved_draft_ref: CD-CH0001-V01
  audit_report_ref: AR-CH0001-V01
  narrative_state_ref: NS-CH0001
  character_state_refs:
    - CS-LINZHOU-0002
  state_changes:
    - 林昼提交不可撤回的虚假现场回报
    - 梦中楼层13开始在现实设备上显现
  facts_added:
    - 陌生人知道1307
    - 现实楼层表只有12层
    - 电梯显示13但监控无记录
  obligations_updated:
    - 新增：解释陌生人为何知道1307
    - 新增：解释组织系统为何未记录13
  threads_updated:
    - 1307实体化：active
    - 陌生人身份：active
  irreversible_changes:
    - 虚假现场回报已进入组织记录
  decision_record_refs:
    - CP-CH0001-A
  rollback_scope:
    - 第一章路径之后的全部对象
  source_refs:
    - CD-CH0001-V01
    - AR-CH0001-V01
    - NS-CH0001
    - CS-LINZHOU-0002
```

首章允许 `previous_snapshot_ref` 为空。

### 最终断言

```text
恰好一个 active NarrativeState
恰好一个 frozen StateSnapshot
封存针仍为1
林昼仍不知道档案删除原因
虚假现场回报已进入正式事实
未执行计划没有进入confirmed_facts
NS-CH0001只引用CS-LINZHOU-0002
下一轮可以从NS-CH0001进入C层
```

### 测试结果

```text
预期：PASS
```

---

# 5. G0测试｜项目与来源

## T05-G0-01｜新项目无project_id

### 输入

```text
用户提交一句话创意，但尚未分配project_id。
```

### 预期

```text
G0分配唯一project_id
→ A层创建ProjectBrief
```

不得判定为跨项目错误。

---

## T05-G0-02｜跨项目对象引用

### 输入

```text
NOVEL-TEST-001的ChapterBlueprint
引用NOVEL-TEST-002的CharacterState
```

### 预期

```text
BLOCKED
→ H层隔离检查
```

不得自动复制角色状态。

---

## T05-G0-03｜同名双真源

### 输入

```text
两个ChapterDraft都声称自己是CH0001当前正式正文
且没有superseded关系
```

### 预期

```text
BLOCKED
→ H层真源核查
→ 人工裁决
```

---

# 6. G1测试｜项目种子

## T05-G1-01｜ProjectSeed未批准

### 输入

```text
ProjectSeed.status = candidate
```

### 预期

```text
G1 FAIL
→ A层
```

---

## T05-G1-02｜内容源不足

### 输入

```text
content_source：主角不断变强
```

### 预期

```text
G1 FAIL
```

理由：

```text
“不断变强”是结果，不是持续产生冲突的内容源。
```

---

## T05-G1-03｜必须项与禁止项冲突

### 输入

```text
must_have：使用系统面板显示规则
must_avoid：禁止任何系统面板
```

### 预期

```text
BLOCKED
→ A层或人工裁决
```

---

# 7. G2测试｜叙事状态

## T05-G2-01｜双active状态

### 输入

```text
NS-A.status = active
NS-B.status = active
project_id相同
```

### 预期

```text
G2 BLOCKED
→ H层核查提交历史
```

---

## T05-G2-02｜不可逆变化消失

### 前状态

```text
林昼已经公开承认自己记忆清除失败。
```

### 新状态

```text
没有任何新事件依据，却恢复为“组织完全不知道”。
```

### 预期

```text
G2 FAIL
→ B层
```

---

## T05-G2-03｜角色知识污染

### 输入

```text
CharacterState.knowledge_confirmed包含：
“组织删除档案是为了掩盖事故”
```

但正文和人工裁决都没有提供该事实。

### 预期

```text
BLOCKED
→ B层清理知识状态
```

---

# 8. G3测试｜候选路径

## T05-G3-01｜使用未知信息

### 路径

```text
林昼直接前往组织秘密档案库，
因为他知道档案被藏在那里。
```

### 状态

```text
林昼不知道档案库位置。
```

### 预期

```text
CandidatePath.status = invalid
```

---

## T05-G3-02｜凭空增加资源

### 路径

```text
林昼连续使用三支封存针。
```

### 状态

```text
封存针数量为1。
```

### 预期

```text
CandidatePath.status = invalid
```

---

## T05-G3-03｜同轮双selected

### 输入

```text
CP-A.status = selected
CP-B.status = selected
planning_round相同
```

### 预期

```text
G3 FAIL
→ C层修正
```

---

## T05-G3-04｜唯一合法路径

### 输入

```text
仅CP-A通过全部硬闸门。
```

### 预期

```text
允许CP-A selected
```

不能因为没有多条可比较路径而自动失败。

---

# 9. G4测试｜章节蓝图

## T05-G4-01｜章末危机无来源

### 蓝图

```text
章末突然出现世界毁灭倒计时。
```

此前没有规则、角色或事件支持。

### 预期

```text
G4 FAIL
→ D层
```

---

## T05-G4-02｜伪悬念

### 蓝图

```text
主角与上级当面交谈，
但双方都故意不提眼前最关键的信息，
唯一理由是“留到下一章”。
```

### 预期

```text
G4 FAIL
→ D层
```

---

## T05-G4-03｜场景功能重复

### 蓝图

```text
连续三个场景都只是在重复说明主角害怕。
```

### 预期

```text
软失败
→ D层局部调整
```

不得直接BLOCKED。

---

## T05-G4-04｜无状态变化

### 蓝图

```text
开头和结尾人物、事实、关系、资源、知识均无变化。
```

### 预期

```text
G4 FAIL
```

---

# 10. G5测试｜草稿可审计性

## T05-G5-01｜草稿无版本

### 输入

```text
ChapterDraft.object_version缺失
```

### 预期

```text
G5 FAIL
→ E层或H层版本核查
```

---

## T05-G5-02｜生成残片

### 输入

正文末尾为：

```text
林昼抬起手，接下来他准备……
```

并标记为完整章节。

### 预期

```text
G5 FAIL
→ E层
```

---

## T05-G5-03｜重写未记录changed_ranges

### 输入

```text
generation_mode = partial_rewrite
changed_ranges = 空
```

### 预期

```text
G5 FAIL
```

---

# 11. G6测试｜审计结果

## T05-G6-01｜PASS样本

条件：

```text
没有硬约束错误
软问题已接受或低风险
target_ref精确匹配
复验要求完成
```

预期：

```text
PASS
→ H-P1
```

---

## T05-G6-02｜REWRITE样本

### 正文

```text
林昼握紧封存针，指节发白。
他很紧张。
他的内心充满紧张。
```

### 判断

```text
动作已表达紧张，后两句重复解释。
```

### 预期AuditReport

```text
result = REWRITE
repair_route = E层局部重写
protected_content = 封存针仍在林昼手中
```

---

## T05-G6-03｜REPLAN样本

### 蓝图与正文

```text
林昼没有任何理由，主动把唯一封存针交给陌生人。
```

### 判断

该问题不是措辞问题，而是：

```text
人物动机
资源风险
关键选择
```

均未成立。

### 预期

```text
result = REPLAN
→ D层
必要时返回C层
```

禁止只改一句心理描写后继续。

---

## T05-G6-04｜BLOCKED样本

### 状态冲突

```text
规则A：任何梦境实体都不能被普通摄像头记录。
规则B：第一章确认普通摄像头完整记录了梦境实体。
```

两条都被标记为当前硬规则或确认事实。

### 预期

```text
result = BLOCKED
→ B层状态核查
→ 必要时人工裁决
```

---

## T05-G6-05｜审计报告自身无效

### 输入

```text
findings中存在角色知识泄漏
result却为PASS
```

### 预期

```text
G6 FAIL
→ G层重做AuditReport
```

---

# 12. G7测试｜新状态预提交

## T05-G7-01｜写入未执行计划

### 蓝图

```text
下一章准备让组织封锁城市。
```

### 第一章正文

```text
尚未发生城市封锁。
```

### 新状态错误写入

```text
confirmed_facts：组织已经封锁城市。
```

### 预期

```text
G7 FAIL
→ B-UPDATE
```

---

## T05-G7-02｜资源数量错误

### 批准正文

```text
封存针未使用。
```

### 新状态

```text
封存针数量变为0。
```

### 预期

```text
G7 FAIL
```

---

## T05-G7-03｜新状态提前active

### 输入

```text
旧NarrativeState仍为active
新NarrativeState也为active
```

### 预期

```text
G7 FAIL
```

正确状态：

```text
旧状态：active
新状态：initial
```

---

## T05-G7-04｜未批准草稿触发状态编译

### 输入

```text
ChapterDraft.status = review_ready
AuditReport.result = REWRITE
却调用B-UPDATE生成新状态
```

### 预期

```text
G7前置条件失败
→ 禁止B-UPDATE
→ 返回G层 / E层
```

不得产生预提交状态包。

---

# 13. G8测试｜原子提交

## T05-G8-01｜完整提交

### 前置

```text
G7已通过
新状态为initial
旧状态为active
尚未创建本轮快照
```

### 预期

一个事务内完成：

```text
创建frozen快照
旧状态→superseded
新状态→active
selected路径→executed
```

最终：

```text
恰好一个active状态
恰好一个本轮frozen快照
```

---

## T05-G8-02｜提交中断

### 模拟故障

```text
快照内容已在事务缓冲区构造，
但尚未冻结时，新状态激活步骤发生错误。
```

### 预期

```text
整个事务不生效
旧状态继续active
新状态保持initial或被废弃
不留下frozen快照
路径仍保持selected
记录提交失败
```

不得出现半提交。

---

## T05-G8-03｜快照引用非PASS审计

### 输入

```text
StateSnapshot.audit_report_ref
指向result = REWRITE的AuditReport
```

### 预期

```text
G8 FAIL
不创建冻结快照
```

---

## T05-G8-04｜快照链断裂

### 输入

```text
第二章快照没有previous_snapshot_ref
```

### 预期

```text
G8 FAIL
→ H层恢复
```

---

# 14. 人工审批测试

## T05-AP-01｜修改主角核心欲望

### 请求

```text
将林昼的核心欲望从“找回被删除的事故记忆”
改为“成为组织最高领导者”。
```

### 预期

```text
进入人工审批门
不得由C、D、E、F或G自动修改
```

---

## T05-AP-02｜重写已发布第一章

### 请求

```text
删除第一章中林昼隐瞒1307的行为。
```

### 影响

该行为已经进入：

```text
NarrativeState
CharacterState
StateSnapshot
后续路径
```

### 预期

```text
人工审批
→ 影响范围分析
→ 从第一章蓝图开始定向回滚
```

---

## T05-AP-03｜新增推翻旧因果的世界规则

### 请求

```text
新增规则：主角可以随时让任何记忆失效，且没有代价。
```

### 预期

```text
人工审批
```

因为它会推翻现有内容源、冲突和资源约束。

---

# 15. 高层错误不得低层修补测试

## T05-HL-01｜蓝图级资源错误不能靠换词修复

### 已知状态

```text
林昼只有一支封存针。
```

### 错误蓝图与正文

```text
蓝图要求林昼连续消耗两支封存针，
正文也执行了两次消耗。
```

### 错误处理方式

```text
只把正文中的“第二支”改成“另一支”。
```

### 预期

```text
拒绝
→ 返回D层重做资源使用方案
→ 若路径本身依赖两支封存针，再返回C层
```

说明：若蓝图合法、只有正文误写“第二支”，则属于E层正文错误；本测试专门验证蓝图级资源错误不得被表面润色掩盖。

---

## T05-HL-02｜路径错误不能靠补心理描写修复

### 错误

```text
林昼无理由背叛当前目标。
```

### 错误处理方式

```text
加一句“他突然改变了主意”。
```

### 预期

```text
拒绝
→ REPLAN
```

---

## T05-HL-03｜没有状态变化不能靠强断章修复

### 错误

整章没有任何实际推进。

### 错误处理方式

```text
末尾突然写“他不知道，灾难已经开始”。
```

### 预期

```text
拒绝
→ D层重做章节目标和状态变化
```

---

# 16. 软检查样本

## T05-SOFT-01｜局部重复

```text
结果：REWRITE或警告
不得BLOCKED
```

## T05-SOFT-02｜轻度句式均匀

```text
结果：记录AI味风险
需要具体文本证据
```

## T05-SOFT-03｜章末力度一般但因果成立

```text
结果：软问题
可REWRITE
不得自动REPLAN
```

## T05-SOFT-04｜同章术语较多

```text
结果：认知负荷警告
检查是否需要删减或延迟解释
```

---

# 17. 重复失败升级测试

## T05-REP-01｜同一知识泄漏反复出现

### 第一次

```text
REWRITE
→ E层修复
```

### 第二次仍出现

```text
检查ChapterBlueprint的信息计划
→ 可能升级REPLAN
```

### 持续出现

```text
检查CharacterState知识边界或生成约束
→ 人工复核
```

不得无限自动重写。

---

# 18. 回滚测试

## T05-RB-01｜蓝图污染后的定向回滚

### 情况

第一章已经冻结，第二章已经规划但未生成。

随后发现第一章蓝图让主角使用了错误知识，且该错误进入第一章正文和快照。

### 预期回滚范围

```text
第一章ChapterBlueprint
第一章ChapterDraft
第一章AuditReport
第一章NarrativeState / CharacterState
第一章StateSnapshot
第二章CandidatePath及其后续对象
```

### 必须保留

```text
旧版本链
错误原因
invalidated / superseded标记
人工审批记录
```

---

## T05-RB-02｜提交事务失败不算正式回滚

### 情况

H-P2尚未完成，快照没有正式冻结。

### 预期

```text
撤销未完成事务
保留旧active状态
不创建正式回滚链
记录提交失败即可
```

---

# 19. 测试执行记录模板

每次测试至少记录：

```yaml
test_id:
test_version:
project_id:
upstream_versions:
input_objects:
preconditions:
execution_steps:
expected_gate:
expected_result:
actual_result:
evidence_refs:
pass_or_fail:
failure_type:
failure_layer:
repair_route:
retest_required:
tester:
executed_at:
notes:
```

---

# 20. M1最低验收集

M1实现前，不要求运行本文全部测试。

最低必须通过：

```text
T05-GOLD-01 完整单章闭环
T05-G0-01 新项目无project_id
T05-G0-02 跨项目引用
T05-G1-01 ProjectSeed未批准
T05-G2-01 双active状态
T05-G3-01 使用未知信息
T05-G3-02 凭空增加资源
T05-G4-01 无来源章末危机
T05-G5-01 草稿无版本
T05-G6-02 REWRITE
T05-G6-03 REPLAN
T05-G6-04 BLOCKED
T05-G6-05 审计报告自身无效
T05-G7-01 写入未执行计划
T05-G7-03 新状态提前active
T05-G7-04 未批准草稿触发状态编译
T05-G8-02 原子提交中断
T05-G8-03 快照引用非PASS审计
T05-AP-01 修改主角核心欲望
T05-HL-03 强断章掩盖无推进
```

M1只有同时满足以下条件才算通过：

1. 黄金路径能够从ProjectBrief运行到StateSnapshot；
2. REWRITE、REPLAN、BLOCKED能正确返回责任层；
3. 未通过草稿不能进入NarrativeState；
4. 角色未知信息不能进入合法路径；
5. 无来源资源不能进入正文；
6. 新旧状态不会同时active；
7. 提交中断不会留下半冻结快照；
8. 第一份快照能够作为下一轮规划入口；
9. PASS报告必须精确匹配获批草稿版本；
10. 黄金路径的关键事实、资源和知识边界均可追溯。

---

# 21. M0-05自身验收标准

本文件满足以下条件才可冻结：

1. 包含一条完整黄金路径。
2. 黄金路径覆盖九类核心对象。
3. 黄金路径覆盖A—H八层。
4. 黄金路径覆盖G0—G8九个闸门。
5. 包含PASS样本。
6. 包含REWRITE样本。
7. 包含REPLAN样本。
8. 包含BLOCKED样本。
9. 包含人工审批样本。
10. 包含高层错误拒绝低层修补样本。
11. 包含原子提交失败样本。
12. 包含正式回滚样本。
13. 包含重复失败升级样本。
14. 包含M1最低验收集。
15. 不引入第十类核心对象。
16. 测试夹具与SRN-U通用核心明确隔离。
17. 与M0-01至M0-04冻结基线一致。
18. 测试结果可由明确断言判定，不依赖模糊总分。
19. 黄金路径中的正文、审计和快照均有可验证对象身份。
20. 测试样本省略字段的规则明确，不会把不完整对象误判为有效对象。

---

# 22. 验收与冻结记录

## 22.1 验收结果

```text
结果：PASS
性质：经修订后通过
正式版本：v1.0
冻结日期：2026-06-21
```

## 22.2 验收中发现并修正的问题

1. **黄金路径没有显式经过G0**  
   已增加新项目入口的G0通过步骤。

2. **黄金路径缺少可验证的ChapterDraft对象**  
   已补入草稿对象身份、版本、状态、蓝图引用和保护约束。

3. **黄金路径缺少StateSnapshot样本**  
   已补入首章冻结快照及其正文、审计、状态、人物和路径引用。

4. **章节目标与正文结果互相矛盾**  
   原目标声称1307“只存在于梦中”，正文却让13侵入现实。现改为确认陌生人掌握梦中1307，并发现其开始侵入现实。

5. **所谓不可逆变化实际上可以撤销**  
   “暂不上报”可在之后补报。现改为提交不可撤回的“无新增异常”虚假现场回报，并在正文、蓝图、状态和快照中统一继承。

6. **CandidatePath前置知识没有进入CharacterState**  
   已补入林昼对梦中1307的残余记忆。

7. **PASS AuditReport缺少必要审计证据**  
   已补入审计范围、证据位置、影响范围、保护内容和复验要求。

8. **预提交阶段人物状态引用不明确**  
   已说明当前性由active NarrativeState的character_refs决定；新角色状态在提交前不得被当前规划读取。

9. **原子提交没有处理旧CharacterState版本**  
   已在黄金路径中补入旧角色状态转superseded、新状态由新NarrativeState引用。

10. **提交中断措辞可能暗示快照已冻结**  
    已改为“事务缓冲区已构造但尚未冻结”。

11. **缺少未批准草稿禁止状态编译测试**  
    新增T05-G7-04。

12. **高层资源错误测试路由错误且场景含混**  
    已明确区分：正文误词返回E层；蓝图依赖不存在资源则返回D/C层。

13. **M1最低集未显式覆盖部分关键闸门失败**  
    已增加G0、G1、审计报告无效、未批准草稿回写和非PASS快照引用测试。

14. **样本省略字段可能被误解为完整有效对象**  
    已增加测试夹具表达规则，明确正向样本依赖M0-02有效基础夹具，负向样本只改变测试字段。

## 22.3 二十项验收结果

| 验收项 | 结果 |
|---|---|
| 包含完整黄金路径 | PASS |
| 黄金路径覆盖九类对象 | PASS |
| 黄金路径覆盖A—H八层 | PASS |
| 黄金路径覆盖G0—G8 | PASS |
| 包含PASS样本 | PASS |
| 包含REWRITE样本 | PASS |
| 包含REPLAN样本 | PASS |
| 包含BLOCKED样本 | PASS |
| 包含人工审批样本 | PASS |
| 包含高层错误拒绝低层修补样本 | PASS |
| 包含原子提交失败样本 | PASS |
| 包含正式回滚样本 | PASS |
| 包含重复失败升级样本 | PASS |
| 包含M1最低验收集 | PASS |
| 未引入第十类核心对象 | PASS |
| 测试夹具与通用核心隔离 | PASS |
| 与M0-01至M0-04一致 | PASS |
| 结果由明确断言判定 | PASS |
| 正文、审计、快照对象身份可验证 | PASS |
| 省略字段规则明确 | PASS |

## 22.4 冻结范围

本次冻结：

- 测试夹具的核心规则与人物边界
- 黄金路径的对象交接顺序
- G0—G8正向与失败测试意图
- PASS / REWRITE / REPLAN / BLOCKED样本
- 人工审批、高层错误、原子提交和回滚样本
- 测试执行记录模板
- M1最低验收集
- 测试样本省略字段规则

本次不冻结：

- 测试小说的商业质量
- 具体正文文风
- 完整对象Schema
- 自动测试代码
- 具体数据库事务实现
- 模型和提示词
- 性能阈值
- 重复失败次数阈值

## 22.5 已知上游缺口

1. AuditReport对象 `status` 枚举仍未在M0-02中冻结；本文件只断言 `result`。
2. CharacterState的业务生命周期状态与对象版本当前性仍部分共用同一字段；本测试通过NarrativeState.character_refs确定当前引用，后续Schema阶段应拆分或明确。
3. “每章必须有不可逆变化”仍需M1真实章节测试。本夹具通过“不可撤回虚假回报”满足当前上游要求，不能证明该要求适用于所有章节类型。
4. 测试样本采用语义夹具片段，不是完整可直接执行的JSON/YAML Schema实例；完整Schema验证属于后续工程任务。

## 22.6 冻结后的变更规则

后续修改必须：

```text
提出变更原因
→ 标明受影响测试与上游闸门
→ 更新预期结果和断言
→ 检查M0-01至M0-04一致性
→ 升级文档版本
→ 保留旧冻结版
```

禁止直接覆盖本文件。

---

# 23. 当前结论

M0-05建立的不是文学评分集，而是SRN-U的最小工程验收集。

最低可信运行链为：

```text
合法项目输入
→ 已批准项目种子
→ 有效初始状态
→ 合法主路径
→ 可执行章节蓝图
→ 完整正文版本
→ 独立审计
→ 新状态预提交
→ 原子提交
→ 冻结快照
```

只有这条链在正常样本和失败样本中都能按预期运行，SRN-U才具备进入M1实现与实测的基础。

本文件冻结的是测试规范，不代表SRN-U已经通过这些测试。实际执行结果必须在M1实现后填写 `actual_result` 与证据引用。
