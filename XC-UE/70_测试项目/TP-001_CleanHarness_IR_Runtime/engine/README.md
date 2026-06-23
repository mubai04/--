# TP-001 Engine

> 状态：TP-001 目标适配器 / 兼容入口。  
> 作用：把 Markdown 文件态转换为可运行检查，不替代 IR / L1 / L2 / L3 真源。

统一工程入口在：

```text
00_工程总控/工程执行层/统一运行入口.py
```

建议优先从统一入口调用：

```powershell
python 00_工程总控/工程执行层/统一运行入口.py --target TP-001 --run-id ENGINE-RUN-UNIFIED-TP001-001
```

## 运行

```powershell
python engine/TP001运行入口.py --run-id ENGINE-RUN-20260621-004
```

指定规则文件：

```powershell
python engine/TP001运行入口.py --rules engine/rules_tp001_v0.1.json --run-id ENGINE-RUN-20260621-004
```

旧入口 `tp001_engine.py` 暂时保留兼容；`TP001运行入口.py` 是 TP-001 目标入口；总入口使用 `00_工程总控/工程执行层/统一运行入口.py`。

## 输入

- `MANIFEST_文件权限与真源表.md`
- `IR/IR-00_项目索引.md` 到 `IR/IR-99_输入完整性检查.md`
- `chapters/_candidates/ch01_candidate_RUN-20260621-002.md`
- `chapters/ch01.md`
- `engine/rules_tp001_v0.1.json`

## 脚本结构

- `TP001运行入口.py`：中文入口脚本。
- `TP001模型.py`：检查结果数据结构。
- `TP001读取.py`：读取规则和输入文件。
- `检查.py`：执行规则检查。
- `TP001报告.py`：生成 JSON / Markdown 报告。

## 输出

- `reports/<run-id>.json`
- `reports/<run-id>.md`

## 边界

- 只读 IR 和正文候选。
- 不覆盖正式 `chapters/ch01.md`。
- 不读取 `_legacy_root_inputs/` 作为正式输入。
- 不把图片当真源。
- 不修改 XC-UE 系统层。

## 规则边界

检查规则不写死在 Python 中。  
Python 只负责读取规则、执行规则、输出报告。  
项目语义关键词放在 `rules_tp001_v0.1.json`，后续可替换为其他项目规则。
