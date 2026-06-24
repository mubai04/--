from __future__ import annotations

import json
import subprocess
import sys
import uuid
import hashlib
import shutil
from pathlib import Path

import pytest

from conftest import ROOT

L2工程 = ROOT / "00_工程总控" / "工程执行层" / "L2工程"
if str(L2工程) not in sys.path:
    sys.path.insert(0, str(L2工程))

from 退出码 import ExitCode
from L2模型 import 失败输入
from L2_99_接口判断 import 判断
from 能力标准解析 import L2规则
from 路由规则加载 import 加载路由规则


pytestmark = pytest.mark.integration


def _写失败包(path: Path, items: list[dict]) -> None:
    payload = {
        "schema_version": "xcue.failure-packet/1.0",
        "pipeline_run_id": "pytest-pipeline",
        "stage_run_id": "pytest-pipeline-L1",
        "status": "SCREENING_REJECT",
        "failure_count": len(items),
        "items": items,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _失败项(name: str, failure_type: str, candidate: str, return_gate: str = "L1-02") -> dict:
    return {
        "闸门": "L1-03",
        "名称": name,
        "状态": "风险",
        "说明": name,
        "证据": [],
        "严重级别": "warning",
        "失败类型": failure_type,
        "候选模块": candidate,
        "回流验收位置": return_gate,
        "修复方向": "pytest 修复方向",
    }


def _失败项带证据(
    name: str,
    failure_type: str,
    evidence: list[dict],
    candidate: str = "L2-01",
    return_gate: str = "L1-01",
    direction: str = "pytest 修复方向",
) -> dict:
    item = _失败项(name, failure_type, candidate, return_gate)
    item["证据"] = evidence
    item["修复方向"] = direction
    return item


def _运行L2(packet: Path, out_dir: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "00_工程总控" / "工程执行层" / "L2工程" / "L2运行入口.py"),
            "--failure-packet",
            str(packet),
            "--run-id",
            "pytest-L2-" + uuid.uuid4().hex[:8],
            "--out-dir",
            str(out_dir),
            "--pipeline-run-id",
            "pytest-pipeline",
            "--stage-run-id",
            "pytest-pipeline-L2",
            "--standard-mode",
            "CANDIDATE_TEST",
        ],
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        env=env,
        timeout=30,
    )


def _运行L2固定编号(packet: Path, out_dir: Path, env: dict[str, str], run_id: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "00_工程总控" / "工程执行层" / "L2工程" / "L2运行入口.py"),
            "--failure-packet",
            str(packet),
            "--run-id",
            run_id,
            "--out-dir",
            str(out_dir),
            "--pipeline-run-id",
            "pytest-pipeline",
            "--stage-run-id",
            "pytest-pipeline-L2",
            "--standard-mode",
            "CANDIDATE_TEST",
        ],
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        env=env,
        timeout=30,
    )


def _运行L2带规则文件(
    packet: Path,
    out_dir: Path,
    env: dict[str, str],
    rules_path: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "00_工程总控" / "工程执行层" / "L2工程" / "L2运行入口.py"),
            "--failure-packet",
            str(packet),
            "--run-id",
            "pytest-L2-a3-" + uuid.uuid4().hex[:8],
            "--out-dir",
            str(out_dir),
            "--pipeline-run-id",
            "pytest-pipeline",
            "--stage-run-id",
            "pytest-pipeline-L2",
            "--standard-mode",
            "CANDIDATE_TEST",
            "--ability-rules",
            str(rules_path),
        ],
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        env=env,
        timeout=30,
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _读取运行报告(result: subprocess.CompletedProcess[str]) -> dict:
    payload = json.loads(result.stdout)
    return json.loads(Path(payload["report_json"]).read_text(encoding="utf-8"))


def _读取固定报告(out_dir: Path) -> dict:
    return json.loads((out_dir / "修复报告.json").read_text(encoding="utf-8"))


