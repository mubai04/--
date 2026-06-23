# SRN-U M0-03｜八层模块输入输出契约

> 文档编号：SRN-U-M0-03  
> 正式版本：v1.0  
> 文档状态：**FROZEN｜已冻结**  
> 冻结日期：2026-06-21  
> 验收结果：PASS（经修订后通过）  
> 工程阶段：M0｜框架与协议锁定  
> 上游基线：  
> - SRN-U-M0-01 v1.0 FROZEN  
> - SRN-U-M0-02 v1.0 FROZEN  
> 文档用途：定义 SRN-U 八层模块的职责、输入、输出、允许修改范围、禁止越权范围、失败状态与层间交接规则  
> 适用范围：M0 与 M1；M2 以后如需拆分子模块，必须保持本契约的职责边界

---

# 1. 设计目标

M0-01 已锁定 SRN-U 的八层总体框架，M0-02 已锁定九类核心数据对象。

本文件负责回答：

1. 每一层读取哪些对象？
2. 每一层输出哪些对象？
3. 每一层可以修改什么？
4. 每一层不能修改什么？
5. 每一层失败时应返回哪里？
6. 层与层之间通过什么契约交接？
7. M1 最小单章闭环实际需要哪些层先工作？

本文件只定义模块契约，不定义代码、数据库、API 或具体模型实现。

---

# 2. 八层总览

```text
A. 创作入口层
B. 叙事状态层
C. 结构规划层
D. 章节设计层
E. 正文执行层
F. 生成控制层
G. 审计修订层
H. 连载运行层
```

标准顺序：

```text
A 创作入口
→ B-INIT 建立初始叙事状态
→ C 候选路径与主路径
→ D 章节蓝图
→ E 正文生成
↔ F 生成中控制
→ G 独立审计与修订路由
→ H-P1 校验PASS并批准指定草稿版本
→ B-UPDATE 编译新的 NarrativeState / CharacterState
→ H-P2 冻结 StateSnapshot 并提交本轮结果
→ C 读取新状态进入下一轮
```

B层具有两种工作模式：

```text
B-INIT：由 ProjectSeed 建立初始状态
B-UPDATE：由已批准正文与 PASS 审计编译下一状态
```

H层采用两阶段提交：

```text
H-P1：批准草稿版本并启动状态编译
H-P2：验证B层新状态后冻结快照
```

其中：

- A 负责“项目是什么”；
- B 负责“故事现在是什么”；
- C 负责“下一步可以怎么走”；
- D 负责“这一章具体怎么执行”；
- E 负责“把蓝图写成正文”；
- F 负责“生成中有没有偏离”；
- G 负责“生成后是否成立、应返回哪一层修”；
- H 负责“如何审批、提交、冻结、回滚和继续”；
- B-UPDATE 负责“正文通过后，新的故事状态具体是什么”。

---

# 3. 统一模块契约字段

每一层至少要明确以下内容：

| 契约项 | 含义 |
|---|---|
| `responsibility` | 本层唯一职责 |
| `required_inputs` | 必须输入 |
| `optional_inputs` | 可选输入 |
| `outputs` | 正式输出 |
| `may_modify` | 允许修改的对象或字段 |
| `must_not_modify` | 禁止修改的对象或字段 |
| `hard_failures` | 必须阻断的失败 |
| `soft_failures` | 可修复但不阻断全局的失败 |
| `next_route` | 成功后进入哪一层 |
| `return_route` | 失败后返回哪一层 |
| `evidence_required` | 输出结论需要保留的证据 |

任何层如果没有清楚定义这些内容，不得进入实现。

## 3.1 对象状态与控制信号分离

本文件中的两类状态不得混用：

```text
对象状态：
写入九类核心对象的 `status` 或 AuditReport.result

控制信号：
模块运行期间的瞬时路由指令，不属于九类核心对象
```

控制信号包括：

```text
BLOCKED
REPLAN_REQUEST
CONTINUE
ADJUST_NEXT_BEAT
LOCAL_REPLAN
ESCALATE_TO_D
```

除非M0-02已经明确允许，否则控制信号不得直接写入对象 `status`。

---

# 4. A层｜创作入口层

## 4.1 唯一职责

把原始创作需求编译为一个已批准、可启动小说创作的最小项目种子。

A层只回答：

> 这本小说要写什么、卖什么、靠什么持续、有哪些不能违反的边界？

A层不负责写章节正文，也不负责决定具体剧情路径。

## 4.2 必须输入

```text
ProjectBrief
```

最低要求：

- `operation_mode`
- `genre`
- `core_emotion`
- `idea_statement`

