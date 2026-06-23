from __future__ import annotations

import json
from pathlib import Path

from 正文检测模型 import 正文检测结果


def 写报告(result: 正文检测结果, out_dir: Path) -> tuple[Path, Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{result.run_id}.json"
    md_path = out_dir / f"{result.run_id}.md"
    packet_path = out_dir / f"{result.run_id}_failure_packet.json"

    json_path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    packet_path.write_text(
        json.dumps([item.__dict__ | {"证据": [e.__dict__ for e in item.证据]} for item in result.失败包], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        f"# 正文检测报告 {result.run_id}",
        "",
        f"- 项目：{result.项目}",
        f"- 章节：{result.章节标题}",
        f"- 正文路径：`{result.章节路径}`",
        f"- 当前字数：{result.当前字数}",
        f"- 段落数：{result.段落数}",
        f"- 方法声明：{result.方法声明}",
        "",
        "## 闸门结论",
    ]

    for gate in result.闸门结果:
        lines.extend(
            [
                "",
                f"### {gate.闸门}",
                f"- 判断结果：{gate.判断结果}",
                f"- 失败类型：{('、'.join(gate.失败类型) if gate.失败类型 else '无硬失败；见检测项风险')}",
                f"- 是否进入 L1.5：{gate.是否进入L15}",
                f"- 调用方向：{('、'.join(gate.调用方向) if gate.调用方向 else '无')}",
                f"- 回流验收位置：{gate.回流验收位置}",
                "",
                "| 检测项 | 状态 | 级别 | 说明 | 证据 |",
                "|---|---|---|---|---|",
            ]
        )
        for item in gate.检测项:
            ev = "<br>".join(f"P{e.段落}：{e.摘句}" for e in item.证据) or "无"
            lines.append(f"| {item.名称} | {item.状态} | {item.严重级别} | {item.说明} | {ev} |")

    lines.extend(["", "## 失败包"])
    if not result.失败包:
        lines.append("无。")
    else:
        for idx, item in enumerate(result.失败包, start=1):
            evidence = "；".join(f"P{e.段落}：{e.摘句}" for e in item.证据) or "无"
            lines.extend(
                [
                    "",
                    f"### FP-{idx:03d} {item.失败类型 or item.名称}",
                    f"- 来源闸门：{item.闸门}",
                    f"- 失败位置：{evidence}",
                    f"- 影响：{item.说明}",
                    f"- 候选模块：{item.候选模块 or '回L1.5/人工复核'}",
                    f"- 修复方向：{item.修复方向 or '人工复核'}",
                    f"- 回流验收位置：{item.回流验收位置 or item.闸门}",
                ]
            )

    lines.extend(["", "## 路由建议"])
    for route in result.路由建议:
        lines.extend(
            [
                "",
                f"### {route['路由编号']}",
                f"- 来源闸门：{route['来源闸门']}",
                f"- 主失败类型：{route['主失败类型']}",
                f"- 失败位置：{route['失败位置']}",
                f"- 建议修复方向：{route['建议修复方向']}",
                f"- 接口候选模块：{route['接口候选模块']}",
                f"- 回流验收位置：{route['回流验收位置']}",
                f"- 最终状态：{route['最终状态']}",
            ]
        )

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md_path, json_path, packet_path
