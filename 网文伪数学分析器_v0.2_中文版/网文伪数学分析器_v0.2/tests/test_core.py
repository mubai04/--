import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "src" / "novel_pseudo_math.py"
spec = importlib.util.spec_from_file_location("npm", SCRIPT)
npm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(npm)


def make_valid_payload(tmp_path: Path):
    owners = list(npm.GATES) + list(npm.PROFILE) + [
        "Ca_causal","Cg_goal","Cs_state","Ve_salience","Vu_reframe","Vb_branch","Vr_rhythm",
        "ES_same","EI_lowvar","ER_repeat","EA_mismatch","Sh_syntax","Lv_voice","Li_sensory",
        "Lm_layers","Lr_rhythm","Lp_pov","Lo_original","H_long","H_voice","H_asym"
    ]
    sentences = [f"第{i:02d}条证据展示人物行动、因果后果与状态变化，内容足够完整。" for i in range(1, len(owners)+1)]
    text = "\n".join(sentences) + "\n" + ("补充正文用于满足最小篇幅与连续性检查。" * 20)
    file = "0001_测试章.md"
    positions = {}
    cursor = 0
    for owner, sentence in zip(owners, sentences):
        start = text.index(sentence, cursor)
        end = start + len(sentence)
        positions[owner] = {"file": file, "quote": sentence, "start": start, "end": end}
        cursor = end
    source_sha = npm.sha256_text(text)
    task = {
        "task_id": "WORK-001-single-test",
        "method_version": npm.VERSION,
        "calibration_level": "C0",
        "work_id": "WORK-001",
        "title": "测试作品",
        "scope_type": "single",
        "chapters": ["0001"],
        "source_files": [{"file": file, "sha256": source_sha, "chars": len(text)}],
        "documents": [{"file": file, "sha256": source_sha, "chars": len(text), "text": text}],
        "source_sha256": source_sha,
        "text_char_count": len(text),
        "truncated": False,
        "text": text,
    }
    ext = {
        "task_id": task["task_id"],
        "source_sha256": source_sha,
        "gates": {k: {"status": "PASS", "evidence": [positions[k]], "judgment": "成立"} for k in npm.GATES},
        "chapter_profile": {k: {"status": "OK", "value": 3.0, "evidence": [positions[k]], "judgment": "成立"} for k in npm.PROFILE},
        "facts": {},
        "manual_scores": {},
        "findings": [],
        "anti_gaming": {k: {"status": "PASS", "evidence": [], "judgment": "未发现刷分行为"} for k in npm.ANTI_GAMING_CODES},
        "context": {"rater_disagreement": 0.0, "baseline_missing": 1, "mixed_edit": 0},
    }
    for key in json.loads(npm.REGISTRY_PATH.read_text(encoding="utf-8"))["manual_scores"]:
        ext["manual_scores"][key] = {"status": "OK", "value": 2.5, "evidence": [positions[key]], "judgment": "成立"}
    task_path = tmp_path / "task.json"
    ext_path = tmp_path / "extraction.json"
    task_path.write_text(json.dumps(task, ensure_ascii=False), encoding="utf-8")
    ext_path.write_text(json.dumps(ext, ensure_ascii=False), encoding="utf-8")
    return task, ext, task_path, ext_path


def test_q_strict():
    assert npm.q_ratio(0.25) == 1.0
    with pytest.raises(npm.AnalyzerError):
        npm.q_ratio(-0.01)
    with pytest.raises(npm.AnalyzerError):
        npm.q_ratio(1.01)


def test_n():
    assert npm.n_map(5, 0, 10) == 2
    with pytest.raises(npm.AnalyzerError):
        npm.n_map(5, 2, 2)


def test_wa_na():
    assert npm.wa_interval([(0, 0), None, (4, 4)], [1, 1, 1]) == (2, 2)


