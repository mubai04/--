# 网文伪数学分析器 v0.2 CANDIDATE

独立、个人使用、本地运行的网文文本分析与定向修复项目。

## 定位

本项目不是小说生成器、爆款预测器或作者身份鉴定器。它把《网文伪数学公式与功能总表》转换为可执行工程：

1. 正文目录是唯一文本真源；
2. Codex 或人工负责事实编码、原文定位和判断说明；
3. Python 负责运行时 Schema 校验、证据校验、公式计算、状态机、Stability、比较和报告；
4. 当前权重与阈值均为 C0，仅允许个人内部分析和同范围版本比较。

## 安装

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

本脚本不调用模型 API，不需要 API Key。

## 最短流程

```powershell
python src/novel_pseudo_math.py self-test
python src/novel_pseudo_math.py init-work --work-id WORK-001 --title "作品名"
python src/novel_pseudo_math.py validate-work --work-dir "正文/作品/WORK-001"
python src/novel_pseudo_math.py prepare --work-dir "正文/作品/WORK-001" --scope single --chapters 0001 --output "分析任务/WORK-001_0001"
# Codex 按 CODEX_TASK.md 生成 extraction.json
python src/novel_pseudo_math.py score --task "分析任务/WORK-001_0001/task.json" --extraction "分析任务/WORK-001_0001/extraction.json" --output "分析报告/WORK-001_0001"
```

版本比较：

```powershell
python src/novel_pseudo_math.py compare --before "分析报告/修改前/analysis.json" --after "分析报告/修改后/analysis.json" --output "分析报告/版本比较.json"
```

批量评分：

```powershell
python src/novel_pseudo_math.py batch-score --tasks-dir "分析任务" --output-dir "分析报告/批处理"
```

任一任务失败时，批处理返回非零退出码。

## v0.2 核心修复

- 运行时执行 JSON Schema；
- 禁止额外字段、负分子、分子大于分母、非法区间和非有限数值；
- 证据必须绑定任务内真实文件、精确起止位置和逐字引文；
- 同一证据默认最多支撑两个主判断；
- 极短文本不得把硬闸门判为 PASS；
- 实现 `BLOCKED / NEEDS_REVIEW / REWRITE / TARGETED_REPAIR / ROBUST_PASS` 状态机；
- 风险阈值改为连续半开区间，无 0.9—1.0 空档；
- `work_id` 路径越界防护；
- 九维风险 Stability 权重扰动；
- 六项反刷分检查；
- UTF-8 BOM 兼容；
- 同范围版本比较；
- 批处理失败传播。

## 核心输出

- 四个三态硬闸门：因果、人物、连续性、视角；
- 六维章节能力；
- 九维风险向量；
- 最终状态机；
- Stability；
- AI 式文本迹象指数；
- 反刷分结果；
- 去重后的病灶与修复动作。

## 边界

- `AI_STYLE_INDEX` 不是 AI 作者身份概率；
- 文本风险不是商业成功率、平台推荐率或真实留存；
- C0 只允许同作品、同范围、同方法版本的内部比较；
- 数据不足必须输出 `UNKNOWN / LOW_SAMPLE / NA / INSUFFICIENT_DATA`，不得按零风险处理；
- 整书分析禁止静默截断。