## 4.3 可选输入

```text
既有小说材料引用
目标平台约束
目标篇幅
目标读者
作者禁区
参考风格说明
人工裁决
```

续写或修订模式必须引用既有材料。

## 4.4 正式输出

```text
ProjectSeed
```

必要时同时输出：

```text
ProjectBrief 修订建议
未决问题清单
冲突报告
```

## 4.5 允许修改

A层可以：

- 创建新的 ProjectBrief 版本或更新其工作流状态；
- 创建 ProjectSeed 的候选版本；
- 在候选 ProjectSeed 中编译卖点、内容源、主角结构与最小世界规则；
- 维护未决问题清单。

A层不得原地覆盖用户原始输入。

## 4.6 禁止修改

A层禁止：

- 直接生成 NarrativeState 中的已发生事实；
- 直接创建正式 ChapterDraft；
- 把候选创意写成已批准项目设定；
- 绕过人工审批修改已锁定 ProjectSeed；
- 为了平台适配改变用户明确禁止项。

## 4.7 硬失败

出现以下情况必须阻断：

```text
创作需求互相矛盾
核心卖点无法与内容源对应
主角结构与长期冲突无法共存
必须项与禁止项冲突
续写模式缺少既有材料
无法形成最小可执行项目种子
```

输出控制信号：

```text
BLOCKED
```

对象状态按M0-02执行：

```text
ProjectBrief.status = invalid
或
ProjectSeed.status = rejected
```

不得把 `BLOCKED` 写成 ProjectSeed 的对象状态。

## 4.8 软失败

```text
项目名不成熟
平台尚未确定
篇幅目标不明确
次要世界规则未定
```

这些内容可保留为 `UNKNOWN` 或 `UNDECIDED`，不阻断项目启动。

## 4.9 成功路由

```text
ProjectSeed.status ∈ {approved, locked}
→ B-INIT 建立初始 NarrativeState 与 CharacterState
```

## 4.10 失败返回

```text
返回 ProjectBrief
或等待人工裁决
```

## 4.11 证据要求

ProjectSeed 中每个核心字段必须能追溯到：

- ProjectBrief；
- 人工裁决；
- 既有材料；
- 明确标记的系统建议。

---

# 5. B层｜叙事状态层

## 5.1 唯一职责

维护当前创作轮次唯一可读取的规范叙事状态。

B层回答：

> 到目前为止，故事真实发生了什么，角色现在处于什么状态，还有哪些约束和未完成问题？

## 5.2 必须输入

B-INIT：

```text
ProjectSeed.status ∈ {approved, locked}
```

B-UPDATE：

```text
当前 NarrativeState
当前 CharacterState 集合
上一 StateSnapshot（首章可为空）
ChapterDraft.status = approved
AuditReport.result = PASS
```

B-UPDATE 只能由 H-P1 在完成草稿审批后调用。

## 5.3 可选输入

```text
人工状态裁决
既有正文
设定真源
角色档案
历史快照
```

## 5.4 正式输出

B-INIT：

```text
初始 NarrativeState
初始 CharacterState 集合
```

B-UPDATE：

```text
新的 NarrativeState
新的 CharacterState 集合
状态变更清单
状态冲突报告（如有）
```

B层只编译状态内容，不创建 StateSnapshot。

## 5.5 允许修改

B层可以：

- 创建新的 NarrativeState 版本；
- 创建新的 CharacterState 版本；
- 增量更新事实、知识、关系、资源、债务、支线和不可逆变化；
- 将不确定字段值标记为 `UNKNOWN`、`UNDECIDED` 或 `DISPUTED`；
- 将 NarrativeState 对象状态标记为 `initial`、`active` 或 `blocked`。

## 5.6 禁止修改

B层禁止：

- 直接修改已冻结 StateSnapshot；
- 将 ChapterBlueprint 中的计划当成已发生事实；
- 将 CandidatePath 中的候选后果写入确认事实；
- 自动补全来源不明的角色知识；
- 无依据删除伤害、代价、承诺或不可逆变化；
- 因为后续写作不方便而重写已批准历史。

## 5.7 硬失败

```text
正文事实与设定真源冲突
同一事实存在两个不能兼容的当前版本
角色知识边界冲突
世界规则互相否定
不可逆变化无依据消失
关键来源无法追溯
跨项目对象混入当前状态
```

输出：

```text
NarrativeState.status = blocked
```

## 5.8 软失败

```text
次要角色当前目标不明
某条支线是否继续尚未决定
某个符号是否升级为核心符号尚未确定
```

允许标记为 `UNKNOWN` 或 `UNDECIDED`。