def test_risk_thresholds_have_no_gaps():
    th = npm.read_json(npm.THRESHOLDS_PATH)
    assert npm.risk_action(0.95, th)["status"] == "PASS"
    assert npm.risk_action(1.95, th)["status"] == "OBSERVE"
    assert npm.risk_action(2.95, th)["status"] == "TARGETED_REPAIR"
    assert npm.risk_action(4.0, th)["status"] == "REWRITE"


def test_runtime_schema_rejects_extra_field(tmp_path):
    task, ext, task_path, ext_path = make_valid_payload(tmp_path)
    ext["unexpected"] = 1
    ext_path.write_text(json.dumps(ext, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(npm.AnalyzerError, match="Schema"):
        npm.score_task(task_path, ext_path, tmp_path / "out")


def test_negative_fact_rejected(tmp_path):
    task, ext, task_path, ext_path = make_valid_payload(tmp_path)
    ev = deepcopy(ext["gates"]["G_C"]["evidence"])
    ext["facts"]["N-01"] = {
        "status": "OK", "numerator": -1, "denominator": 5, "sample_size": 5,
        "evidence": ev, "judgment": "非法负数"
    }
    ext_path.write_text(json.dumps(ext, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(npm.AnalyzerError):
        npm.score_task(task_path, ext_path, tmp_path / "out")


def test_fake_evidence_file_rejected(tmp_path):
    task, ext, task_path, ext_path = make_valid_payload(tmp_path)
    ext["gates"]["G_C"]["evidence"][0]["file"] = "不存在.md"
    ext_path.write_text(json.dumps(ext, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(npm.AnalyzerError, match="证据文件不存在"):
        npm.score_task(task_path, ext_path, tmp_path / "out")


def test_short_text_cannot_pass_gates(tmp_path):
    task, ext, task_path, ext_path = make_valid_payload(tmp_path)
    short = "人物做出选择并承担后果。"
    task["documents"][0]["text"] = short
    task["documents"][0]["chars"] = len(short)
    task["documents"][0]["sha256"] = npm.sha256_text(short)
    task["source_files"][0]["chars"] = len(short)
    task["source_files"][0]["sha256"] = npm.sha256_text(short)
    task["text"] = short
    task["text_char_count"] = len(short)
    task["source_sha256"] = npm.sha256_text(short)
    ext["source_sha256"] = task["source_sha256"]
    for code in npm.GATES:
        ext["gates"][code]["evidence"] = [{"file":"0001_测试章.md","quote":short,"start":0,"end":len(short)}]
    task_path.write_text(json.dumps(task, ensure_ascii=False), encoding="utf-8")
    ext_path.write_text(json.dumps(ext, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(npm.AnalyzerError, match="不得判 PASS"):
        npm.score_task(task_path, ext_path, tmp_path / "out")


def test_evidence_reuse_limit(tmp_path):
    task, ext, task_path, ext_path = make_valid_payload(tmp_path)
    same = deepcopy(ext["gates"]["G_C"]["evidence"][0])
    for code in npm.GATES:
        ext["gates"][code]["evidence"] = [deepcopy(same)]
    ext_path.write_text(json.dumps(ext, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(npm.AnalyzerError, match="复用"):
        npm.score_task(task_path, ext_path, tmp_path / "out")


def test_score_outputs_decision_and_stability(tmp_path):
    task, ext, task_path, ext_path = make_valid_payload(tmp_path)
    result = npm.score_task(task_path, ext_path, tmp_path / "out")
    assert result["decision"]["state"] in {"TARGETED_REPAIR", "ROBUST_PASS", "NEEDS_REVIEW"}
    assert (tmp_path / "out" / "analysis.json").exists()
    assert "R_narrative" in result["risk_vector"]


def test_path_traversal_rejected():
    for bad in ("../evil", "..", "a/b", "a\\b", ".hidden"):
        with pytest.raises(npm.AnalyzerError):
            npm.safe_work_id(bad)


def test_compare_requires_different_hash_and_same_scope(tmp_path):
    before = {
        "project":"网文伪数学分析器","version":npm.VERSION,
        "task":{"work_id":"W","scope_type":"single","chapters":["0001"],"source_sha256":"a"*64},
        "decision":{"state":"TARGETED_REPAIR"},
        "risk_vector":{"R_narrative":{"center":2.5}},
        "chapter_profile":{"dimensions":{k:[2,2] for k in npm.PROFILE}}
    }
    after = deepcopy(before)
    after["task"]["source_sha256"] = "b"*64
    after["decision"]["state"] = "ROBUST_PASS"
    after["risk_vector"]["R_narrative"]["center"] = 1.5
    after["chapter_profile"]["dimensions"]["U_ch"] = [3,3]
    b=tmp_path/'b.json'; a=tmp_path/'a.json'; o=tmp_path/'compare.json'
    b.write_text(json.dumps(before),encoding='utf-8'); a.write_text(json.dumps(after),encoding='utf-8')
    args=type('A',(),{'before':str(b),'after':str(a),'output':str(o)})()
    npm.cmd_compare(args)
    data=json.loads(o.read_text(encoding='utf-8'))
    assert data['risk_delta']['R_narrative'] == -1.0
    assert data['chapter_profile_delta']['U_ch'] == 1.0


def test_batch_failure_propagates(tmp_path):
    tasks = tmp_path / "tasks" / "bad"
    tasks.mkdir(parents=True)
    (tasks / "task.json").write_text("{}", encoding="utf-8")
    args=type('A',(),{'tasks_dir':str(tmp_path/'tasks'),'output_dir':str(tmp_path/'batch_out')})()
    with pytest.raises(npm.AnalyzerError, match="失败任务"):
        npm.cmd_batch_score(args)

def test_numerator_cannot_exceed_denominator(tmp_path):
    task, ext, task_path, ext_path = make_valid_payload(tmp_path)
    ev = deepcopy(ext["gates"]["G_C"]["evidence"])
    ext["facts"]["N-01"] = {
        "status": "OK", "numerator": 6, "denominator": 5, "sample_size": 5,
        "evidence": ev, "judgment": "非法比例"
    }
    ext_path.write_text(json.dumps(ext, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(npm.AnalyzerError, match="不得大于"):
        npm.score_task(task_path, ext_path, tmp_path / "out")


def test_state_machine_core_paths():
    profile = {k: (3.0, 3.2) for k in npm.PROFILE}
    risks = {"R": {"center": 1.0}}
    anti = {k: {"status": "PASS"} for k in npm.ANTI_GAMING_CODES}
    assert npm.derive_decision_state("PASSED", profile, (3.0, 3.2), risks, anti)[0] == "ROBUST_PASS"
    risks["R"]["center"] = 3.1
    assert npm.derive_decision_state("PASSED", profile, (3.0, 3.2), risks, anti)[0] == "REWRITE"
    assert npm.derive_decision_state("BLOCKED", profile, (3.0, 3.2), risks, anti)[0] == "BLOCKED"
    assert npm.derive_decision_state("NEEDS_REVIEW", profile, (3.0, 3.2), risks, anti)[0] == "NEEDS_REVIEW"


def test_anti_gaming_fail_prevents_robust_pass():
    profile = {k: (3.0, 3.2) for k in npm.PROFILE}
    risks = {"R": {"center": 1.0}}
    anti = {k: {"status": "PASS"} for k in npm.ANTI_GAMING_CODES}
    anti["AG_SYMBOL_SPAM"] = {"status": "FAIL"}
    assert npm.derive_decision_state("PASSED", profile, (3.0, 3.2), risks, anti)[0] == "TARGETED_REPAIR"


def test_stability_is_deterministic():
    th = npm.read_json(npm.THRESHOLDS_PATH)
    values = [(1.0, 1.0), (2.0, 2.0), (3.0, 3.0)]
    a = npm.module_stability(values, [0.4, 0.3, 0.3], th, 50, 0.2, 42)
    b = npm.module_stability(values, [0.4, 0.3, 0.3], th, 50, 0.2, 42)
    assert a == b
    assert 0 <= a["stability"] <= 1
