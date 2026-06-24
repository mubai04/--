from __future__ import annotations

import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from conftest import ROOT
from 退出码 import ExitCode


pytestmark = [pytest.mark.integration, pytest.mark.adversarial]


def _写L1章节(path: Path, paragraphs: list[str], title: str = "批次05对抗样本") -> None:
    path.write_text("#" + title + "\n\n" + "\n\n".join(paragraphs) + "\n", encoding="utf-8")


def _运行L1(chapter: Path, out_dir: Path, env: dict[str, str], rules_path: Path | None = None) -> tuple[subprocess.CompletedProcess[str], dict | None]:
    run_id = "pytest-L1-" + uuid.uuid4().hex[:8]
    cmd = [
        sys.executable,
        str(ROOT / "00_工程总控" / "工程执行层" / "L1工程" / "L1运行入口.py"),
        "--chapter",
        str(chapter),
        "--run-id",
        run_id,
        "--out-dir",
        str(out_dir),
        "--project",
        "pytest",
        "--standard-mode",
        "CANDIDATE_TEST",
    ]
    if rules_path:
        cmd.extend(["--gate-rules", str(rules_path)])
    result = subprocess.run(
        cmd,
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        env=env,
        timeout=30,
    )
    report_path = out_dir / f"{run_id}.json"
    if not report_path.exists():
        return result, None
    return result, json.loads(report_path.read_text(encoding="utf-8"))


def _复制L1闸门规则(root_case: Path) -> Path:
    source = ROOT / "00_工程总控" / "工程执行层" / "L1工程" / "gate_rules.json"
    target = root_case / "gate_rules.json"
    shutil.copyfile(source, target)
    return target


def _随机中文段落(count: int) -> list[str]:
    base = "春川晚镜素岚青石远灯旧纸新茶薄雨空庭微响南窗北巷白墙小桥"
    return ["".join(base[(i + j) % len(base)] for j in range(42 + (i % 5))) + "。" for i in range(count)]


def _关键词堆砌段落(count: int) -> list[str]:
    words = "死 血 杀 追 逃 塌 碎 规则 代价 选择 决定 不能 必须 真相 秘密 下一 门后 第一次 最后"
    return [words + "。" + words.replace(" ", "，") + "。" for _ in range(count)]


def _无因果段落(count: int) -> list[str]:
    pool = [
        "屋里有一张桌子，桌上放着杯子，杯中有水，窗外有光。",
        "街边的人走得很慢，店铺开着门，招牌挂在原处。",
        "他看见墙上的影子，又看见地上的鞋印，随后坐下。",
        "房间保持整洁，账本摆在左边，钥匙放在右边。",
    ]
    return [pool[i % len(pool)] for i in range(count)]


def _完整但乏味段落(count: int) -> list[str]:
    pool = [
        "早上七点，陈立起床，洗漱，吃饭，然后乘车去库房。",
        "他按照表格核对箱号，把数量写在记录本上，再把门关好。",
        "中午他吃了面，下午继续整理纸箱，傍晚把钥匙交给同事。",
        "这一天没有争执，没有变化，也没有新的困难需要处理。",
    ]
    return [pool[i % len(pool)] for i in range(count)]


def _高质量少目标词段落() -> list[str]:
    return [
        "雨停在黄昏前。林照把母亲留下的木匣放进怀里，沿着河堤往渡口走。",
        "船夫认得他，却没有像往常那样招呼，只把竹篙横在岸边，示意他先看水面。",
        "水里浮着一串红绳，每一截都系着小小的铜片，正顺流撞向石阶。",
        "林照蹲下去，发现铜片背面刻着母亲的笔迹，字很浅，像是匆忙划出来的。",
        "他没有喊人。镇上的更夫刚从桥头经过，腰间那串铃比平日少了一枚。",
        "木匣在怀里轻轻发热，他想起母亲临走前说过，若匣子发热，就去找不会说话的人。",
        "渡口唯一不会说话的人，是修船棚里的哑伯。可哑伯昨天已经被送去山后的义庄。",
        "林照把铜片收起，绕开人群，沿着废船背后的泥路走。每一步都在湿土上留下深印。",
        "修船棚的门半开着，里面没有灯，只有一只新编的草鞋摆在桌下。",
        "他认出那是母亲常穿的样式，鞋底却干净得像刚从手里放下。",
        "门后传来木头轻响。林照屏住呼吸，把木匣推到桌面中央。",
        "匣盖自己弹开，里面没有遗物，只有一枚少掉舌片的铜铃。",
        "桥头更夫的铃声又响了一遍。这一次，声音从修船棚地下传出来。",
        "林照弯下腰，听见有人在木板下面敲了三下，像是在回答他一路带来的问题。",
    ]


def _断言L1降级字段(report: dict) -> None:
    assert report["heuristic"] is True
    assert report["publish_authority"] is False
    assert report["human_review_required"] is True
    assert report["validation_status"] == "UNVALIDATED"
    assert report["rule_version"]
    assert report["signal_strength"]
    assert report["confidence"]
    assert report["known_limitations"]
    assert report["human_review_reasons"]
    assert report["forbidden_extrapolations"]