## 5.9 成功路由

```text
NarrativeState.active
+ CharacterState
→ C层路径规划
```

## 5.10 失败返回

```text
来源或历史快照问题 → H层执行恢复核查
状态内容冲突 → B层生成冲突报告
无法裁决 → 等待人工状态裁决
```

## 5.11 证据要求

所有确认事实必须至少有一个有效来源：

```text
ProjectSeed
已批准正文
人工裁决
上一状态快照
```

---

# 6. C层｜结构规划层

## 6.1 唯一职责

根据当前叙事状态，生成合法候选路径，过滤无效路径，并锁定本轮主推进路径。

C层回答：

> 接下来哪些剧情真正成立，哪一条最值得执行？

## 6.2 必须输入

```text
NarrativeState.active
CharacterState 集合
ProjectSeed
```

## 6.3 可选输入

```text
长期方向
阶段目标
潜伏路径池
历史决策记录
生命周期风险提示
人工偏好
```

## 6.4 正式输出

```text
CandidatePath 集合
其中恰好一条 status = selected
路径选择记录
```

单候选模式下仍必须建立一个 CandidatePath。

## 6.5 允许修改

C层可以：

- 创建 CandidatePath；
- 标记路径为 `invalid`、`rejected`、`selected`、`latent`、`expired` 或 `executed`；
- 记录选择理由、代价、不确定性和触发条件；
- 更新潜伏路径管理状态。

## 6.6 禁止修改

C层禁止：

- 直接修改 NarrativeState 的确认事实；
- 为了让路径成立而新增无来源能力、资源或知识；
- 直接生成 ChapterDraft；
- 以“爽感高”覆盖人物、因果和世界规则；
- 把未执行路径写成事实；
- 宣称某条路径是绝对全局最优。

## 6.7 硬闸门顺序

候选路径先检查：

```text
1. 事实一致性
2. 世界规则
3. 人物动机与人格
4. 角色知识边界
5. 能力与资源来源
6. 不可逆后果继承
7. 当前阶段目标相关性
```

任一硬闸门失败：

```text
CandidatePath.status = invalid
```

不得进入后续比较。

## 6.8 软比较维度

通过硬闸门后，可以比较：

```text
状态推进
人物主动性
承诺兑现
长期资源消耗
信息价值
重复风险
认知成本
修复成本
潜在副作用
```

这些维度不得被压成一个不可解释的总分。

## 6.9 硬失败

```text
所有候选路径均 invalid
无法形成任何合法推进
当前阶段目标与人物状态冲突
关键状态输入缺失
同一轮出现多条 selected 主路径
```

## 6.10 软失败

```text
只有一条合法路径
多条路径价值接近
长期后果置信度低
```

这些情况允许进入人工裁决，不必自动阻断。

## 6.11 成功路由

```text
CandidatePath.selected
→ D层章节设计
```

## 6.12 失败返回

```text
输入状态问题 → B层
阶段目标问题 → A层或人工裁决
候选生成不足 → C层重新生成
```

## 6.13 证据要求

每条路径必须记录：

- 前置条件；
- 使用的状态事实；
- 主要收益；
- 主要代价；
- 短期后果；
- 长期风险；
- 选择或淘汰理由。

---

# 7. D层｜章节设计层

## 7.1 唯一职责

把已选中的 CandidatePath 转换为可执行的 ChapterBlueprint。

D层回答：

> 这一章具体从哪里开始，通过什么行动、冲突、选择和信息变化，抵达什么结束状态？

## 7.2 必须输入

```text
CandidatePath.status = selected
NarrativeState
CharacterState 集合
ProjectSeed
```

## 7.3 可选输入

```text
前章节奏状态
章节长度目标
平台形式约束
角色声音摘要
信息依赖图
```

## 7.4 正式输出

```text
ChapterBlueprint
```

必要时可输出瞬时控制信号：

```text
REPLAN_REQUEST
```

并附：

```text
缺失条件清单
退回层级
保护内容
```

该信号不是第十类核心数据对象。

## 7.5 允许修改

D层可以：

- 安排场景顺序；
- 定义章节目标；
- 安排信息隐藏、暗示、释放与延迟；
- 定义节奏轨迹；
- 定义当章兑现；
- 定义章末压力；
- 定义必须保留与必须避免的内容。

## 7.6 禁止修改

D层禁止：

- 改写 ProjectSeed 的核心卖点；
- 改写 NarrativeState 中的事实；
- 为了章末钩子新增无来源危机；
- 让角色使用未知信息；
- 把计划写成已发生事实；
- 同时设置多个并列主目标；
- 通过隐藏正常人应当说出的信息制造伪悬念。

