from __future__ import annotations

import copy
from pathlib import Path

import pytest

from conftest import ROOT
from 结构校验 import 按结构文件校验
from 工程异常 import 结构错误


pytestmark = pytest.mark.unit

SCHEMA_DIR = ROOT / "00_工程总控" / "工程执行层" / "公共组件" / "结构定义"
RUN_ID = "pytest-pipeline"
SHA256 = "a" * 64


def _schema(name: str) -> Path:
    return SCHEMA_DIR / name


def _artifact(kind: str = "report", stage: str = "L1", run_id: str = "pytest-L1") -> dict:
    return {
        "kind": kind,
        "path": "运行记录/pytest/report.json",
        "sha256": SHA256,
        "producer_stage": stage,
        "producer_run_id": run_id,
    }


def _evidence() -> dict:
    return {"段落": 1, "摘句": "pytest evidence"}


def _failure_item() -> dict:
    return {
        "闸门": "L1-02",
        "名称": "投入意愿不足",
        "状态": "风险",
        "说明": "pytest",
        "证据": [_evidence()],
        "严重级别": "warning",
        "失败类型": "投入意愿不足",
        "候选模块": "L2-05",
        "回流验收位置": "L1-02",
        "修复方向": "补强选择压力",
        "heuristic": True,
        "signal_strength": "UNRANKED_HEURISTIC_SIGNAL",
        "confidence": "UNVALIDATED",
    }


def _gate_result() -> dict:
    return {
        "闸门": "L1-02",
        "判断结果": "REVIEW_REQUIRED",
        "输入材料": ["chapters/ch01.md"],
        "失败类型": ["投入意愿不足"],
        "失败位置": [_evidence()],
        "是否进入L15": "否",
        "调用方向": ["L2-05"],
        "回流验收位置": "L1-02",
        "最终状态": "REVIEW_REQUIRED",
        "检测项": [_failure_item()],
        "规则摘要": {"rule": "pytest"},
    }


def _interface_judgement() -> dict:
    return {
        "来源闸门": "L1-02",
        "输入来源模式": "L1_FAILURE_PACKET",
        "输入问题": "投入意愿不足",
        "初步归属": "市场体验",
        "主候选模块": "L2-05",
        "次候选模块": "",
        "接口失败类型": "投入意愿不足",
        "判断依据": "pytest",
        "是否混合问题": "否",
        "是否越界": "否",
        "建议动作": ["生成 L2 修复单"],
        "回流验收位置": "L1-02",
        "最终状态": "接口明确",
        "备注": "",
    }


def _fix_form() -> dict:
    return {
        "修复单类型": "L2 能力修复单",
        "来源闸门": "L1-02",
        "接收模块": "L2-05",
        "输入问题": "投入意愿不足",
        "主失败类型": "投入意愿不足",
        "次失败类型": "",
        "修复动作": "规划修复动作",
        "修复产物": "任务包",
        "验收问题": "回到 L1-02 复验",
        "回流位置": "L1-02",
        "是否需要其他L2辅助": "否",
        "是否需要回L15重路由": "否",
        "最终状态": "回原闸门复验",
        "标准来源": "L2-05",
        "规则编号": "pytest-rule",
        "规则依据": "pytest",
        "标准动作": ["补强读者投入"],
        "标准验收": ["L1-02 复验"],
    }


def _l3_task() -> dict:
    return {
        "执行编号": "T-001",
        "来源层": "L2-05",
        "来源文件": "运行记录/pytest/第二层/修复报告.json",
        "ProjectHarness根": "70_测试项目/TP-001_CleanHarness_IR_Runtime",
        "任务类型": "正文改写任务规划",
        "输入材料": "投入意愿不足",
        "IR输入": ["IR/IR-01_立项卡.md"],
        "目标文件": "chapters/ch01.md",
        "禁止修改文件": ["AGENTS.md"],
        "修复方向": "规划修复动作",
        "修复产物要求": "任务包",
        "回流验收位置": "L1-02",
        "是否允许改正式正文": "否",
        "是否需要备份": "不适用",
        "执行状态": "TASK_PLANNED",
        "校验问题": [],
        "状态历史": [
            {
                "前状态": "RECEIVED",
                "后状态": "INPUT_VALIDATED",
                "触发事件": "pytest",
                "时间": "2026-06-23T00:00:00+08:00",
                "执行组件": "pytest",
                "证据文件": "pytest",
            }
        ],
    }


