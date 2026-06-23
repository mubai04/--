from __future__ import annotations

from pathlib import Path

import pytest
import tomllib


ROOT = Path(__file__).resolve().parents[3]

pytestmark = pytest.mark.governance


def 测试测试代码不再复制整库():
    forbidden_patterns = [
        "copytree" + "(ROOT",
        "copytree" + "( ROOT",
        "shutil.copytree" + "(ROOT",
        "shutil.copytree" + "( ROOT",
    ]
    test_roots = [
        ROOT / "00_工程总控" / "工程执行层" / "测试",
    ]
    self_path = Path(__file__).resolve()
    offenders: list[str] = []
    for test_root in test_roots:
        for path in test_root.rglob("*.py"):
            if path.resolve() == self_path:
                continue
            text = path.read_text(encoding="utf-8")
            if any(pattern in text for pattern in forbidden_patterns):
                offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == []


def 测试pytest分类标记已登记():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    markers = "\n".join(data["tool"]["pytest"]["ini_options"]["markers"])
    for marker in ["unit", "integration", "governance", "security", "adversarial", "slow"]:
        assert f"{marker}:" in markers


def 测试pytest路径安全临时目录无残留():
    runtime = ROOT / "运行记录"
    if not runtime.exists():
        return
    leftovers = [path.name for path in runtime.iterdir() if path.is_dir() and path.name.startswith("pytest-路径安全-")]
    assert leftovers == []
