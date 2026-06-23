#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True

公共组件 = Path(__file__).resolve().parents[1] / "公共组件"
if str(公共组件) not in sys.path:
    sys.path.insert(0, str(公共组件))

from 正文切分 import 切段, 正文字数, 清理正文
from L1报告 import 写报告, 拒绝覆盖既有报告
from L1模型 import 正文检测结果
from L1读取 import 读文本, 读标准
from 闸门标准解析 import 解析规则
from L15交接 import 生成路由建议
from 失败包生成 import 生成失败包
import L1_前置质量护栏
import L1_00_闸门接口校验
import L1_01_内部创作检测
import L1_02_读者投入检测
import L1_03_发布锁检测
from 退出码 import ExitCode
from 工程异常 import 工程错误
from 运行状态 import 状态说明, 机器初筛通过, 机器初筛退回, 需要人工复核
from 标准加载器 import 候选试验模式, 生产模式
from 安全路径 import resolve_inside_root, safe_id
from 错误信封 import 打印错误信封


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CHAPTER = ROOT / "70_测试项目" / "TP-001_CleanHarness_IR_Runtime" / "chapters" / "_candidates" / "ch01_candidate_RUN-20260621-002.md"
测试IO令牌内容 = "XCUE_TEST_EXTERNAL_IO_TOKEN_V1"


def _允许测试外部IO() -> bool:
    if os.environ.get("XCUE_TEST_ALLOW_EXTERNAL_IO") != "1":
        return False
    token_path = os.environ.get("XCUE_TEST_IO_TOKEN_FILE", "")
    if not token_path:
        return False
    resolved = Path(token_path).resolve()
    try:
        resolved.relative_to(Path(tempfile.gettempdir()).resolve())
    except ValueError:
        return False
    try:
        return resolved.read_text(encoding="utf-8") == 测试IO令牌内容
    except OSError:
        return False


def _解析输入输出路径(value: str | Path, label: str) -> Path:
    if _允许测试外部IO():
        resolved = Path(value).resolve()
        try:
            resolved.relative_to(Path(tempfile.gettempdir()).resolve())
        except ValueError:
            return resolve_inside_root(ROOT, value)
        return resolved
    return resolve_inside_root(ROOT, value)


