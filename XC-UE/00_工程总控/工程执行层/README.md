# 工程执行层

> 状态：统一工程执行入口。  
> 目的：避免各层各项目自行散落 `engine/`，统一从工程总控调度。

## 当前目标

```text
00_工程总控/工程执行层/统一运行入口.py
```

统一调度：

- `L1`：调用 `00_工程总控/工程执行层/L1工程/L1运行入口.py`
- `L2`：调用 `00_工程总控/工程执行层/L2工程/L2运行入口.py`
- `L3`：调用 `00_工程总控/工程执行层/L3工程/L3运行入口.py`
- `正文检测`：兼容旧目标，后续应迁移到 `L1`
- `TP-001`：调用 `70_测试项目/TP-001_CleanHarness_IR_Runtime/engine/TP001运行入口.py`

## 运行

```powershell
python 00_工程总控/工程执行层/统一运行入口.py --target L1 --run-id L1_RUN-UNIFIED-001
python 00_工程总控/工程执行层/统一运行入口.py --target L2 --run-id L2_RUN-UNIFIED-001
python 00_工程总控/工程执行层/统一运行入口.py --target L3 --run-id L3_RUN-UNIFIED-001
python 00_工程总控/工程执行层/统一运行入口.py --target TP-001 --run-id ENGINE-RUN-UNIFIED-TP001-001
```

## 架构纠偏

此前：

```text
TP-001 自带 engine/
```

现在：

```text
00_工程总控/工程执行层/统一运行入口.py
↓
L1工程 / L2工程 / L3工程 / 各项目执行入口
```

旧 TP-001 入口暂时保留，作为目标适配器；长期可逐步上提公共能力。