## 7.7 必须成立的结构

ChapterBlueprint 至少要有：

```text
起始状态
本章主目标
主要行动者
核心阻力
关键选择
状态变化
场景顺序
信息计划
节奏轨迹
当章兑现
章末压力
```

关于“不可逆变化”：

- 当前按 M0-01 与 M0-02 冻结基线保留；
- 若M1实测证明对过渡章过强，必须走正式变更流程；
- 本文件不在下游擅自放宽。

## 7.8 硬失败

```text
蓝图未引用 selected CandidatePath
章节主目标不明确
起始状态与结束状态没有变化
关键选择违反人物动机
信息计划造成知识泄漏
章末压力与本章因果无关
```

## 7.9 软失败

```text
章节名未定
次要场景可删可留
节奏轨迹有两种可行方案
多个场景存在功能重复
```

## 7.10 成功路由

```text
ChapterBlueprint.approved
→ E层正文执行
并同时交给F层生成控制
```

## 7.11 失败返回

```text
结构问题 → C层重新选择路径
场景问题 → D层重做蓝图
状态问题 → B层
```

## 7.12 证据要求

ChapterBlueprint 中每个关键事件必须能追溯到：

- selected CandidatePath；
- NarrativeState；
- CharacterState；
- 已登记信息计划。

---

# 8. E层｜正文执行层

## 8.1 唯一职责

把 approved ChapterBlueprint 转化为具体小说正文。

E层回答：

> 如何把已批准的章节计划写成可读、具体、连贯的小说文本？

## 8.2 必须输入

```text
ChapterBlueprint.status = approved
NarrativeState
CharacterState 集合
ProjectSeed
```

## 8.3 可选输入

```text
动态文风画像
前章正文
角色声音摘要
平台格式约束
媒介适配要求
```

## 8.4 正式输出

```text
ChapterDraft
```

生成中可以输出：

```text
known_deviations
局部重规划请求
约束冲突报告
```

## 8.5 允许修改

E层可以：

- 选择具体措辞；
- 安排行动细节；
- 生成对话与叙述；
- 调整段落与动态分行；
- 在不改变蓝图目标的前提下补充现场细节；
- 将蓝图中的抽象行动具体化。

## 8.6 禁止修改

E层禁止：

- 修改 ProjectSeed；
- 修改 NarrativeState 中已确认事实；
- 改变 ChapterBlueprint 的主目标；
- 取消关键选择或状态变化；
- 让角色获得未登记能力；
- 让角色知道不应知道的信息；
- 为追求文采加入改变剧情的新事实；
- 未经记录擅自改变章末结果。

## 8.7 生成控制原则

正文必须尽量满足：

```text
句子有可解释功能
语言绑定具体人物与现场
节奏存在推进、延迟、停顿、爆发和余波
人物声音与当前状态一致
前文变化在语言中得到继承
```

但禁止机械执行：

```text
每句话必须增加新事实
每段都必须有爆点
每次符号出现都必须变义
所有情绪都只能通过动作表达
```

## 8.8 硬失败

```text
蓝图硬约束被破坏
正文出现事实冲突
角色知识泄漏
能力或资源凭空出现
核心场景无法执行
正文偏离章节主目标
```

## 8.9 软失败

```text
局部重复
AI味
节奏同质
对话声音接近
细节过密或过薄
章末力度不足
```

软失败进入G层，不在E层自行宣布通过。

## 8.10 成功路由

```text
ChapterDraft.review_ready
→ G层审计
```

## 8.11 失败返回

```text
局部生成偏差 → F层调整
蓝图不可执行 → D层
状态冲突 → B层
```

## 8.12 证据要求

ChapterDraft 必须记录：

- 对应 blueprint_ref；
- object_version；
- generation_mode；
- known_deviations；
- 人工介入记录；
- 相对上一版的 changed_ranges。

---

# 9. F层｜生成控制层

## 9.1 唯一职责

在正文生成过程中监测偏差，并在不越权的前提下调整后续叙事拍或发起局部重规划。

F层不是第二个正文生成器，也不是逐句评分器。

## 9.2 必须输入

```text
ChapterBlueprint.status = approved
生成缓冲区中的正文片段
NarrativeState
CharacterState 集合
```

“生成缓冲区”是E层运行期间的临时内容，不是新的核心数据对象；章节结束后由E层形成正式 ChapterDraft。

## 9.3 可选输入

```text
节奏状态
信息计划
前一叙事拍结果
认知负荷提示
已知偏差
```

## 9.4 正式输出

F层输出瞬时控制信号：

