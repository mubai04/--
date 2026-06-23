from __future__ import annotations

from pathlib import Path


def 发现Harness(root: Path, preferred: str | None = None) -> Path:
    if not preferred:
        raise FileNotFoundError("P0 后 L3 必须显式提供 --project-harness，不得按修改时间自动选择。")
    candidate = Path(preferred)
    if not candidate.is_absolute():
        candidate = (root / candidate).resolve()
    required = [candidate / "IR", candidate / "chapters", candidate / "logs"]
    missing = [item for item in required if not item.exists()]
    if missing:
        raise FileNotFoundError(f"Project Harness 缺少必备目录：{', '.join(str(item) for item in missing)}")
    return candidate


def 相对(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def 确保Harness目录(harness: Path) -> list[Path]:
    required = [harness / "IR", harness / "chapters", harness / "logs"]
    missing = [item for item in required if not item.exists()]
    if missing:
        raise FileNotFoundError(f"Project Harness 验证失败：{', '.join(str(item) for item in missing)}")
    return required


def 默认候选目标(root: Path, harness: Path, run_id: str, index: int) -> str:
    target = harness / "chapters" / "_candidates" / f"{run_id}_TASK-{index:03d}.md"
    return 相对(root, target)
