from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
公共组件 = ROOT / "00_工程总控" / "工程执行层" / "公共组件"
L1工程 = ROOT / "00_工程总控" / "工程执行层" / "L1工程"
if str(公共组件) not in sys.path:
    sys.path.insert(0, str(公共组件))
if str(L1工程) not in sys.path:
    sys.path.insert(0, str(L1工程))

from 标准加载器 import 候选试验模式, 标准加载错误, 加载标准文本, 生产模式
from 系统状态 import 生产规则集缺失
from 结构校验 import 按结构文件校验
from 工程异常 import 结构错误
from 闸门标准解析 import 规则解析错误, 解析规则


def _加载读取器(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


pytestmark = pytest.mark.integration


def _最小规则根(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "mini-xcue"
    target = root / "20_L1_闸门层" / "L1-02_读者投入意愿工程图.md"
    target.parent.mkdir(parents=True)
    target.write_text(
        (ROOT / "20_L1_闸门层" / "L1-02_读者投入意愿工程图.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return root, target


def 测试生产模式拒绝候选规则():
    reader = _加载读取器("l1_reader_b_test", L1工程 / "L1读取.py")
    with pytest.raises(生产规则集缺失):
        reader.读标准(ROOT, 生产模式)


def 测试候选试验模式显式加载规则():
    reader = _加载读取器("l1_reader_candidate_b_test", L1工程 / "L1读取.py")
    standards = reader.读标准(ROOT, 候选试验模式)
    assert "L1-02" in standards
    assert "L1-03" in standards


def 测试规则缺FrontMatter时失败(tmp_path: Path):
    copied, target = _最小规则根(tmp_path)
    text = target.read_text(encoding="utf-8")
    end = text.find("\n---\n", 4)
    target.write_text(text[end + 5 :], encoding="utf-8")
    specs = {"L1-02": target}
    with pytest.raises(标准加载错误):
        加载标准文本(copied, specs, 候选试验模式)


def 测试JSONSchema字段类型错误失败():
    schema_path = ROOT / "00_工程总控" / "工程执行层" / "公共组件" / "结构定义" / "流水线清单结构.json"
    invalid = {
        "schema_version": "xcue.pipeline-manifest/1.0",
        "pipeline_run_id": "RUN-1",
        "created_at": "2026-06-22T00:00:00+08:00",
        "status": "RUNNING",
        "input": {},
        "standards": {},
        "stages": "not-list",
        "final_status": None,
        "final_exit_code": None,
    }
    with pytest.raises(结构错误):
        按结构文件校验(invalid, schema_path, "流水线清单")


def 测试Markdown缺机器规则字段失败():
    reader = _加载读取器("l1_reader_parse_b_test", L1工程 / "L1读取.py")
    standards = reader.读标准(ROOT, 候选试验模式)
    standards["L1-02"] = standards["L1-02"].replace("I = E × V - C", "I 等于一个概念模型")
    with pytest.raises(规则解析错误):
        解析规则(standards)