def _复制L2能力规则(root_case: Path) -> Path:
    source = ROOT / "00_工程总控" / "工程执行层" / "L2工程" / "ability_rules.json"
    target = root_case / "ability_rules.json"
    shutil.copyfile(source, target)
    return target


def _L2路由规则文件() -> Path:
    return ROOT / "00_工程总控" / "工程执行层" / "L2工程" / "routes.json"


def _改写L205首条修复规则(path: Path, marker: str) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    first = payload["abilities"]["L2-05"]["failure_types"][0]
    first["repair_rules"] = [marker]
    first["acceptance"] = [marker + "-验收"]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _改写L201规则为B1可读样本(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    ability = payload["abilities"]["L2-01"]
    ability["failure_types"] = [
        {
            "id": "F01",
            "name": "主线发散",
            "definition": "结构单元内多个方向同时成立，没有唯一推进轴。",
            "signals": ["多个事件都像主线", "读者不知道该关注哪一个问题"],
            "repair_rules": ["主线锁定", "支线降级为压力线"],
            "acceptance": ["结构单元只能压缩成一个主体目标和一个核心阻力。"],
            "match_keywords": ["主线发散", "主线"],
        },
        {
            "id": "F03",
            "name": "条件链断裂",
            "definition": "后一事件缺少前置条件，因果链不能闭合。",
            "signals": ["突然发生", "不知道为什么进入下一步"],
            "repair_rules": ["条件补全", "补充后一事件成立所需的前置条件"],
            "acceptance": ["每个关键事件都能回答因为前面发生了什么，所以现在必须发生什么。"],
            "match_keywords": ["条件链断裂", "突然发生", "条件"],
        },
        {
            "id": "F10",
            "name": "疑似越界 / 建议回 L1.5 重路由",
            "definition": "问题表面像结构问题，但主因可能属于其他专题能力。",
            "signals": ["文风", "角色心理", "市场"],
            "repair_rules": ["建议回 L1.5 重路由"],
            "acceptance": ["不得生成候选修复。"],
            "match_keywords": ["文风", "角色心理", "市场", "越界"],
        },
    ]
    ability["default_actions"] = {"*": ["主线锁定"]}
    ability["acceptance_questions"] = [
        "结构单元主行动线是否唯一？",
        "条件链是否闭合？",
        "是否存在需要回 L1.5 重路由的越界问题？",
    ]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _B1诊断(report: dict) -> list[dict]:
    return report["extensions"]["L2-01真实诊断"]


def 测试A03_L2重叠关键词按最长专词路由(root_case):
    routes_path = root_case / "routes.json"
    routes_path.write_text(
        json.dumps(
            {
                "schema_version": "xcue.l2-routes/1.0",
                "version": "pytest-a03",
                "status": "active",
                "routes": [
                    {
                        "rule_id": "GENERIC",
                        "keywords": ["认知成本"],
                        "target": "L2-02",
                        "source": "pytest",
                    },
                    {
                        "rule_id": "SPECIFIC",
                        "keywords": ["认知成本过高"],
                        "target": "L2-05",
                        "source": "pytest",
                    },
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    rules = L2规则(路由规则集=加载路由规则(routes_path))
    item = 失败输入(
        来源闸门="L1-02",
        名称="入口认知成本过高",
        状态="风险",
        说明="C高：认知成本过高导致弃读点明显。",
        证据=[],
        严重级别="warning",
        失败类型="认知成本过高",
        候选模块="",
        回流验收位置="L1-02",
        修复方向="降低认知成本",
    )

    judgement = 判断(item, rules)

    assert judgement.主候选模块 == "L2-05"
    assert judgement.route_rule_id == "SPECIFIC"


def 测试A04_L2路由规则加载失败不生成修复单且不回退(root_case, test_io_env):
    packet = root_case / "失败包.json"
    out_dir = root_case / "第二层"
    routes_path = _L2路由规则文件()
    before = routes_path.read_text(encoding="utf-8")
    _写失败包(packet, [_失败项("入口弱", "入口弱", "L2-05")])
    try:
        routes_path.write_text(
            json.dumps(
                {
                    "schema_version": "xcue.l2-routes/1.0",
                    "version": "pytest-a04-bad",
                    "status": "active",
                    "routes": [{"rule_id": "BROKEN", "keywords": ["入口弱"], "target": "L2-99"}],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        result = _运行L2(packet, out_dir, test_io_env)
    finally:
        routes_path.write_text(before, encoding="utf-8")

    assert result.returncode == int(ExitCode.RULE_PARSE_FAILED)
    payload = json.loads(result.stderr)
    assert payload["error_code"] == "RULE_PARSE_FAILED"
    assert payload["reason"] == "RULE_TARGET_INVALID"
    assert payload["location"] == "routes[0].target"
    assert payload["error"]["details"]["reason"] == "RULE_TARGET_INVALID"
    assert payload["error"]["details"]["location"] == "routes[0].target"
    assert not (out_dir / "修复报告.json").exists()
    assert not (out_dir / "修复报告.md").exists()


def 测试L2普通失败生成修复单(root_case, test_io_env):
    packet = root_case / "失败包.json"
    out_dir = root_case / "第二层"
    _写失败包(packet, [_失败项("入口弱", "入口弱", "L2-05")])
    result = _运行L2(packet, out_dir, test_io_env)
    assert result.returncode == int(ExitCode.OK), result.stderr
    report = json.loads((out_dir / "修复报告.json").read_text(encoding="utf-8"))
    assert len(report["修复单"]) == 1
    assert report["阻断项"] == []


def 测试L2普通失败加派生复验项不全局阻断(root_case, test_io_env):
    packet = root_case / "失败包.json"
    out_dir = root_case / "第二层"
    _写失败包(
        packet,
        [
            _失败项("入口弱", "入口弱", "L2-05"),
            _失败项("投入意愿前置", "投入意愿不足", "回L1-02", "L1-02"),
        ],
    )
    result = _运行L2(packet, out_dir, test_io_env)
    assert result.returncode == int(ExitCode.OK), result.stderr
    report = json.loads((out_dir / "修复报告.json").read_text(encoding="utf-8"))
    assert len(report["修复单"]) == 1
    assert report["阻断项"] == []
    assert report["复验目标"][0]["最终状态"] == "派生复验"


def 测试L2只有派生复验项合法NOOP(root_case, test_io_env):
    packet = root_case / "失败包.json"
    out_dir = root_case / "第二层"
    _写失败包(packet, [_失败项("投入意愿前置", "投入意愿不足", "回L1-02", "L1-02")])
    result = _运行L2(packet, out_dir, test_io_env)
    assert result.returncode == int(ExitCode.OK), result.stderr
    report = json.loads((out_dir / "修复报告.json").read_text(encoding="utf-8"))
    assert report["修复单"] == []
    assert report["阻断项"] == []
    assert len(report["复验目标"]) == 1


def 测试L2真实越界仍然阻断(root_case, test_io_env):
    packet = root_case / "失败包.json"
    out_dir = root_case / "第二层"
    _写失败包(packet, [_失败项("运营越界", "外部运营", "外部运营层")])
    result = _运行L2(packet, out_dir, test_io_env)
    assert result.returncode == int(ExitCode.BLOCKED)
    report = json.loads((out_dir / "修复报告.json").read_text(encoding="utf-8"))
    assert report["阻断项"]


def 测试L2同RunID任一既有产物存在时拒绝且不覆盖(root_case, test_io_env):
    packet = root_case / "失败包.json"
    out_dir = root_case / "第二层"
    run_id = "pytest-L2-fixed-" + uuid.uuid4().hex[:8]
    _写失败包(packet, [_失败项("入口弱", "入口弱", "L2-05")])

    first = _运行L2固定编号(packet, out_dir, test_io_env, run_id)
    assert first.returncode == int(ExitCode.OK), first.stderr
    json_path = out_dir / "修复报告.json"
    md_path = out_dir / "修复报告.md"
    assert json_path.exists()
    assert md_path.exists()
    before_json = _sha256(json_path)
    before_md = _sha256(md_path)
    before_files = sorted(path.relative_to(out_dir).as_posix() for path in out_dir.rglob("*") if path.is_file())

    second = _运行L2固定编号(packet, out_dir, test_io_env, run_id)

    assert second.returncode == int(ExitCode.INPUT_INVALID)
    payload = json.loads(second.stderr)
    assert payload["error_code"] == "INPUT_INVALID"
    assert _sha256(json_path) == before_json
    assert _sha256(md_path) == before_md
    after_files = sorted(path.relative_to(out_dir).as_posix() for path in out_dir.rglob("*") if path.is_file())
    assert after_files == before_files


@pytest.mark.parametrize("existing_name,forbidden_name", [("修复报告.json", "修复报告.md"), ("修复报告.md", "修复报告.json")])
def 测试L2任一单独既有产物存在时拒绝且不生成部分新文件(root_case, test_io_env, existing_name, forbidden_name):
    packet = root_case / "失败包.json"
    out_dir = root_case / "第二层"
    run_id = "pytest-L2-fixed-" + uuid.uuid4().hex[:8]
    _写失败包(packet, [_失败项("入口弱", "入口弱", "L2-05")])
    out_dir.mkdir(parents=True)
    existing = out_dir / existing_name
    forbidden = out_dir / forbidden_name
    existing.write_text("历史产物\n", encoding="utf-8")
    before_hash = _sha256(existing)

    result = _运行L2固定编号(packet, out_dir, test_io_env, run_id)

    assert result.returncode == int(ExitCode.INPUT_INVALID)
    payload = json.loads(result.stderr)
    assert payload["error_code"] == "INPUT_INVALID"
    assert _sha256(existing) == before_hash
    assert not forbidden.exists()


def 测试A3结构化能力规则改动会改变L2修复单(root_case, test_io_env):
    packet = root_case / "失败包.json"
    out_dir = root_case / "第二层"
    rules_path = _复制L2能力规则(root_case)
    marker = "A3-结构化规则动作-市场入口"
    _改写L205首条修复规则(rules_path, marker)
    _写失败包(packet, [_失败项("入口弱", "入口弱", "L2-05")])

    result = _运行L2带规则文件(packet, out_dir, test_io_env, rules_path)

    assert result.returncode == int(ExitCode.OK), result.stderr
    report = json.loads((out_dir / "修复报告.json").read_text(encoding="utf-8"))
    form = report["修复单"][0]
    assert marker in form["修复动作"]
    assert marker in form["标准动作"]
    assert form["规则编号"]
    assert form["规则依据"]
    assert form["rule_id"] == "L2-05:P1"
    assert form["rule_version"] == "2026-06-24.a3-01"
    assert len(form["rule_hash"]) == 64


def 测试A3Markdown能力标准改动不改变L2运行行为(root_case, test_io_env):
    packet = root_case / "失败包.json"
    out_dir_a = root_case / "A" / "第二层"
    out_dir_b = root_case / "B" / "第二层"
    rules_path = _复制L2能力规则(root_case)
    _写失败包(packet, [_失败项("入口弱", "入口弱", "L2-05")])

    first = _运行L2带规则文件(packet, out_dir_a, test_io_env, rules_path)
    assert first.returncode == int(ExitCode.OK), first.stderr

    markdown_source = ROOT / "40_L2_正式能力层" / "L2-05_市场体验能力_v0.1.1_自检修正版.md"
    before = markdown_source.read_text(encoding="utf-8")
    try:
        markdown_source.write_text(before + "\n\n<!-- A3 pytest markdown mutation should not affect runtime rules -->\n", encoding="utf-8")
        second = _运行L2带规则文件(packet, out_dir_b, test_io_env, rules_path)
    finally:
        markdown_source.write_text(before, encoding="utf-8")

    assert second.returncode == int(ExitCode.OK), second.stderr
    report_a = json.loads((out_dir_a / "修复报告.json").read_text(encoding="utf-8"))
    report_b = json.loads((out_dir_b / "修复报告.json").read_text(encoding="utf-8"))
    assert report_a["修复单"] == report_b["修复单"]


def 测试A3结构化能力规则坏文件在写报告前失败(root_case, test_io_env):
    packet = root_case / "失败包.json"
    out_dir = root_case / "第二层"
    bad_rules = root_case / "bad_ability_rules.json"
    bad_rules.write_text('{"schema_version":"xcue.l2-ability-rules/1.0","abilities":{}}', encoding="utf-8")
    _写失败包(packet, [_失败项("入口弱", "入口弱", "L2-05")])

    result = _运行L2带规则文件(packet, out_dir, test_io_env, bad_rules)

    assert result.returncode == int(ExitCode.RULE_PARSE_FAILED)
    payload = json.loads(result.stderr)
    assert payload["error_code"] == "RULE_PARSE_FAILED"
    assert not (out_dir / "修复报告.json").exists()
    assert not (out_dir / "修复报告.md").exists()


def 测试A3结构化匹配关键词控制失败规则选择(root_case, test_io_env):
    packet = root_case / "失败包.json"
    out_dir = root_case / "第二层"
    rules_path = _复制L2能力规则(root_case)
    payload = json.loads(rules_path.read_text(encoding="utf-8"))
    for failure in payload["abilities"]["L2-05"]["failure_types"]:
        failure["signals"] = []
        failure["definition"] = ""
        failure["repair_rules"] = []
        failure["match_keywords"] = []
    first = payload["abilities"]["L2-05"]["failure_types"][0]
    first["match_keywords"] = ["A3独占失败"]
    first["repair_rules"] = ["A3独占结构化动作"]
    rules_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _写失败包(packet, [_失败项("A3独占失败", "A3独占失败", "L2-05")])

    result = _运行L2带规则文件(packet, out_dir, test_io_env, rules_path)

    assert result.returncode == int(ExitCode.OK), result.stderr
    report = json.loads((out_dir / "修复报告.json").read_text(encoding="utf-8"))
    form = report["修复单"][0]
    assert form["规则编号"] == "P1"
    assert form["标准动作"] == ["A3独占结构化动作"]


def 测试B1_L201正例生成真实诊断与候选策略(root_case, test_io_env):
    packet = root_case / "失败包.json"
    out_dir = root_case / "第二层"
    rules_path = _复制L2能力规则(root_case)
    _改写L201规则为B1可读样本(rules_path)
    anchor = "沈照决定追查账册，同时又答应护送商队，还想去找失踪的师兄。"
    _写失败包(
        packet,
        [
            _失败项带证据(
                "主线发散",
                "主线发散",
                [{"段落": 3, "摘句": anchor}],
                direction="锁定沈照追查账册为主行动线",
            )
        ],
    )

    result = _运行L2带规则文件(packet, out_dir, test_io_env, rules_path)

    assert result.returncode == int(ExitCode.OK), result.stderr
    report = _读取固定报告(out_dir)
    diagnosis = _B1诊断(report)[0]
    assert diagnosis["问题类型"] == "主线发散"
    assert diagnosis["证据锚点"] == [{"段落": 3, "摘句": anchor}]
    assert diagnosis["涉及段落"] == [3]
    assert "结构单元内多个方向同时成立" in diagnosis["原因诊断"]
    assert diagnosis["修改目标"] == "锁定沈照追查账册为主行动线"
    assert diagnosis["候选修改策略"] == ["主线锁定", "支线降级为压力线"]
    assert diagnosis["自动修复资格判定"] == "可自动修复"
    assert diagnosis["置信度"] == "高"
    assert report["修复单"][0]["规则编号"] == "F01"


def 测试B1_L201反例未命中结构问题不生成修复(root_case, test_io_env):
    packet = root_case / "失败包.json"
    out_dir = root_case / "第二层"
    rules_path = _复制L2能力规则(root_case)
    _改写L201规则为B1可读样本(rules_path)
    _写失败包(
        packet,
        [
            _失败项带证据(
                "已闭合结构",
                "结构正常",
                [{"段落": 1, "摘句": "沈照只保留追查账册这一条行动线，其余信息都服务于账册。"}],
            )
        ],
    )

    result = _运行L2带规则文件(packet, out_dir, test_io_env, rules_path)

    assert result.returncode == int(ExitCode.OK), result.stderr
    report = _读取固定报告(out_dir)
    diagnosis = _B1诊断(report)[0]
    assert report["修复单"] == []
    assert diagnosis["自动修复资格判定"] == "无需修复"
    assert diagnosis["候选修改策略"] == []
    assert diagnosis["置信度"] == "低"


def 测试B1_L201证据不足不伪造定位(root_case, test_io_env):
    packet = root_case / "失败包.json"
    out_dir = root_case / "第二层"
    rules_path = _复制L2能力规则(root_case)
    _改写L201规则为B1可读样本(rules_path)
    _写失败包(packet, [_失败项带证据("主线发散", "主线发散", [])])

    result = _运行L2带规则文件(packet, out_dir, test_io_env, rules_path)

    assert result.returncode == int(ExitCode.OK), result.stderr
    report = _读取固定报告(out_dir)
    diagnosis = _B1诊断(report)[0]
    assert report["修复单"] == []
    assert diagnosis["证据锚点"] == []
    assert diagnosis["涉及段落"] == []
    assert diagnosis["自动修复资格判定"] == "需人工判断"
    assert diagnosis["置信度"] == "低"
    assert any("证据不足" in risk for risk in diagnosis["风险"])


def 测试B1_L201越界样例不生成候选修复(root_case, test_io_env):
    packet = root_case / "失败包.json"
    out_dir = root_case / "第二层"
    rules_path = _复制L2能力规则(root_case)
    _改写L201规则为B1可读样本(rules_path)
    _写失败包(
        packet,
        [
            _失败项带证据(
                "文风过白",
                "文风",
                [{"段落": 2, "摘句": "这段对白只有语气问题，结构行动线仍然清晰。"}],
            )
        ],
    )

    result = _运行L2带规则文件(packet, out_dir, test_io_env, rules_path)

    assert result.returncode == int(ExitCode.OK), result.stderr
    report = _读取固定报告(out_dir)
    diagnosis = _B1诊断(report)[0]
    assert report["修复单"] == []
    assert diagnosis["自动修复资格判定"] == "禁止处理"
    assert diagnosis["候选修改策略"] == []
    assert any("回 L1.5" in risk for risk in diagnosis["风险"])


def 测试B1_L201不同正文问题产生不同诊断和策略(root_case, test_io_env):
    packet = root_case / "失败包.json"
    out_dir = root_case / "第二层"
    rules_path = _复制L2能力规则(root_case)
    _改写L201规则为B1可读样本(rules_path)
    _写失败包(
        packet,
        [
            _失败项带证据(
                "主线发散",
                "主线发散",
                [{"段落": 3, "摘句": "沈照同时追账册、护商队、寻师兄，三条线都像主线。"}],
            ),
            _失败项带证据(
                "条件链断裂",
                "条件链断裂",
                [{"段落": 7, "摘句": "没有任何铺垫，密室门突然打开，沈照直接拿到账册。"}],
            ),
        ],
    )

    result = _运行L2带规则文件(packet, out_dir, test_io_env, rules_path)

    assert result.returncode == int(ExitCode.OK), result.stderr
    report = _读取固定报告(out_dir)
    first, second = _B1诊断(report)
    assert first["问题类型"] == "主线发散"
    assert second["问题类型"] == "条件链断裂"
    assert first["候选修改策略"] == ["主线锁定", "支线降级为压力线"]
    assert second["候选修改策略"] == ["条件补全", "补充后一事件成立所需的前置条件"]
    assert first["原因诊断"] != second["原因诊断"]
