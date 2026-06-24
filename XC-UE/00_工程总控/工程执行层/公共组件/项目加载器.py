from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from 安全路径 import resolve_inside_root, safe_id
from 工程异常 import 输入错误


注册表版本 = "xcue.project-registry/1.0"


@dataclass(frozen=True)
class 项目上下文:
    project_id: str
    project_root: Path
    relative_project_root: str
    registry_path: Path


def 默认注册表路径(root: Path) -> Path:
    return root / "00_工程总控" / "工程执行层" / "项目注册表.json"


def _注册表路径(root: Path, registry_path: str | Path | None) -> Path:
    if registry_path is None:
        return 默认注册表路径(root)
    path = Path(registry_path)
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def _读注册表(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise 输入错误(f"项目注册表不存在：{path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise 输入错误(f"项目注册表 JSON 解析失败：{path}: {exc}") from exc
    if not isinstance(data, dict):
        raise 输入错误("项目注册表必须是 JSON object")
    if data.get("schema_version") != 注册表版本:
        raise 输入错误("项目注册表 schema_version 不支持")
    if not isinstance(data.get("default_project"), str) or not data["default_project"]:
        raise 输入错误("项目注册表缺少 default_project")
    if not isinstance(data.get("projects"), dict):
        raise 输入错误("项目注册表缺少 projects")
    return data


def 加载项目(root: Path, project_id: str | None = None, registry_path: str | Path | None = None) -> 项目上下文:
    root = root.resolve()
    registry = _注册表路径(root, registry_path)
    data = _读注册表(registry)
    selected = project_id or data["default_project"]
    selected = safe_id(selected, "project")
    projects = data["projects"]
    if selected not in projects:
        raise 输入错误(f"未知项目：{selected}")
    entry = projects[selected]
    if not isinstance(entry, dict):
        raise 输入错误(f"项目注册项必须是 object：{selected}")
    raw_root = entry.get("project_root")
    if not isinstance(raw_root, str) or not raw_root:
        raise 输入错误(f"项目缺少 project_root：{selected}")
    project_root = resolve_inside_root(root, raw_root)
    if not project_root.exists():
        raise 输入错误(f"项目根目录不存在：{project_root}")
    if not project_root.is_dir():
        raise 输入错误(f"项目根路径不是目录：{project_root}")
    return 项目上下文(
        project_id=selected,
        project_root=project_root,
        relative_project_root=project_root.relative_to(root).as_posix(),
        registry_path=registry,
    )


def 读取默认项目ID(root: Path, registry_path: str | Path | None = None) -> str:
    registry = _注册表路径(root.resolve(), registry_path)
    data = _读注册表(registry)
    return safe_id(data["default_project"], "default_project")
