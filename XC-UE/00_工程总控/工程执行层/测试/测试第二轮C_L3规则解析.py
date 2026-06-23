from __future__ import annotations

import re

import pytest

from conftest import ROOT
from 协议解析 import 解析规则, 规则解析失败
from 退出码 import ExitCode


pytestmark = [pytest.mark.integration, pytest.mark.adversarial]


def _L3标准文本() -> dict[str, str]:
    base = ROOT / "50_L3_执行协议层"
    return {
        "L3-00": (base / "L3-00_执行协议总表_v0.1.2.md").read_text(encoding="utf-8"),
        "L3-06": (base / "L3-06_IR输入映射协议_v0.1.2.md").read_text(encoding="utf-8"),
        "L3-07": (base / "L3-07_ProjectHarness运行协议_v0.1.2.md").read_text(encoding="utf-8"),
        "L3-99": (base / "L3-99_执行禁止项_v0.1.2.md").read_text(encoding="utf-8"),
    }


def _替换机器区块(text: str, block_id: str, replacement: str) -> str:
    pattern = rf"(?ms)(<!--\s*XCUE:{re.escape(block_id)}:START\s*-->).*?(<!--\s*XCUE:{re.escape(block_id)}:END\s*-->)"
    return re.sub(pattern, rf"\1\n{replacement}\n\2", text, count=1)


def 测试L3状态机为空硬失败():
    standards = _L3标准文本()
    standards["L3-00"] = _替换机器区块(standards["L3-00"], "L3_STATE_MACHINE", "```text\n```")
    with pytest.raises(规则解析失败) as exc:
        解析规则(standards)
    assert exc.value.exit_code == ExitCode.RULE_PARSE_FAILED
    assert "RULE_PARSE_FAILED" in str(exc.value)
    assert "L3_STATE_MACHINE" in str(exc.value)


def 测试L3权限矩阵缺列硬失败():
    standards = _L3标准文本()
    standards["L3-00"] = standards["L3-00"].replace("| 区域 / 文件类型 | 默认权限 | 说明 |", "| 区域 / 文件类型 | 默认权限 |")
    with pytest.raises(规则解析失败) as exc:
        解析规则(standards)
    assert "L3_PERMISSION_MATRIX" in str(exc.value)


def 测试L3缺输出字段硬失败():
    standards = _L3标准文本()
    standards["L3-00"] = standards["L3-00"].replace("  断点记录: \"\"\n", "")
    with pytest.raises(规则解析失败) as exc:
        解析规则(standards)
    assert "L3_TASK_OUTPUT_FIELDS" in str(exc.value)
    assert "断点记录" in str(exc.value)


def 测试L3缺禁止项硬失败():
    standards = _L3标准文本()
    standards["L3-99"] = _替换机器区块(standards["L3-99"], "L3_FORBIDDEN", "")
    with pytest.raises(规则解析失败) as exc:
        解析规则(standards)
    assert "L3_FORBIDDEN" in str(exc.value)
