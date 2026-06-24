from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

公共组件 = Path(__file__).resolve().parent / "公共组件"
if str(公共组件) not in sys.path:
    sys.path.insert(0, str(公共组件))

from 文件哈希 import 计算文件哈希
from 原子写入 import 原子写文本
from 退出码 import ExitCode
from 工程异常 import 工程错误
from 标准加载器 import 候选试验模式, 加载标准文本, 标准记录转字典
from 生产资格 import 判定结果转标准字段, 要求生产资格
from 结构校验 import 按结构文件校验
from 安全路径 import resolve_inside_root, safe_id, safe_output_path
from 项目加载器 import 项目上下文, 加载项目, 校验项目正文路径
from 错误信封 import 错误信封


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "00_工程总控" / "工程执行层" / "公共组件" / "结构定义"
阶段超时秒 = int(os.environ.get("XCUE_STAGE_TIMEOUT_SECONDS", "120"))


def 新流水线编号() -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"流水线-{stamp}-{uuid.uuid4().hex[:6]}"


def _相对(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _写清单(path: Path, manifest: dict[str, Any]) -> None:
    按结构文件校验(manifest, SCHEMA_DIR / "流水线清单结构.json", "流水线清单")
    原子写文本(path, json.dumps(manifest, ensure_ascii=False, indent=2))


def _写失败清单(path: Path, manifest: dict[str, Any]) -> None:
    try:
        _写清单(path, manifest)
    except 工程错误:
        原子写文本(path, json.dumps(manifest, ensure_ascii=False, indent=2))


def _运行阶段(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        return subprocess.run(
            cmd,
            cwd=str(cwd),
            text=True,
            encoding="utf-8",
            capture_output=True,
            env=env,
            timeout=阶段超时秒,
        )
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(
            cmd,
            int(ExitCode.INTERNAL_ERROR),
            stdout=(exc.stdout or ""),
            stderr=f"FAILED_TIMEOUT: 阶段执行超过 {阶段超时秒} 秒",
        )


def _产物(kind: str, path: Path, stage: str, stage_run_id: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "path": _相对(path),
        "sha256": 计算文件哈希(path),
        "producer_stage": stage,
        "producer_run_id": stage_run_id,
    }


def _项目清单(project: 项目上下文, chapter: Path) -> dict[str, str]:
    return {
        "project_id": project.project_id,
        "project_root": str(project.project_root),
        "project_manifest": str(project.project_manifest),
        "content_root": str(project.content_root),
        "chapter_source": str(chapter),
        "entrypoint": str(project.entrypoint),
        "entrypoint_type": project.entrypoint_type,
        "source_scope": project.source_scope,
    }


def _标准哈希(records: list[dict[str, str]]) -> str:
    joined = "\n".join(
        f"{record.get('名称', '')}:{record.get('路径', '')}:{record.get('版本', '')}:{record.get('状态', '')}:{record.get('sha256', '')}:{record.get('模式', '')}"
        for record in sorted(records, key=lambda item: (item.get("路径", ""), item.get("名称", "")))
    )
    import hashlib

    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _标准路径() -> dict[str, Path]:
    l1 = ROOT / "20_L1_闸门层"
    l15 = ROOT / "30_L1.5_路由矩阵层"
    l2 = ROOT / "40_L2_正式能力层"
    l3 = ROOT / "50_L3_执行协议层"
    return {
        "L1-00": l1 / "L1-00_闸门接口表.md",
        "L1-01": l1 / "L1-01_五大创作问题_技术护栏闭环图.md",
        "L1-02": l1 / "L1-02_读者投入意愿工程图.md",
        "L1-03": l1 / "L1-03_发布锁验收工程图.md",
        "L1.5": l15 / "L1.5_Routing_Matrix.md",
        "L2-00": l2 / "L2-00_正式能力层定义_v0.2.md",
        "L2-01": l2 / "L2-01_叙事结构能力_v0.3.1_边界修正版.md",
        "L2-02": l2 / "L2-02_文风语言能力_v0.3_真源绑定版.md",
        "L2-03": l2 / "L2-03_角色心理能力_v0.1.1_自检修正版.md",
        "L2-04": l2 / "L2-04_创意设定能力_v0.2_根部结构图绑定版.md",
        "L2-05": l2 / "L2-05_市场体验能力_v0.1.1_自检修正版.md",
        "L2-06": l2 / "L2-06_系统一致性与状态管理能力_v0.3.1_技术根修正版.md",
        "L2-99": l2 / "L2-99_能力层接口总表_v0.1.1_自检修正版.md",
        "L3-00": l3 / "L3-00_执行协议总表_v0.1.2.md",
        "L3-01": l3 / "L3-01_Cursor文件操作协议_v0.1.2.md",
        "L3-02": l3 / "L3-02_正文生成与改写任务协议_v0.1.2.md",
        "L3-03": l3 / "L3-03_验收回填协议_v0.1.2.md",
        "L3-04": l3 / "L3-04_版本与回滚协议_v0.1.2.md",
        "L3-05": l3 / "L3-05_日志记录协议_v0.1.2.md",
        "L3-06": l3 / "L3-06_IR输入映射协议_v0.1.2.md",
        "L3-07": l3 / "L3-07_ProjectHarness运行协议_v0.1.2.md",
        "L3-99": l3 / "L3-99_执行禁止项_v0.1.2.md",
    }


def _加载规则血缘(standard_mode: str) -> tuple[list[dict[str, str]], int | None, str | None]:
    specs = _标准路径()
    try:
        _, records = 加载标准文本(ROOT, specs, standard_mode)
    except 工程错误 as exc:
        return [
            {
                "名称": name,
                "路径": path.resolve().relative_to(ROOT.resolve()).as_posix(),
                "模式": standard_mode,
                "错误": str(exc),
            }
            for name, path in sorted(specs.items())
        ], int(exc.exit_code), str(exc)
    return 标准记录转字典(records), None, None


def _阶段记录(stage: str, stage_run_id: str, result: subprocess.CompletedProcess[str], inputs: list[dict[str, Any]], outputs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "stage": stage,
        "stage_run_id": stage_run_id,
        "status": "COMPLETED" if result.returncode == 0 else ("FAILED_TIMEOUT" if "FAILED_TIMEOUT" in (result.stderr or "") else "NONZERO_EXIT"),
        "exit_code": result.returncode,
        "input_artifacts": inputs,
        "output_artifacts": outputs,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def _读取JSON(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise 工程错误(f"{label} JSON 解析失败：{path}: {exc}", ExitCode.SCHEMA_INVALID) from exc
    if not isinstance(data, dict):
        raise 工程错误(f"{label} 必须是 JSON object：{path}", ExitCode.SCHEMA_INVALID)
    return data


def _校验结构文件(path: Path, schema_name: str, label: str) -> None:
    data = _读取JSON(path, label)
    按结构文件校验(data, SCHEMA_DIR / schema_name, label)


def _缺产物状态(stage: str, missing: list[Path]) -> tuple[int, str, str]:
    details = "、".join(_相对(path) for path in missing)
    return int(ExitCode.INTERNAL_ERROR), f"{stage}_OUTPUT_MISSING", f"{stage} 成功返回但缺少必备产物：{details}"


def _最终判定(codes: list[int]) -> tuple[int, str]:
    priority = [
        (int(ExitCode.INTERNAL_ERROR), "FAILED_INTERNAL"),
        (int(ExitCode.SCHEMA_INVALID), "FAILED_SCHEMA"),
        (int(ExitCode.RULE_PARSE_FAILED), "RULE_PARSE_FAILED"),
        (int(ExitCode.HASH_MISMATCH), "FAILED_HASH"),
        (int(ExitCode.LINEAGE_ERROR), "FAILED_LINEAGE"),
        (int(ExitCode.PRODUCTION_MODE_NOT_ELIGIBLE), "PRODUCTION_MODE_NOT_ELIGIBLE"),
        (int(ExitCode.NO_PRODUCTION_RULESET), "NO_PRODUCTION_RULESET"),
        (int(ExitCode.BLOCKED), "BLOCKED"),
        (int(ExitCode.GATE_REJECTED), "GATE_REJECTED"),
        (int(ExitCode.REVIEW_REQUIRED), "REVIEW_REQUIRED"),
    ]
    for code, status in priority:
        if code in codes:
            return code, status
    if any(code != 0 for code in codes):
        return int(ExitCode.INTERNAL_ERROR), "FAILED_INTERNAL"
    return int(ExitCode.OK), "SCREENING_PASS"


def _项目上下文(project: 项目上下文 | str) -> 项目上下文:
    if isinstance(project, 项目上下文):
        return project
    return 加载项目(ROOT, project)


def 运行流水线(chapter: Path, project: 项目上下文 | str, pipeline_run_id: str | None = None, standard_mode: str = 候选试验模式) -> int:
    try:
        project_context = _项目上下文(project)
        chapter = 校验项目正文路径(project_context, chapter or project_context.chapter_source)
        pipeline_id = safe_id(pipeline_run_id, "pipeline_run_id") if pipeline_run_id else safe_id(新流水线编号(), "pipeline_run_id")
        input_stage = safe_id(f"{pipeline_id}-INPUT", "stage_run_id")
        l1_stage = safe_id(f"{pipeline_id}-L1", "stage_run_id")
        l2_stage = safe_id(f"{pipeline_id}-L2", "stage_run_id")
        l3_stage = safe_id(f"{pipeline_id}-L3", "stage_run_id")
    except 工程错误 as exc:
        print(
            json.dumps(
                错误信封(
                    exc,
                    stage="PROJECT_LOADER",
                    run_id=pipeline_run_id or "",
                    path=chapter or "",
                    details=getattr(exc, "details", {}),
                )
                | {"run_root_created": False},
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return int(exc.exit_code)

    run_root = safe_output_path(ROOT, Path("运行记录") / pipeline_id)
    if run_root.exists():
        print(json.dumps({"error": f"运行记录已存在，拒绝覆盖：{run_root}"}, ensure_ascii=False), file=sys.stderr)
        return int(ExitCode.INPUT_INVALID)

    try:
        mode_decision = 要求生产资格(
            requested_mode=standard_mode,
            rule_source=[
                ROOT / "00_工程总控" / "工程执行层" / "L1工程" / "gate_rules.json",
                ROOT / "00_工程总控" / "工程执行层" / "L2工程" / "ability_rules.json",
                ROOT / "00_工程总控" / "工程执行层" / "L2工程" / "routes.json",
                ROOT / "00_工程总控" / "工程执行层" / "L3工程" / "protocol_rules.json",
            ],
            entrypoint="PIPELINE",
            project_identity=project_context.project_id,
        )
    except 工程错误 as exc:
        print(
            json.dumps(
                错误信封(
                    exc,
                    stage="PIPELINE",
                    run_id=pipeline_id,
                    path=chapter,
                    details=getattr(exc, "details", {}),
                )
                | {"run_root_created": False},
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return int(exc.exit_code)

    standard_records, standard_error_code, standard_error = _加载规则血缘(mode_decision.effective_mode or standard_mode)
    if standard_error_code is not None:
        status = "NO_PRODUCTION_RULESET" if standard_error_code == int(ExitCode.NO_PRODUCTION_RULESET) else "STANDARD_PRECHECK_FAILED"
        print(
            json.dumps(
                {
                    "error": status,
                    "message": standard_error,
                    "exit_code": standard_error_code,
                    "standard_mode": mode_decision.effective_mode or standard_mode,
                    "run_root_created": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return standard_error_code

    input_dir = run_root / "输入快照"
    l1_dir = run_root / "第一层"
    l2_dir = run_root / "第二层"
    l3_dir = run_root / "第三层"
    log_dir = run_root / "运行日志"
    for path in [input_dir, l1_dir, l2_dir, l3_dir, log_dir]:
        path.mkdir(parents=True, exist_ok=True)

    snapshot = input_dir / "章节正文.md"
    shutil.copy2(chapter, snapshot)
    input_artifact = _产物("chapter_snapshot", snapshot, "INPUT", input_stage)
    manifest_path = run_root / "流水线清单.json"
    manifest: dict[str, Any] = {
        "schema_version": "xcue.pipeline-manifest/1.0",
        "pipeline_run_id": pipeline_id,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "RUNNING",
        "input": {
            "original_path": str(chapter),
            "snapshot_path": _相对(snapshot),
            "sha256": input_artifact["sha256"],
        },
        "project": _项目清单(project_context, chapter),
        "standards": {
            "source": "Markdown Front Matter",
            "combined_sha256": _标准哈希(standard_records),
            **判定结果转标准字段(mode_decision),
            "records": standard_records,
            "error": standard_error,
        },
        "stages": [],
        "final_status": None,
        "final_exit_code": None,
    }
    try:
        _写清单(manifest_path, manifest)
    except 工程错误 as exc:
        manifest["status"] = "FAILED"
        manifest["final_status"] = "FAILED_SCHEMA"
        manifest["final_exit_code"] = int(exc.exit_code)
        _写失败清单(manifest_path, manifest)
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return int(exc.exit_code)

    l1_cmd = [
        sys.executable,
        str(ROOT / "00_工程总控" / "工程执行层" / "L1工程" / "L1运行入口.py"),
        "--chapter",
        str(snapshot),
        "--project",
        project_context.project_id,
        "--project-manifest",
        str(project_context.project_manifest),
        "--run-id",
        l1_stage,
        "--out-dir",
        str(l1_dir),
        "--pipeline-run-id",
        pipeline_id,
        "--stage-run-id",
        l1_stage,
        "--standard-mode",
        mode_decision.effective_mode or standard_mode,
    ]
    l1_result = _运行阶段(l1_cmd, ROOT)
    l1_report = l1_dir / "检测报告.json"
    l1_packet = l1_dir / "失败包.json"
    l1_missing = [path for path in [l1_report, l1_packet] if not path.exists()]
    if l1_missing:
        status_code = int(l1_result.returncode) if l1_result.returncode != 0 else _缺产物状态("L1", l1_missing)[0]
        status_name = "FAILED_SCHEMA" if status_code == int(ExitCode.SCHEMA_INVALID) else ("FAILED_LINEAGE" if status_code == int(ExitCode.LINEAGE_ERROR) else ("L1_OUTPUT_MISSING" if l1_result.returncode == 0 else "L1_STAGE_FAILED"))
        manifest["status"] = "FAILED"
        manifest["final_status"] = status_name
        manifest["final_exit_code"] = status_code
        manifest["stages"].append(_阶段记录("L1", l1_stage, l1_result, [input_artifact], []))
        _写失败清单(manifest_path, manifest)
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return status_code
    try:
        _校验结构文件(l1_report, "第一层报告结构.json", "L1 检测报告")
        _校验结构文件(l1_packet, "失败包结构.json", "L1 失败包")
    except 工程错误 as exc:
        manifest["status"] = "FAILED"
        manifest["final_status"] = "FAILED_SCHEMA"
        manifest["final_exit_code"] = int(exc.exit_code)
        manifest["stages"].append(_阶段记录("L1", l1_stage, l1_result, [input_artifact], []))
        _写失败清单(manifest_path, manifest)
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return int(exc.exit_code)
    l1_outputs = [
        _产物("l1_report", l1_report, "L1", l1_stage),
        _产物("l1_failure_packet", l1_packet, "L1", l1_stage),
    ]
    manifest["stages"].append(_阶段记录("L1", l1_stage, l1_result, [input_artifact], l1_outputs))
    _写清单(manifest_path, manifest)

    l2_cmd = [
        sys.executable,
        str(ROOT / "00_工程总控" / "工程执行层" / "L2工程" / "L2运行入口.py"),
        "--failure-packet",
        str(l1_packet),
        "--run-id",
        l2_stage,
        "--out-dir",
        str(l2_dir),
        "--pipeline-run-id",
        pipeline_id,
        "--stage-run-id",
        l2_stage,
        "--expected-input-sha256",
        l1_outputs[1]["sha256"],
        "--standard-mode",
        mode_decision.effective_mode or standard_mode,
    ]
    l2_result = _运行阶段(l2_cmd, ROOT)
    l2_report = l2_dir / "修复报告.json"
    l2_outputs = [_产物("l2_report", l2_report, "L2", l2_stage)] if l2_report.exists() else []
    manifest["stages"].append(_阶段记录("L2", l2_stage, l2_result, [l1_outputs[1]], l2_outputs))
    _写清单(manifest_path, manifest)
    if l2_result.returncode == 0 and not l2_report.exists():
        final_exit, final_status = _缺产物状态("L2", [l2_report])[:2]
        manifest["status"] = "FAILED"
        manifest["final_status"] = final_status
        manifest["final_exit_code"] = final_exit
        _写失败清单(manifest_path, manifest)
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return final_exit
    if l2_report.exists():
        try:
            _校验结构文件(l2_report, "第二层报告结构.json", "L2 修复报告")
        except 工程错误 as exc:
            manifest["status"] = "FAILED"
            manifest["final_status"] = "FAILED_SCHEMA"
            manifest["final_exit_code"] = int(exc.exit_code)
            _写失败清单(manifest_path, manifest)
            print(json.dumps(manifest, ensure_ascii=False, indent=2))
            return int(exc.exit_code)

    l3_outputs: list[dict[str, Any]] = []
    l3_result: subprocess.CompletedProcess[str] | None = None
    if l2_result.returncode == int(ExitCode.BLOCKED):
        manifest["stages"].append(
            {
                "stage": "L3",
                "stage_run_id": l3_stage,
                "status": "SKIPPED",
                "exit_code": int(ExitCode.BLOCKED),
                "reason": "L2 已阻断，L3 不生成任务包。",
                "input_artifacts": l2_outputs,
                "output_artifacts": [],
            }
        )
    elif l2_report.exists():
        l3_cmd = [
            sys.executable,
            str(ROOT / "00_工程总控" / "工程执行层" / "L3工程" / "L3运行入口.py"),
            "--l2-report",
            str(l2_report),
            "--run-id",
            l3_stage,
            "--out-dir",
            str(l3_dir),
            "--pipeline-run-id",
            pipeline_id,
            "--stage-run-id",
            l3_stage,
            "--expected-input-sha256",
            l2_outputs[0]["sha256"] if l2_outputs else "",
            "--standard-mode",
            mode_decision.effective_mode or standard_mode,
            "--project-harness",
            str(project_context.project_root),
        ]
        l3_result = _运行阶段(l3_cmd, ROOT)
        l3_report = l3_dir / "任务包.json"
        if l3_report.exists():
            l3_outputs.append(_产物("l3_task_bundle", l3_report, "L3", l3_stage))
        manifest["stages"].append(_阶段记录("L3", l3_stage, l3_result, l2_outputs, l3_outputs))
        if l3_result.returncode == 0 and not l3_report.exists():
            final_exit, final_status = _缺产物状态("L3", [l3_report])[:2]
            manifest["status"] = "FAILED"
            manifest["final_status"] = final_status
            manifest["final_exit_code"] = final_exit
            _写失败清单(manifest_path, manifest)
            print(json.dumps(manifest, ensure_ascii=False, indent=2))
            return final_exit
        if l3_report.exists():
            try:
                _校验结构文件(l3_report, "第三层任务包结构.json", "L3 任务包")
            except 工程错误 as exc:
                manifest["status"] = "FAILED"
                manifest["final_status"] = "FAILED_SCHEMA"
                manifest["final_exit_code"] = int(exc.exit_code)
                _写失败清单(manifest_path, manifest)
                print(json.dumps(manifest, ensure_ascii=False, indent=2))
                return int(exc.exit_code)

    codes = [int(l1_result.returncode), int(l2_result.returncode)]
    if standard_error_code is not None:
        codes.append(standard_error_code)
    if l3_result is not None:
        codes.append(int(l3_result.returncode))
    elif l2_result.returncode == int(ExitCode.BLOCKED):
        codes.append(int(ExitCode.BLOCKED))
    final_exit, final_status = _最终判定(codes)
    manifest["status"] = "COMPLETED" if final_exit == 0 else "FAILED"
    manifest["final_status"] = final_status
    manifest["final_exit_code"] = final_exit
    _写清单(manifest_path, manifest)
    print(json.dumps({"pipeline_run_id": pipeline_id, "run_root": str(run_root), "manifest": str(manifest_path), "final_exit_code": final_exit}, ensure_ascii=False, indent=2))
    return final_exit
