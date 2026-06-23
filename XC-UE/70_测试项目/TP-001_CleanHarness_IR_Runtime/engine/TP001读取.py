from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_rules(path: Path) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(f"Missing rules file: {path}")
    return json.loads(read_text(path))


def load_sources(candidate: Path) -> dict[str, str]:
    sources = {
        "manifest": ROOT / "MANIFEST_文件权限与真源表.md",
        "ir00": ROOT / "IR" / "IR-00_项目索引.md",
        "ir01": ROOT / "IR" / "IR-01_立项卡.md",
        "ir02": ROOT / "IR" / "IR-02_世界约束.md",
        "ir03": ROOT / "IR" / "IR-03_角色动机表.md",
        "ir04": ROOT / "IR" / "IR-04_事件链.md",
        "ir05": ROOT / "IR" / "IR-05_章节目标表.md",
        "ir06": ROOT / "IR" / "IR-06_读者预期表.md",
        "ir07": ROOT / "IR" / "IR-07_发布状态表.md",
        "ir08": ROOT / "IR" / "IR-08_状态快照.md",
        "ir99": ROOT / "IR" / "IR-99_输入完整性检查.md",
        "candidate": candidate,
        "formal_ch01": ROOT / "chapters" / "ch01.md",
    }
    missing = [str(path.relative_to(ROOT)) for path in sources.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing required files: " + ", ".join(missing))
    return {name: read_text(path) for name, path in sources.items()}