def _l3_output() -> dict:
    return {
        "执行编号": "T-001",
        "执行状态": "TASK_PACKAGE_CREATED",
        "实际读取文件": ["IR/IR-01_立项卡.md"],
        "任务包文件": "运行记录/pytest/第三层/任务包.md",
        "分项任务文件": "运行记录/pytest/第三层/分项任务/T-001.md",
        "任务依赖": ["IR 输入完整"],
        "约束": ["不修改正文"],
        "目标文件引用": "chapters/ch01.md",
        "修复产物": "任务包",
        "复验入口": "L1-02",
        "待复验问题": "投入意愿不足",
        "断点记录": "运行记录/pytest/断点记录.md",
        "execution_mode": "TASK_PLANNING_ONLY",
        "prose_modified": False,
        "task_package_created": True,
        "awaiting_executor": True,
    }


def _stage_record() -> dict:
    return {
        "stage": "L1",
        "stage_run_id": "pytest-pipeline-L1",
        "status": "COMPLETED",
        "exit_code": 0,
        "input_artifacts": [_artifact("chapter_snapshot", "INPUT", "pytest-pipeline-INPUT")],
        "output_artifacts": [_artifact("failure_packet", "L1", "pytest-pipeline-L1")],
        "stdout": "{}",
        "stderr": "",
    }


