from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from conftest import ROOT

L2工程 = ROOT / "00_工程总控" / "工程执行层" / "L2工程"
if str(L2工程) not in sys.path:
    sys.path.insert(0, str(L2工程))

from 路由规则加载 import 路由规则加载错误, 加载路由规则
from 退出码 import ExitCode


def _合法路由() -> dict:
    return {
        "schema_version": "xcue.l2-routes/1.0",
        "version": "pytest-a04",
        "status": "active",
        "routes": [
            {"rule_id": "R1", "keywords": ["叙事失败"], "target": "L2-01", "source": "pytest"},
            {"rule_id": "R2", "keywords": ["认知成本过高"], "target": "L2-05", "source": "pytest"},
        ],
    }


def _写规则(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _断言规则解析失败(path: Path, reason: str, location: str) -> None:
    with pytest.raises(路由规则加载错误) as exc_info:
        加载路由规则(path)
    exc = exc_info.value
    assert exc.exit_code == ExitCode.RULE_PARSE_FAILED
    assert exc.reason == reason
    assert exc.location == location
    assert exc.details["error_code"] == "RULE_PARSE_FAILED"
    assert exc.details["rule_source"] == "routes.json"


def 测试A04_L2合法路由文件成功加载(root_case):
    path = root_case / "routes.json"
    _写规则(path, _合法路由())

    rules = 加载路由规则(path)

    assert rules.version == "pytest-a04"
    assert [rule.target for rule in rules.rules] == ["L2-01", "L2-05"]
    assert len(rules.hash) == 64


@pytest.mark.parametrize(
    "mutate,reason,location",
    [
        (lambda payload: payload.pop("schema_version"), "RULE_SCHEMA_VERSION_MISSING", "schema_version"),
        (lambda payload: payload.__setitem__("schema_version", "xcue.l2-routes/0.9"), "RULE_SCHEMA_VERSION_UNSUPPORTED", "schema_version"),
        (lambda payload: payload.pop("status"), "RULE_STATUS_INVALID", "status"),
        (lambda payload: payload.__setitem__("status", "draft"), "RULE_STATUS_INVALID", "status"),
        (lambda payload: payload.pop("routes"), "RULE_ROUTES_INVALID", "routes"),
        (lambda payload: payload.__setitem__("routes", {}), "RULE_ROUTES_INVALID", "routes"),
        (lambda payload: payload["routes"][0]["keywords"].__setitem__(0, ""), "RULE_KEYWORD_INVALID", "routes[0].keywords[0]"),
        (lambda payload: payload["routes"][0]["keywords"].__setitem__(0, 42), "RULE_KEYWORD_INVALID", "routes[0].keywords[0]"),
        (lambda payload: payload["routes"][0].pop("target"), "RULE_TARGET_INVALID", "routes[0].target"),
        (lambda payload: payload["routes"][0].__setitem__("target", "L2-99"), "RULE_TARGET_INVALID", "routes[0].target"),
        (
            lambda payload: payload["routes"].append(
                {"rule_id": "R3", "keywords": ["叙事失败"], "target": "L2-02", "source": "pytest"}
            ),
            "RULE_DUPLICATE_CONFLICT",
            "routes[2].keywords[0]",
        ),
        (
            lambda payload: (
                payload["routes"][0].__setitem__("priority", 10),
                payload["routes"].append(
                    {"rule_id": "R3", "priority": 10, "keywords": ["角色失败"], "target": "L2-03", "source": "pytest"}
                ),
            ),
            "RULE_ROUTE_AMBIGUOUS",
            "routes",
        ),
        (
            lambda payload: payload["routes"].append(
                {"rule_id": "BROKEN", "keywords": ["可用"], "source": "pytest"}
            ),
            "RULE_TARGET_INVALID",
            "routes[2].target",
        ),
    ],
)
def 测试A04_L2坏路由规则统一封装(root_case, mutate, reason, location):
    path = root_case / "routes.json"
    payload = _合法路由()
    mutate(payload)
    _写规则(path, payload)

    _断言规则解析失败(path, reason, location)


def 测试A04_L2路由文件不存在统一封装(root_case):
    _断言规则解析失败(root_case / "missing-routes.json", "RULE_FILE_NOT_FOUND", "routes.json")


def 测试A04_L2非法JSON统一封装(root_case):
    path = root_case / "routes.json"
    path.write_text('{"schema_version": ', encoding="utf-8")

    _断言规则解析失败(path, "RULE_JSON_INVALID", "routes.json")


def 测试A04_L2编码错误统一封装(root_case):
    path = root_case / "routes.json"
    path.write_bytes(b"\xff\xfe\x00\x00")

    _断言规则解析失败(path, "RULE_ENCODING_INVALID", "routes.json")


def 测试A04_L2根节点非对象统一封装(root_case):
    path = root_case / "routes.json"
    _写规则(path, [])

    _断言规则解析失败(path, "RULE_ROOT_INVALID", "routes.json")