def 测试L1对抗样本随机和关键词堆砌不产生正向总判定(root_case, test_io_env):
    forbidden = {"SCREENING_PASS", "READY", "PUBLISHABLE"}
    for label, factory in [("random", _随机中文段落), ("stuffing", _关键词堆砌段落)]:
        for count in [8, 24, 48]:
            chapter = root_case / f"{label}-{count}.md"
            out_dir = root_case / f"l1-{label}-{count}"
            _写L1章节(chapter, factory(count), f"{label}-{count}")
            _, report = _运行L1(chapter, out_dir, test_io_env)
            _断言L1降级字段(report)
            assert report["status"] not in forbidden
            assert all(gate["判断结果"] not in forbidden for gate in report["闸门结果"])


def 测试L1关键词密度增加不提升权限或跳过人工复核(root_case, test_io_env):
    base = root_case / "boring.md"
    stuffed = root_case / "boring-stuffed.md"
    _写L1章节(base, _完整但乏味段落(28), "完整但乏味")
    _写L1章节(stuffed, _完整但乏味段落(28) + _关键词堆砌段落(8), "完整但乏味加关键词")
    _, base_report = _运行L1(base, root_case / "l1-base", test_io_env)
    _, stuffed_report = _运行L1(stuffed, root_case / "l1-stuffed", test_io_env)
    for report in [base_report, stuffed_report]:
        _断言L1降级字段(report)
    assert stuffed_report["publish_authority"] is False
    assert stuffed_report["human_review_required"] is True
    assert stuffed_report["status"] != "SCREENING_PASS"


def 测试L1无因果和信息完整但乏味仍需复核或退回(root_case, test_io_env):
    for label, paragraphs in [
        ("no-causality", _无因果段落(30)),
        ("complete-boring", _完整但乏味段落(30)),
    ]:
        chapter = root_case / f"{label}.md"
        _写L1章节(chapter, paragraphs, label)
        _, report = _运行L1(chapter, root_case / f"l1-{label}", test_io_env)
        _断言L1降级字段(report)
        assert report["status"] in {"SCREENING_REJECT", "REVIEW_REQUIRED"}


def 测试L1高质量少目标词不因单一词表缺失硬退回(root_case, test_io_env):
    chapter = root_case / "high-quality-low-keyword.md"
    _写L1章节(chapter, _高质量少目标词段落(), "少目标词样本")
    _, report = _运行L1(chapter, root_case / "l1-high-quality-low-keyword", test_io_env)
    _断言L1降级字段(report)
    hard_failures = [item for item in report["失败包"] if item["严重级别"] == "error"]
    assert not hard_failures or any(item["失败类型"] != "创意设定失败" for item in hard_failures)


def 测试A3L1结构化规则改动会改变发布锁字数判定(root_case, test_io_env):
    chapter = root_case / "chapter.md"
    out_dir = root_case / "l1-structured"
    rules_path = _复制L1闸门规则(root_case)
    payload = json.loads(rules_path.read_text(encoding="utf-8"))
    payload["gates"]["L1-03"]["word_count"]["function_floor"] = 9999
    payload["gates"]["L1-03"]["word_count"]["lower"] = 10000
    payload["gates"]["L1-03"]["word_count"]["upper"] = 12000
    rules_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _写L1章节(chapter, _关键词堆砌段落(120), "A3-L1-结构化规则")

    result, report = _运行L1(chapter, out_dir, test_io_env, rules_path)

    assert result.returncode in {int(ExitCode.GATE_REJECTED), int(ExitCode.REVIEW_REQUIRED)}, result.stderr
    assert report is not None
    l103 = next(gate for gate in report["闸门结果"] if gate["闸门"] == "L1-03")
    assert l103["规则摘要"]["功能稿下限"] == 9999
    assert any(item["失败类型"] == "字数不足" for item in l103["检测项"])
    assert report["rule_version"] == payload["version"]
    assert len(report["rule_hash"]) == 64


def 测试A3L1Markdown闸门标准改动不改变L1运行行为(root_case, test_io_env):
    chapter = root_case / "chapter.md"
    rules_path = _复制L1闸门规则(root_case)
    _写L1章节(chapter, _关键词堆砌段落(80), "A3-L1-Markdown")

    first, first_report = _运行L1(chapter, root_case / "A", test_io_env, rules_path)
    assert first_report is not None, first.stderr

    markdown_source = ROOT / "20_L1_闸门层" / "L1-03_发布锁验收工程图.md"
    before = markdown_source.read_text(encoding="utf-8")
    try:
        markdown_source.write_text(before + "\n\n<!-- A3-L1 pytest markdown mutation should not affect runtime rules -->\n", encoding="utf-8")
        second, second_report = _运行L1(chapter, root_case / "B", test_io_env, rules_path)
    finally:
        markdown_source.write_text(before, encoding="utf-8")

    assert second_report is not None, second.stderr
    assert first_report["闸门结果"] == second_report["闸门结果"]


def 测试A3L1坏结构化规则在写报告前失败(root_case, test_io_env):
    chapter = root_case / "chapter.md"
    out_dir = root_case / "bad-rules"
    bad_rules = root_case / "bad_gate_rules.json"
    bad_rules.write_text('{"schema_version":"xcue.l1-gate-rules/1.0","gates":{}}', encoding="utf-8")
    _写L1章节(chapter, _关键词堆砌段落(20), "A3-L1-bad")

    result, report = _运行L1(chapter, out_dir, test_io_env, bad_rules)

    assert result.returncode == int(ExitCode.RULE_PARSE_FAILED)
    payload = json.loads(result.stderr)
    assert payload["error_code"] == "RULE_PARSE_FAILED"
    assert report is None
    assert not list(out_dir.glob("*.json"))