def _valid_samples() -> dict[str, dict]:
    return {
        "失败包结构.json": {
            "schema_version": "xcue.failure-packet/1.0",
            "pipeline_run_id": RUN_ID,
            "stage_run_id": "pytest-pipeline-L1",
            "status": "SCREENING_REJECT",
            "failure_count": 1,
            "items": [_failure_item()],
        },
        "第一层报告结构.json": {
            "schema_version": "xcue.l1-report/1.0",
            "pipeline_run_id": RUN_ID,
            "stage_run_id": "pytest-pipeline-L1",
            "status": "REVIEW_REQUIRED",
            "状态说明": "pytest",
            "publish_authority": False,
            "human_review_required": True,
            "validation_status": "UNVALIDATED",
            "decision_scope": "HEURISTIC_SCREENING",
            "run_id": "pytest-L1",
            "项目": "pytest",
            "章节路径": "chapters/ch01.md",
            "章节标题": "第一章",
            "当前字数": 1200,
            "段落数": 8,
            "方法声明": "pytest",
            "heuristic": True,
            "rule_version": "L1-CANDIDATE-UNVALIDATED",
            "signal_strength": "HEURISTIC_ONLY",
            "confidence": "LOW_UNCALIBRATED",
            "known_limitations": ["pytest"],
            "human_review_reasons": ["pytest"],
            "forbidden_extrapolations": ["pytest"],
            "闸门结果": [_gate_result()],
            "失败包": [_failure_item()],
            "路由建议": [
                {
                    "路由编号": "ROUTE-001",
                    "来源闸门": "L1-02",
                    "主失败类型": "投入意愿不足",
                    "失败位置": "P1",
                    "建议修复方向": "补强选择压力",
                    "接口候选模块": "L2-05",
                    "回流验收位置": "L1-02",
                    "最终状态": "接口明确",
                }
            ],
            "input_artifacts": [_artifact("chapter_snapshot", "INPUT", "pytest-pipeline-INPUT")],
            "output_artifacts": [_artifact("failure_packet", "L1", "pytest-pipeline-L1")],
        },
        "第二层报告结构.json": {
            "schema_version": "xcue.l2-report/1.0",
            "pipeline_run_id": RUN_ID,
            "stage_run_id": "pytest-pipeline-L2",
            "status": "COMPLETED",
            "状态说明": "pytest",
            "run_id": "pytest-L2",
            "输入文件": "运行记录/pytest/第一层/失败包.json",
            "输入数量": 1,
            "方法声明": "pytest",
            "标准校验问题": [],
            "回流校验问题": [],
            "接口判断": [_interface_judgement()],
            "修复单": [_fix_form()],
            "阻断项": [],
            "复验目标": [],
            "input_artifacts": [_artifact("failure_packet", "L1", "pytest-pipeline-L1")],
            "output_artifacts": [_artifact("l2_report", "L2", "pytest-pipeline-L2")],
        },
        "第三层任务包结构.json": {
            "schema_version": "xcue.l3-task-bundle/1.0",
            "pipeline_run_id": RUN_ID,
            "stage_run_id": "pytest-pipeline-L3",
            "status": "AWAITING_EXECUTOR",
            "状态说明": "pytest",
            "run_id": "pytest-L3",
            "输入文件": "运行记录/pytest/第二层/修复报告.json",
            "输入修复单数量": 1,
            "方法声明": "pytest",
            "标准校验问题": [],
            "协议规则摘要": {"状态机步骤数": 1},
            "任务单": [_l3_task()],
            "执行输出": [_l3_output()],
            "阻断任务": [],
            "execution_mode": "TASK_PLANNING_ONLY",
            "prose_modified": False,
            "task_package_created": True,
            "awaiting_executor": True,
            "input_artifacts": [_artifact("l2_report", "L2", "pytest-pipeline-L2")],
            "output_artifacts": [_artifact("l3_task_bundle", "L3", "pytest-pipeline-L3")],
        },
        "流水线清单结构.json": {
            "schema_version": "xcue.pipeline-manifest/1.0",
            "pipeline_run_id": RUN_ID,
            "created_at": "2026-06-23T00:00:00+08:00",
            "status": "RUNNING",
            "input": {
                "original_path": "70_测试项目/TP-001_CleanHarness_IR_Runtime/chapters/ch01.md",
                "snapshot_path": "运行记录/pytest/输入快照/章节正文.md",
                "sha256": SHA256,
            },
            "standards": {
                "source": "Markdown Front Matter",
                "combined_sha256": SHA256,
                "standard_mode": "CANDIDATE_TEST",
                "experimental_standard": True,
                "records": [
                    {
                        "名称": "L1-02",
                        "文档编号": "L1-02",
                        "路径": "20_L1_闸门层/L1-02_读者投入意愿工程图.md",
                        "状态": "CANDIDATE",
                        "版本": "v0.1",
                        "sha256": SHA256,
                        "模式": "CANDIDATE_TEST",
                    }
                ],
                "error": None,
            },
            "stages": [_stage_record()],
            "final_status": None,
            "final_exit_code": None,
        },
        "产物记录结构.json": _artifact("report", "L1", "pytest-L1"),
    }


def _set_path(data: dict, path: tuple, value) -> dict:
    updated = copy.deepcopy(data)
    cursor = updated
    for part in path[:-1]:
        cursor = cursor[part]
    cursor[path[-1]] = value
    return updated


def _drop_path(data: dict, path: tuple) -> dict:
    updated = copy.deepcopy(data)
    cursor = updated
    for part in path[:-1]:
        cursor = cursor[part]
    cursor.pop(path[-1])
    return updated


def _add_root_extra(data: dict) -> dict:
    updated = copy.deepcopy(data)
    updated["unexpected"] = True
    return updated


