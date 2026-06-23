from __future__ import annotations

from pathlib import Path

from L3模型 import L2修复单
from ProjectHarness运行校验 import 相对


def 映射IR(form: L2修复单, root: Path, harness: Path) -> list[str]:
    base = harness / "IR"
    if form.接收模块 == "L2-01":
        files = [base / "IR-04_事件链.md", base / "IR-05_章节目标表.md"]
    elif form.接收模块 == "L2-05":
        files = [base / "IR-06_读者预期表.md", base / "IR-05_章节目标表.md"]
    elif form.接收模块 == "L2-03":
        files = [base / "IR-03_角色动机表.md"]
    elif form.接收模块 == "L2-04":
        files = [base / "IR-02_世界约束.md"]
    elif form.接收模块 == "L2-06":
        files = [base / "IR-08_状态快照.md"]
    else:
        files = [base / "IR-00_项目索引.md"]
    return [相对(root, path) for path in files]


def 校验IR存在(task, root: Path) -> list[str]:
    errors: list[str] = []
    for item in task.IR输入:
        path = root / item
        if not path.exists():
            errors.append(f"IR 输入不存在：{item}")
        elif path.stat().st_size == 0:
            errors.append(f"IR 输入为空：{item}")
    return errors