def main() -> int:
    parser = argparse.ArgumentParser(description="XC-UE L1工程：把 L1 Markdown 闸门标准转成对章节正文的检测报告。")
    parser.add_argument("--chapter", default=str(DEFAULT_CHAPTER), help="待检测正文 Markdown 路径。")
    parser.add_argument("--run-id", default=None, help="报告编号。")
    parser.add_argument("--project", default="未命名项目", help="项目名。")
    parser.add_argument("--out-dir", default=None, help="输出目录。")
    parser.add_argument("--pipeline-run-id", default="", help="流水线编号。")
    parser.add_argument("--stage-run-id", default="", help="阶段运行编号。")
    parser.add_argument("--standard-mode", default=候选试验模式, choices=[生产模式, 候选试验模式], help="标准加载模式。")
    args = parser.parse_args()

    try:
        run_id = safe_id(args.run_id or "L1_RUN-" + datetime.now().strftime("%Y%m%d-%H%M%S"), "run_id")
        pipeline_run_id = safe_id(args.pipeline_run_id, "pipeline_run_id") if args.pipeline_run_id else ""
        stage_run_id = safe_id(args.stage_run_id, "stage_run_id") if args.stage_run_id else ""
        chapter_path = _解析输入输出路径(args.chapter, "chapter")
        out_dir = _解析输入输出路径(args.out_dir, "out_dir") if args.out_dir else Path(__file__).resolve().parent / "reports"
        拒绝覆盖既有报告(run_id, out_dir)
    except 工程错误 as exc:
        打印错误信封(exc, stage="L1", run_id=locals().get("run_id", ""), path=locals().get("out_dir", ""))
        return int(exc.exit_code)
    if not chapter_path.exists():
        raise SystemExit(ExitCode.INPUT_INVALID)

    raw = 读文本(chapter_path)
    if not raw.strip():
        raise SystemExit(ExitCode.INPUT_INVALID)
    try:
        standards = 读标准(ROOT, args.standard_mode)
        rules = 解析规则(standards)
    except 工程错误 as exc:
        print(json.dumps({"error": str(exc), "exit_code": int(exc.exit_code)}, ensure_ascii=False), file=sys.stderr)
        return int(exc.exit_code)
    title, body = 清理正文(raw)
    paragraphs = 切段(body)
    if not paragraphs:
        raise SystemExit(ExitCode.INPUT_INVALID)
    word_count = 正文字数(paragraphs)

    l101 = L1_01_内部创作检测.检测(paragraphs, rules.L101)
    l101_passed = l101.判断结果 == "STRUCTURE_SIGNAL_PRESENT"
    l102 = L1_02_读者投入检测.检测(paragraphs, rules.L102, l101_passed)
    l102_passed = l102.判断结果 == "STRUCTURE_SIGNAL_PRESENT"
    l103 = L1_03_发布锁检测.检测(paragraphs, word_count, rules.L103, l102_passed)

    gates = [l101, l102, l103]
    l100 = L1_00_闸门接口校验.检测(gates, standards)
    guard_items = L1_前置质量护栏.检测(paragraphs)
    l100.检测项.extend(guard_items)
    if guard_items:
        l100.失败类型.extend([item.失败类型 for item in guard_items if item.失败类型])
        l100.失败位置.extend([e for item in guard_items for e in item.证据])
        l100.是否进入L15 = "是"
        l100.调用方向.extend([item.候选模块 for item in guard_items if item.候选模块])
        if any(item.严重级别 == "error" for item in guard_items):
            l100.判断结果 = "SCREENING_REJECT"
        else:
            l100.判断结果 = "HUMAN_REVIEW_REQUIRED"
        l100.最终状态 = l100.判断结果
    gates = [l100, *gates]
    failure_packet = 生成失败包(gates)
    routes = 生成路由建议(failure_packet)
    has_error = any(item.严重级别 == "error" for item in failure_packet)
    has_warning = any(item.严重级别 == "warning" for item in failure_packet)
    if has_error:
        status = 机器初筛退回
        exit_code = ExitCode.GATE_REJECTED
    elif has_warning:
        status = 需要人工复核
        exit_code = ExitCode.REVIEW_REQUIRED
    else:
        status = 机器初筛通过
        exit_code = ExitCode.OK

    result = 正文检测结果(
        run_id=run_id,
        项目=args.project,
        章节路径=str(chapter_path),
        章节标题=title,
        当前字数=word_count,
        段落数=len(paragraphs),
        方法声明="自动检测只做未验证的启发式风险筛查：按 L1/L1.5/L2 Markdown 标准提取可证据化的正文风险；不能冒充最终文学判断、读者投入判断或发布授权。",
        闸门结果=gates,
        失败包=failure_packet,
        路由建议=routes,
        pipeline_run_id=pipeline_run_id,
        stage_run_id=stage_run_id or f"{pipeline_run_id}-L1" if pipeline_run_id else run_id,
        status=status,
        状态说明=状态说明[status],
    )

    try:
        md_path, json_path, packet_path = 写报告(result, out_dir)
    except 工程错误 as exc:
        打印错误信封(exc, stage="L1", run_id=run_id, path=out_dir)
        return int(exc.exit_code)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "chapter": str(chapter_path),
                "word_count": word_count,
                "paragraphs": len(paragraphs),
                "report_md": str(md_path),
                "report_json": str(json_path),
                "failure_packet": str(packet_path),
                "gate_results": {gate.闸门: gate.判断结果 for gate in gates},
                "failure_count": len(failure_packet),
                "status": status,
                "heuristic": result.heuristic,
                "publish_authority": result.publish_authority,
                "human_review_required": result.human_review_required,
                "validation_status": result.validation_status,
                "exit_code": int(exit_code),
                "standard_mode": args.standard_mode,
                "experimental_standard": args.standard_mode == 候选试验模式,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return int(exit_code)


if __name__ == "__main__":
    raise SystemExit(main())