```text
CONTINUE
ADJUST_NEXT_BEAT
LOCAL_REPLAN
ESCALATE_TO_D
BLOCKED
```

这些信号不写入九类核心对象的 `status`。

同时输出：

```text
偏差位置
偏差类型
偏差证据
建议调整范围
禁止修改内容
```

## 9.5 允许修改

F层可以：

- 向E层提出下一叙事拍速度调整建议；
- 建议推迟尚未写出的信息揭示；
- 建议降低后续解释密度；
- 建议调整后续场景细节顺序；
- 发出局部重规划请求；
- 记录已生成内容中的偏差。

F层不直接改写生成缓冲区；实际文字修改由E层执行。

## 9.6 禁止修改

F层禁止：

- 重写已完成并已锁定的整个章节；
- 修改 NarrativeState；
- 修改 ProjectSeed；
- 取消已批准主路径；
- 为了修正节奏新增无来源冲突；
- 逐句循环评分、改写、再评分；
- 自行宣布整章通过。

## 9.7 监测范围

重点监测：

```text
信息提前泄露
冲突升级不足
人物被剧情强推
节奏持续同质
认知负荷过高
场景目标提前耗尽
章末结果正在失去因果来源
```

控制粒度优先：

```text
叙事拍
段落组
场景
信息节点
```

不以单句为默认控制单位。

## 9.8 硬失败

```text
正文已经违反硬事实
角色行动与人物状态根本冲突
蓝图本身不可执行
信息计划与角色知识边界冲突
```

## 9.9 软失败

```text
局部节奏偏快
解释略多
下一叙事拍压力不足
信息节点次序可调整
```

## 9.10 成功路由

```text
CONTINUE / ADJUST_NEXT_BEAT
→ E层继续生成

LOCAL_REPLAN / ESCALATE_TO_D
→ D层局部或整体蓝图调整

BLOCKED
→ 根据根因返回B、C或等待人工裁决

正文完成
→ E层封装 ChapterDraft.review_ready
→ G层
```

## 9.11 失败返回

```text
蓝图问题 → D层
路径问题 → C层
状态问题 → B层
```

## 9.12 证据要求

每次控制动作必须记录：

- 触发位置；
- 触发原因；
- 修改范围；
- 未修改的保护内容；
- 对最终正文的影响。

---

# 10. G层｜审计修订层

## 10.1 唯一职责

对指定版本产物进行独立审计，定位错误，路由修复，并对修订结果复验。

G层回答：

> 这一版是否成立；若不成立，问题在哪里，应返回哪一层修？

“审计修订层”在本契约中的含义是：G层负责审计、修复路由和复验编排；实际正文重写由E层执行，蓝图重做由D层执行，路径重选由C层执行。

## 10.2 必须输入

```text
ChapterDraft 精确版本
ChapterBlueprint
NarrativeState
CharacterState
ProjectSeed
```

## 10.3 可选输入

```text
前章正文
历史 AuditReport
人工审阅意见
平台形式要求
读者风险面板
```

## 10.4 正式输出

```text
AuditReport
```

结果只允许：

```text
PASS
REWRITE
REPLAN
BLOCKED
```

## 10.5 允许修改

G层可以：

- 创建 AuditReport；
- 指定错误位置、类型、证据和根因；
- 指定允许修改与保护内容；
- 指定修复路由；
- 对新版本重新复验；
- 创建新的 AuditReport 版本。

G层不能直接修改被审计对象，也不依赖未在M0-02中定义的 AuditReport 状态枚举。

## 10.6 禁止修改

G层禁止：

- 一边修改正文一边宣布通过；
- 用总分覆盖具体错误；
- 用语言优点掩盖硬约束冲突；
- 把个人偏好写成硬规则；
- 因为“整体不错”而忽略角色知识泄漏；
- 对未指定版本做模糊审计。

## 10.7 审计优先级

```text
1. 已发生事实与世界规则
2. 人物动机与知识边界
3. 因果与状态变化
4. 主路径与章节目标
5. 信息控制
6. 语言、节奏和文风
7. 符号、传播和平台适配
```

## 10.8 结果路由

### PASS

```text
→ H-P1 校验PASS与草稿版本
→ 将指定 ChapterDraft 从 review_ready 转为 approved
→ 调用 B-UPDATE
```

### REWRITE

```text
→ E层局部重写
→ 新 ChapterDraft 版本
→ G层复验
```

### REPLAN

```text
→ D层重做 ChapterBlueprint
必要时返回 C层
```

### BLOCKED

```text
→ B层状态核查
或等待人工裁决
```

## 10.9 硬失败

