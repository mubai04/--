from __future__ import annotations

from pathlib import Path
from typing import Any

from 文件哈希 import 计算文件哈希
from 工程异常 import 哈希错误, 血缘错误


def 产物记录(kind: str, path: Path, producer_stage: str, producer_run_id: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "path": str(path),
        "sha256": 计算文件哈希(path),
        "producer_stage": producer_stage,
        "producer_run_id": producer_run_id,
    }


def 校验产物哈希(record: dict[str, Any]) -> None:
    path = Path(record["path"])
    actual = 计算文件哈希(path)
    expected = record.get("sha256")
    if actual != expected:
        raise 哈希错误(f"产物哈希不一致：{path} expected={expected} actual={actual}")


def 校验流水线归属(data: dict[str, Any], pipeline_run_id: str, label: str) -> None:
    actual = data.get("pipeline_run_id")
    if actual and actual != pipeline_run_id:
        raise 血缘错误(f"{label} 不属于本次流水线：expected={pipeline_run_id} actual={actual}")