def _invalid_cases(name: str, valid: dict) -> list[dict]:
    common = [
        _set_path(valid, ("schema_version",), "bad-version") if "schema_version" in valid else _add_root_extra(valid),
        _add_root_extra(valid),
    ]
    if name == "失败包结构.json":
        selected = [
            _drop_path(valid, ("pipeline_run_id",)),
            _set_path(valid, ("pipeline_run_id",), "../bad"),
            _set_path(valid, ("stage_run_id",), "x" * 65),
            _set_path(valid, ("status",), "NOT_A_STATUS"),
            _set_path(valid, ("failure_count",), -1),
            _set_path(valid, ("items",), {}),
            _set_path(valid, ("items", 0, "证据", 0, "段落"), 0),
            _set_path(valid, ("items", 0, "严重级别"), "critical"),
        ]
    elif name == "第一层报告结构.json":
        selected = [
            _drop_path(valid, ("validation_status",)),
            _set_path(valid, ("publish_authority",), True),
            _set_path(valid, ("decision_scope",), "PUBLISH_APPROVAL"),
            _set_path(valid, ("status",), "ACCEPTED"),
            _set_path(valid, ("当前字数",), -1),
            _set_path(valid, ("闸门结果", 0, "判断结果"), "OK"),
            _set_path(valid, ("失败包", 0, "heuristic"), "yes"),
            _set_path(valid, ("output_artifacts", 0, "sha256"), "A" * 64),
        ]
    elif name == "第二层报告结构.json":
        selected = [
            _drop_path(valid, ("方法声明",)),
            _set_path(valid, ("status",), "SCREENING_PASS"),
            _set_path(valid, ("输入数量",), -1),
            _set_path(valid, ("接口判断", 0, "最终状态"), "随便通过"),
            _set_path(valid, ("修复单", 0, "接收模块"), "L4-01"),
            _set_path(valid, ("修复单", 0, "是否需要回L15重路由"), "maybe"),
            _set_path(valid, ("阻断项",), {}),
            _set_path(valid, ("input_artifacts", 0, "path"), "../逃逸.json"),
        ]
    elif name == "第三层任务包结构.json":
        selected = [
            _drop_path(valid, ("execution_mode",)),
            _set_path(valid, ("execution_mode",), "EXECUTE_NOW"),
            _set_path(valid, ("prose_modified",), True),
            _set_path(valid, ("status",), "SCREENING_PASS"),
            _set_path(valid, ("任务单", 0, "执行状态"), "DONE"),
            _set_path(valid, ("执行输出", 0, "execution_mode"), "EXECUTE_NOW"),
            _set_path(valid, ("执行输出", 0, "prose_modified"), True),
            _set_path(valid, ("执行输出", 0, "实际读取文件"), "IR/IR-01.md"),
        ]
    elif name == "流水线清单结构.json":
        selected = [
            _set_path(valid, ("created_at",), "not-a-date"),
            _set_path(valid, ("status",), "DONE"),
            _set_path(valid, ("final_status",), "DONE"),
            _set_path(valid, ("input", "sha256"), "A" * 64),
            _set_path(valid, ("standards", "standard_mode"), "DEV"),
            _set_path(valid, ("standards", "records", 0, "状态"), "DRAFT"),
            _set_path(valid, ("stages", 0, "stage"), "L4"),
            _set_path(valid, ("stages", 0, "exit_code"), -1),
        ]
    elif name == "产物记录结构.json":
        selected = [
            _drop_path(valid, ("producer_run_id",)),
            _set_path(valid, ("sha256",), "A" * 64),
            _set_path(valid, ("sha256",), "abc"),
            _set_path(valid, ("producer_stage",), "L4"),
            _set_path(valid, ("producer_run_id",), "../bad"),
            _set_path(valid, ("path",), ""),
            _set_path(valid, ("path",), "../逃逸.json"),
            _set_path(valid, ("kind",), ""),
        ]
    else:
        raise AssertionError(f"未覆盖的 Schema：{name}")
    result = common + selected
    assert len(result) >= 10
    return result


@pytest.mark.parametrize("schema_name,valid", _valid_samples().items())
def 测试M1_02_六份核心Schema接受合法样本(schema_name: str, valid: dict):
    按结构文件校验(valid, _schema(schema_name), schema_name)


@pytest.mark.parametrize("schema_name,valid", _valid_samples().items())
def 测试M1_02_每份核心Schema至少十组非法样本(schema_name: str, valid: dict):
    for index, invalid in enumerate(_invalid_cases(schema_name, valid), start=1):
        try:
            按结构文件校验(invalid, _schema(schema_name), schema_name)
        except 结构错误:
            continue
        pytest.fail(f"{schema_name} 非法样本 {index} 未被 Schema 拦截")