```text
审计对象版本不明确
缺少必要上游对象
发现硬约束错误却给出 PASS
修复范围与保护内容冲突
BLOCKED 未列出解除条件
审计结论没有证据位置
```

## 10.10 软失败

```text
语言问题难以统一判断
角色声音存在多种可接受版本
章末力度属于审美分歧
```

可降低置信度并交由人工裁决。

## 10.11 证据要求

AuditReport 必须包含：

- target_ref；
- findings；
- evidence_refs；
- impact_range；
- allowed_changes；
- protected_content；
- repair_route；
- retest_requirements；
- confidence；
- unknowns。

---

# 11. H层｜连载运行层

## 11.1 唯一职责

作为提交事务协调器，在章节通过验收后完成草稿审批、调用B层状态编译、快照冻结、版本记录、失败恢复和下一轮启动。

H层回答：

> 这一章通过后，如何把“PASS草稿”合法转换为正式状态和不可变快照？

H层不负责判断新的故事状态内容；该内容由 B-UPDATE 编译。

## 11.2 必须输入

H-P1：

```text
ChapterDraft.status = review_ready
AuditReport.result = PASS
AuditReport.target_ref 精确指向该 ChapterDraft 版本
上一 StateSnapshot（首章除外）
当前 NarrativeState
当前 CharacterState 集合
CandidatePath.status = selected
```

H-P2：

```text
ChapterDraft.status = approved
B-UPDATE 输出的新 NarrativeState
B-UPDATE 输出的新 CharacterState 集合
状态变更清单
```

## 11.3 可选输入

```text
人工审批记录
发布状态
外部平台结果
生命周期提示
```

## 11.4 正式输出

```text
ChapterDraft.status = approved
StateSnapshot.status = frozen
章节工作流状态更新
提交记录
下一轮启动信号
```

新的 NarrativeState 与 CharacterState 由B层生成，H层只负责验证、提交和纳入快照，不拥有其内容修改权。

## 11.5 允许修改

H层可以：

- 在PASS条件满足后，将指定 ChapterDraft 的工作流状态从 `review_ready` 转为 `approved`；
- 调用 B-UPDATE 编译新状态；
- 验证B层输出与批准正文的一致性；
- 创建新 StateSnapshot；
- 在快照提交成功后标记旧状态对象为 `superseded`；
- 更新章节工作流；
- 保存决策、审计与提交记录；
- 执行定向回滚；
- 更新项目级运行日志。

## 11.6 禁止修改

H层禁止：

- 修改已冻结 StateSnapshot 的业务内容；
- 把未执行蓝图写成事实；
- 把 REWRITE / REPLAN / BLOCKED 的正文写入状态；
- 静默覆盖旧版本；
- 自动批准重大设定变更；
- 把平台反馈直接写入小说事实；
- 越过人工审批修改核心设定。

## 11.7 硬失败

```text
AuditReport 不是 PASS
AuditReport.target_ref 与 ChapterDraft 版本不一致
ChapterDraft 不是 review_ready
B-UPDATE 失败或返回 blocked 状态
状态变更无法追溯到正文
新状态与旧状态无依据矛盾
快照引用链断裂
回滚范围不明确
跨项目状态混入
```

## 11.8 软失败

```text
尚未发布
平台数据暂缺
生命周期报告尚未更新
```

不影响状态快照创建。

## 11.9 成功路由

```text
StateSnapshot.status = frozen
→ 新 NarrativeState.status = active
→ C层启动下一轮路径规划
```

## 11.10 失败返回

```text
状态提取错误 → B层
审计遗漏 → G层
正文引用错误 → E层
重大设定问题 → 人工审批
```

## 11.11 证据要求

StateSnapshot 必须同时引用：

- `ChapterDraft.status = approved` 的精确版本；
- `AuditReport.result = PASS` 且 target_ref 匹配；
- B-UPDATE 生成的新 NarrativeState；
- B-UPDATE 生成的新 CharacterState；
- `CandidatePath.status = selected` 的路径；
- previous_snapshot_ref（首章除外）；
- H层提交记录。

---

# 12. 层间交接契约

## 12.1 A → B

```text
ProjectSeed.status ∈ {approved, locked}
```

否则B层不得建立正式初始状态。

## 12.2 B → C

```text
NarrativeState.status = active
且关键 CharacterState 可用
```

`blocked` 状态禁止规划。

## 12.3 C → D

```text
同一 planning_round 恰好一条 CandidatePath.status = selected
```

## 12.4 D → E/F

```text
ChapterBlueprint.status = approved
```

E与F同时读取同一蓝图版本。

