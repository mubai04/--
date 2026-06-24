#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True

公共组件 = Path(__file__).resolve().parents[1] / "公共组件"
if str(公共组件) not in sys.path:
    sys.path.insert(0, str(公共组件))

from L3补丁执行器 import 执行补丁, _resolve_io_path
from 协议规则加载 import L3协议规则路径, 加载协议规则
from 生产资格 import 判定结果转标准字段, 要求生产资格
from 标准加载器 import 候选试验模式, 生产模式
from 退出码 import ExitCode
from 工程异常 import 工程错误
from 安全路径 import safe_id
from 错误信封 import 打印错误信封


ROOT = Path(__file__).resolve().parents[3]


def main() -> int:
    parser = argparse.ArgumentParser(description="XC-UE B2：审批保护的确定性文本补丁执行器。")
    parser.add_argument("--l2-report", default=None, help="包含 L2-01 确定性候选策略的 L2 报告。")
    parser.add_argument("--audit-json", default=None, help="READY_FOR_ACCEPTANCE 审计文件；用于正式采纳阶段。")
    parser.add_argument("--approval", default=None, help="审批记录 JSON；plan-only 时可省略。")
    parser.add_argument("--plan-only", action="store_true", help="只生成补丁计划和待审批审计，不执行补丁。")
    parser.add_argument("--final-decision", default=None, choices=["apply", "reject"], help="READY_FOR_ACCEPTANCE 后的人工最终决定。")
    parser.add_argument("--decision-reason", default="", help="最终决定理由。")
    parser.add_argument("--run-id", default=None, help="运行编号。")
    parser.add_argument("--out-dir", default=None, help="输出目录。")
    parser.add_argument("--standard-mode", default=候选试验模式, choices=[生产模式, 候选试验模式])
    parser.add_argument("--protocol-rules", default=None, help="L3 结构化协议规则 JSON。")
    args = parser.parse_args()

    try:
        run_id = safe_id(args.run_id or "L3_PATCH-" + datetime.now().strftime("%Y%m%d-%H%M%S"), "run_id")
        l2_report = _resolve_io_path(args.l2_report) if args.l2_report else None
        audit_json = _resolve_io_path(args.audit_json) if args.audit_json else None
        out_dir = _resolve_io_path(args.out_dir) if args.out_dir else ROOT / "运行记录" / run_id / "第三层补丁"
        approval = _resolve_io_path(args.approval) if args.approval else None
        rules_path = Path(args.protocol_rules) if args.protocol_rules else L3协议规则路径(ROOT)
        if not rules_path.is_absolute():
            rules_path = (ROOT / rules_path).resolve()
        mode_decision = 要求生产资格(
            requested_mode=args.standard_mode,
            rule_source=rules_path,
            entrypoint="L3_PATCH",
            project_identity="TP-001",
        )
        rules = 加载协议规则(rules_path)
        payload = 执行补丁(
            l2_report=l2_report,
            audit_json=audit_json,
            out_dir=out_dir,
            run_id=run_id,
            approval_path=approval,
            plan_only=args.plan_only,
            final_decision=args.final_decision,
            decision_reason=args.decision_reason,
            protocol_rules=rules,
        )
        print(
            json.dumps(
                {
                    "run_id": run_id,
                    "status": payload.get("final_status", payload["status"]),
                    "audit_json": str(out_dir / "补丁审计.json"),
                    "plan_json": str(out_dir / "补丁计划.json") if (out_dir / "补丁计划.json").exists() else "",
                    "protocol_rule_version": rules.规则版本,
                    "protocol_rule_hash": rules.规则哈希,
                    **判定结果转标准字段(mode_decision),
                    "exit_code": int(ExitCode.OK),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return int(ExitCode.OK)
    except 工程错误 as exc:
        打印错误信封(
            exc,
            stage="L3_PATCH",
            run_id=locals().get("run_id", ""),
            path=locals().get("out_dir", ""),
            details=getattr(exc, "details", {}),
        )
        return int(exc.exit_code)


if __name__ == "__main__":
    raise SystemExit(main())