## 12.5 E → G

```text
ChapterDraft.status = review_ready
且 object_version 明确
```

## 12.6 G → H-P1

```text
AuditReport.result = PASS
且 target_ref 指向当前 ChapterDraft.status = review_ready 的精确版本
```

## 12.7 H-P1 → B-UPDATE

```text
H已将指定 ChapterDraft 转为 approved
且上一状态与上一快照可用
```

## 12.8 B-UPDATE → H-P2

```text
新的 NarrativeState / CharacterState 已建立
且状态变更可追溯到批准正文
```

## 12.9 H-P2 → C

```text
StateSnapshot.status = frozen
且新 NarrativeState.status = active
```

---

# 13. 失败路由总表

| 失败类型 | 主要发现层 | 返回层 |
|---|---|---|
| 创作需求冲突 | A | A / 人工裁决 |
| 状态或真源冲突 | B | B / H / 人工裁决 |
| 所有路径无效 | C | B / A |
| 蓝图不可执行 | D | C / B |
| 正文偏离蓝图 | E / F | D / E |
| 生成中局部偏差 | F | E / D |
| 正文局部问题 | G | E |
| 路径或结构错误 | G | D / C |
| 状态编译失败 | B-UPDATE | B / G / 人工裁决 |
| 草稿审批或提交事务失败 | H-P1 | G / H |
| 快照冻结失败 | H-P2 | B / H |
| 快照链断裂 | H | H / 人工恢复 |

禁止跨多层随意跳转。

例如：

```text
语言问题不能直接返回A层
状态冲突不能只在E层改句子
路径错误不能靠G层局部润色解决
```

---

# 14. 八层权限矩阵

| 层 | 主要读取 | 主要输出 | 可修改 | 禁止修改 |
|---|---|---|---|---|
| A | ProjectBrief | ProjectSeed | 创作需求与项目种子 | 正文事实、状态 |
| B | ProjectSeed / Snapshot / approved Draft + PASS Audit | NarrativeState / CharacterState | 状态内容与新版本 | 冻结快照、候选路径 |
| C | 当前状态 | CandidatePath | 路径状态与决策记录 | 已发生事实、正文 |
| D | selected Path | ChapterBlueprint | 章节计划 | 项目核心、当前事实 |
| E | approved Blueprint | ChapterDraft | 正文内容与版本 | 状态真源、主路径 |
| F | 蓝图与生成缓冲区 | 瞬时控制信号 | 后续叙事拍建议 | 正文内容、全局设定、已冻结事实 |
| G | 指定草稿与上游对象 | AuditReport | 审计记录与修复路由 | 被审计正文、状态真源 |
| H | PASS审计、review_ready草稿、B层新状态 | Snapshot / 提交记录 | 工作流状态、快照、回滚事务 | B层状态内容、冻结快照业务内容 |

---

# 15. M1最小运行范围

M1必须让八层全部出现，但允许简化：

## A层

```text
ProjectBrief → ProjectSeed
```

## B层

```text
建立最简 NarrativeState 与核心 CharacterState
```

## C层

```text
允许单 CandidatePath
但必须完成硬闸门与 selected 状态
```

## D层

```text
生成一份 approved ChapterBlueprint
```

## E层

```text
生成第一章 ChapterDraft
```

## F层

```text
只监测三类偏差：
信息提前泄露
人物行为偏离
章节目标偏离
```

## G层

```text
只检查：
因果
人物
状态
重复
AI味
章末推进
```

## H层

```text
H-P1批准PASS草稿
→ 调用B-UPDATE建立下一轮 NarrativeState / CharacterState
→ H-P2生成第一份 StateSnapshot
```

M1如果没有完成 B-UPDATE 与 H-P2，不算形成完整单章闭环。

---

# 16. 当前不在本文件中定义的内容

本文件不定义：

```text
具体提示词
具体模型
具体代码类
数据库表
JSON Schema
API协议
目录结构
自动化调度器
平台评分算法
读者心理公式
```

这些属于后续实现文件。

---

# 17. 本文件验收标准

本文件满足以下条件才可冻结：

1. 八层职责互斥且完整。
2. 每层都有明确输入与输出。
3. 每层都有允许修改与禁止修改范围。
4. 每层都有硬失败与软失败。
5. 层间交接条件明确。
6. 失败路由不会靠低层修补高层问题。
7. 审计层不直接修改正文。
8. 运行层不把未通过正文写入状态。
9. M1能够用最小实现跑通八层。
10. 与 M0-01、M0-02 冻结基线一致。
11. 未提前扩展成具体代码或数据库。
12. 没有任何一层可以绕过状态、审计或快照。

---

# 18. 验收与冻结记录

## 18.1 验收结果

```text
结果：PASS
性质：经修订后通过
正式版本：v1.0
冻结日期：2026-06-21
```

## 18.2 验收中发现并修正的问题

1. **B层与H层重复生成新状态**  
   已明确：B层拥有状态内容编译权；H层只负责审批、提交、快照和回滚。

2. **PASS后缺少合法的草稿审批者**  
   已增加H-P1：核验PASS报告后，将精确草稿版本从 `review_ready` 转为 `approved`。

3. **G→H形成循环前置条件**  
   原契约要求G的PASS报告指向“已approved草稿”，但草稿只有通过PASS后才应批准。现改为G审计 `review_ready` 草稿，H-P1负责批准。

4. **状态编译与快照冻结顺序错误**  
   修正为：G PASS → H-P1 → B-UPDATE → H-P2。

5. **对象状态与控制信号混用**  
   已明确 `BLOCKED`、`LOCAL_REPLAN` 等是瞬时控制信号，不得写入未授权对象状态。

6. **B层把UNKNOWN/DISPUTED误写成对象状态**  
   已区分字段不确定值与 NarrativeState 对象状态。

7. **A层成功条件遗漏locked状态**  
   已改为 `ProjectSeed.status ∈ {approved, locked}`。

8. **F层越权修改正文风险**  
   已明确F层只输出控制建议，实际文字修改由E层执行。

9. **G层“审计修订”职责容易误解**  
   已明确G只负责审计、修复路由和复验编排，不直接改正文。

10. **D层将场景功能重复列为硬失败**  
    已降为软失败，避免把可局部修复问题错误升级为全局阻断。

11. **H层直接拥有状态内容修改权**  
    已删除该权限；H只能验证和提交B层输出。

12. **正文生成中的临时片段被误当成核心对象**  
    已定义为E层生成缓冲区，不新增第十类数据对象。

## 18.3 十二项验收结果

| 验收项 | 结果 |
|---|---|
| 八层职责互斥且完整 | PASS |
| 每层输入与输出明确 | PASS |
| 修改权限与禁止权限明确 | PASS |
| 硬失败与软失败明确 | PASS |
| 层间交接条件明确 | PASS |
| 高层问题不会被低层修补掩盖 | PASS |
| G层不直接修改正文 | PASS |
| H层不写入未通过正文 | PASS |
| M1可用最小实现跑通八层 | PASS |
| 与M0-01、M0-02一致 | PASS |
| 未提前扩展代码或数据库 | PASS |
| 状态、审计、快照均不可绕过 | PASS |

## 18.4 冻结范围

本次冻结：

- A—H八层唯一职责
- B层INIT/UPDATE双模式
- H层两阶段提交
- 各层输入、输出和权限边界
- 硬失败、软失败与失败路由
- 层间交接条件
- M1最小八层运行方式
- 对象状态与控制信号分离原则

本次不冻结：

- 具体提示词
- 编程语言与类设计
- API和数据库
- 具体控制信号编码
- 具体人工审批界面
- M2以后新增的子模块
- 各层性能指标与阈值

## 18.5 已知上游缺口

M0-02 的 AuditReport 示例使用 `status: final`，但未单独冻结 AuditReport 的 `status` 枚举。本文件不依赖该字段，只依赖 `AuditReport.result`。后续设计数据Schema时必须发起上游变更审查，补齐或删除该状态枚举，不能自行猜测。

## 18.6 冻结后的变更规则

后续修改必须：

```text
提出变更原因
→ 标明受影响层与对象
→ 检查M0-01、M0-02一致性
→ 更新失败路由与测试案例
→ 升级文档版本
→ 保留旧冻结版
```

禁止直接覆盖本文件。

---

# 19. 当前结论

八层的核心分工可以压缩为：

```text
A：定义小说项目
B：维护真实状态
C：选择合法路径
D：设计可执行章节
E：生成具体正文
F：控制生成偏差
G：审计并路由修复
H：冻结状态并继续连载
```

完整交接链：

```text
ProjectBrief
→ ProjectSeed
→ B-INIT：NarrativeState / CharacterState
→ CandidatePath.status = selected
→ ChapterBlueprint.status = approved
→ ChapterDraft.status = review_ready
→ AuditReport.result = PASS
→ H-P1：ChapterDraft.status = approved
→ B-UPDATE：新 NarrativeState / CharacterState
→ H-P2：StateSnapshot.status = frozen
→ C层下一轮规划
```

当前文件只锁定模块契约，不代表任何模块已经实现。
