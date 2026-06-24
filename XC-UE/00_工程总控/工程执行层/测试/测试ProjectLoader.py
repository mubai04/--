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
from 项目加载器 import 加载项目


pytestmark = pytest.mark.integration


ENTRY = ROOT / "00_工程总控" / "工程执行层" / "统一运行入口.py"
CHAPTER = ROOT / "70_测试项目" / "TP-001_CleanHarness_IR_Runtime" / "chapters" / "ch01.md"
L3_ENTRY = ROOT / "00_工程总控" / "工程执行层" / "L3工程" / "L3运行入口.py"
L1_ENTRY = ROOT / "00_工程总控" / "工程执行层" / "L1工程" / "L1运行入口.py"
PROJECT_ERROR = 27


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ENTRY), *args],
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=30,
    )


def _registry(path: Path, *, default_project: str = "TP-001", projects: dict | None = None) -> Path:
    payload = {
        "schema_version": "xcue.project-registry/1.0",
        "default_project": default_project,
        "projects": projects
        if projects is not None
        else {
            "TP-001": {
                "project_root": "70_测试项目/TP-001_CleanHarness_IR_Runtime",
            }
        },
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _write_project(
    root: Path,
    project_id: str,
    *,
    manifest_project_id: str | None = None,
    chapter: str = "# 测试项目\n\n入口、正文、项目身份必须一致。\n",
    entrypoint: bool = True,
    content_root: str = "chapters",
    default_chapter: str = "chapters/ch01.md",
    entrypoint_path: str = "runtime/project_entry.py",
) -> Path:
    (root / "IR").mkdir(parents=True, exist_ok=True)
    (root / "chapters").mkdir(parents=True, exist_ok=True)
    (root / "logs").mkdir(parents=True, exist_ok=True)
    (root / "runtime").mkdir(parents=True, exist_ok=True)
    if chapter is not None:
        (root / default_chapter).parent.mkdir(parents=True, exist_ok=True)
        (root / default_chapter).write_text(chapter, encoding="utf-8")
    if entrypoint:
        entry = root / entrypoint_path
        entry.parent.mkdir(parents=True, exist_ok=True)
        entry.write_text(
            "from __future__ import annotations\n"
            "import argparse, json\n"
            "from pathlib import Path\n"
            "parser = argparse.ArgumentParser()\n"
            "parser.add_argument('--run-id', default='run')\n"
            "args, extra = parser.parse_known_args()\n"
            "marker = Path('reports') / f'{args.run_id}.json'\n"
            "marker.parent.mkdir(exist_ok=True)\n"
            f"payload = {{'project_id': '{project_id}', 'entrypoint': 'project', 'extra': extra}}\n"
            "marker.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')\n"
            "print(json.dumps(payload, ensure_ascii=False))\n",
            encoding="utf-8",
        )
    manifest = {
        "schema_version": "xcue.project-manifest/1.0",
        "project_id": manifest_project_id or project_id,
        "content_root": content_root,
        "default_chapter": default_chapter,
        "entrypoint": entrypoint_path,
        "entrypoint_type": "project",
        "required_dirs": ["IR", "chapters", "logs"],
    }
    (root / "project.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return root


def _stderr_payload(result: subprocess.CompletedProcess[str]) -> dict:
    return json.loads(result.stderr)


def _assert_project_error(result: subprocess.CompletedProcess[str], code: str) -> dict:
    assert result.returncode == PROJECT_ERROR, result.stdout + result.stderr
    payload = _stderr_payload(result)
    assert payload["error_code"] == code
    assert payload["reason"] == code
    return payload


def _write_l2_report(path: Path) -> None:
    payload = {
        "schema_version": "xcue.l2-report/1.0",
        "pipeline_run_id": "pytest-loader",
        "stage_run_id": "pytest-loader-L2",
        "status": "COMPLETED",
        "run_id": "pytest-loader-L2",
        "输入文件": str(path.parent / "失败包.json"),
        "输入数量": 1,
        "方法声明": "pytest",
        "标准校验问题": [],
        "回流校验问题": [],
        "接口判断": [],
        "修复单": [
            {
                "修复单类型": "L2 能力修复单",
                "来源闸门": "L1-02",
                "接收模块": "L2-05",
                "输入问题": "入口弱",
                "主失败类型": "入口弱",
                "次失败类型": "",
                "修复动作": "规划修复动作",
                "修复产物": "任务包",
                "验收问题": "回到 L1-02 复验",
                "回流位置": "L1-02",
                "是否需要其他L2辅助": "否",
                "是否需要回L15重路由": "否",
                "最终状态": "回原闸门复验",
                "rule_id": "L2-05:pytest-rule",
                "rule_version": "pytest",
                "rule_hash": "a" * 64,
            }
        ],
        "阻断项": [],
        "复验目标": [],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def 测试默认项目和显式TP001流水线输入无效行为一致且不创建运行记录():
    default_run = "pytest-loader-default-" + uuid.uuid4().hex[:8]
    explicit_run = "pytest-loader-explicit-" + uuid.uuid4().hex[:8]
    base = [
        "--target",
        "PIPELINE",
        "--chapter",
        str(CHAPTER),
        "--standard-mode",
        "PRODUCTION",
    ]
    default_result = _run([*base, "--run-id", default_run])
    explicit_result = _run([*base, "--project", "TP-001", "--run-id", explicit_run])

    assert default_result.returncode == explicit_result.returncode == int(ExitCode.PRODUCTION_MODE_NOT_ELIGIBLE)
    assert not (ROOT / "运行记录" / default_run).exists()
    assert not (ROOT / "运行记录" / explicit_run).exists()


def 测试L3未指定Harness时默认加载TP001项目(tmp_path: Path, test_io_env: dict[str, str]):
    l2_report = tmp_path / "第二层" / "修复报告.json"
    out_dir = tmp_path / "第三层"
    l2_report.parent.mkdir(parents=True)
    _write_l2_report(l2_report)
    result = subprocess.run(
        [
            sys.executable,
            str(L3_ENTRY),
            "--l2-report",
            str(l2_report),
            "--run-id",
            "pytest-loader-L3-" + uuid.uuid4().hex[:8],
            "--out-dir",
            str(out_dir),
            "--pipeline-run-id",
            "pytest-loader",
            "--stage-run-id",
            "pytest-loader-L3",
            "--standard-mode",
            "CANDIDATE_TEST",
        ],
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        env=test_io_env,
        timeout=30,
    )
    assert result.returncode == int(ExitCode.OK), result.stderr
    report = json.loads((out_dir / "任务包.json").read_text(encoding="utf-8"))
    assert report["任务单"][0]["ProjectHarness根"] == "70_测试项目/TP-001_CleanHarness_IR_Runtime"


def 测试第二项目只改注册表即可被Loader加载(tmp_path: Path):
    project_root = ROOT / "运行记录" / ("pytest-TEST-002-" + uuid.uuid4().hex[:8])
    try:
        _write_project(project_root, "TEST-002")
        registry = _registry(
            tmp_path / "projects.json",
            default_project="TEST-002",
            projects={
                "TEST-002": {
                    "project_root": project_root.relative_to(ROOT).as_posix(),
                }
            },
        )

        project = 加载项目(ROOT, "TEST-002", registry)

        assert project.project_id == "TEST-002"
        assert project.project_root == project_root.resolve()
        assert project.project_manifest == (project_root / "project.json").resolve()
        assert project.content_root == (project_root / "chapters").resolve()
        assert project.chapter_source == (project_root / "chapters" / "ch01.md").resolve()
        assert project.entrypoint == (project_root / "runtime" / "project_entry.py").resolve()
        assert project.relative_project_root.startswith("运行记录/pytest-TEST-002-")
    finally:
        if project_root.exists():
            shutil.rmtree(project_root)


def 测试A06仓库外显式项目Root可加载且不要求位于仓库内(tmp_path: Path):
    external = _write_project(tmp_path / "external-novel", "EXT-001")

    project = 加载项目(ROOT, project_root=external)

    assert project.project_id == "EXT-001"
    assert project.source_scope == "external"
    assert project.project_root == external.resolve()
    assert project.chapter_source == (external / "chapters" / "ch01.md").resolve()
    assert project.entrypoint == (external / "runtime" / "project_entry.py").resolve()


def 测试A06项目ID与Manifest不一致时报PROJECT_ID_MISMATCH(tmp_path: Path):
    project_root = _write_project(tmp_path / "bad-project", "TP-002", manifest_project_id="OTHER")
    registry = _registry(
        tmp_path / "projects.json",
        default_project="TP-002",
        projects={"TP-002": {"project_root": str(project_root)}},
    )

    with pytest.raises(Exception) as excinfo:
        加载项目(ROOT, "TP-002", registry)

    assert getattr(excinfo.value, "details", {})["reason"] == "PROJECT_ID_MISMATCH"


def 测试A06项目正文不存在时报PROJECT_CONTENT_NOT_FOUND(tmp_path: Path):
    project_root = _write_project(tmp_path / "missing-content", "TP-002", chapter=None)
    registry = _registry(
        tmp_path / "projects.json",
        default_project="TP-002",
        projects={"TP-002": {"project_root": str(project_root)}},
    )

    with pytest.raises(Exception) as excinfo:
        加载项目(ROOT, "TP-002", registry)

    assert getattr(excinfo.value, "details", {})["reason"] == "PROJECT_CONTENT_NOT_FOUND"


def 测试A06项目入口不存在时报PROJECT_ENTRYPOINT_NOT_FOUND(tmp_path: Path):
    project_root = _write_project(tmp_path / "missing-entrypoint", "TP-002", entrypoint=False)
    registry = _registry(
        tmp_path / "projects.json",
        default_project="TP-002",
        projects={"TP-002": {"project_root": str(project_root)}},
    )

    with pytest.raises(Exception) as excinfo:
        加载项目(ROOT, "TP-002", registry)

    assert getattr(excinfo.value, "details", {})["reason"] == "PROJECT_ENTRYPOINT_NOT_FOUND"


def 测试A06项目正文越界时报PROJECT_PATH_OUT_OF_SCOPE(tmp_path: Path):
    outside = tmp_path / "outside.md"
    outside.write_text("# 越界正文\n", encoding="utf-8")
    project_root = _write_project(tmp_path / "escape-content", "TP-002", default_chapter="../outside.md")
    registry = _registry(
        tmp_path / "projects.json",
        default_project="TP-002",
        projects={"TP-002": {"project_root": str(project_root)}},
    )

    with pytest.raises(Exception) as excinfo:
        加载项目(ROOT, "TP-002", registry)

    assert getattr(excinfo.value, "details", {})["reason"] == "PROJECT_PATH_OUT_OF_SCOPE"


def 测试A06显式项目不存在返回PROJECT_RESOLUTION_FAILED且不回退TP001():
    run_id = "pytest-a06-missing-" + uuid.uuid4().hex[:8]
    result = _run(
        [
            "--target",
            "PIPELINE",
            "--project",
            "DOES-NOT-EXIST",
            "--run-id",
            run_id,
        ]
    )

    _assert_project_error(result, "PROJECT_RESOLUTION_FAILED")
    assert not (ROOT / "运行记录" / run_id).exists()


def 测试A06项目TP002但章节指向TP001时执行前阻断(tmp_path: Path):
    project_root = _write_project(ROOT / "运行记录" / ("pytest-TP002-" + uuid.uuid4().hex[:8]), "TP-002")
    registry = _registry(
        tmp_path / "projects.json",
        default_project="TP-002",
        projects={"TP-002": {"project_root": project_root.relative_to(ROOT).as_posix()}},
    )
    run_id = "pytest-a06-mixed-" + uuid.uuid4().hex[:8]
    try:
        result = _run(
            [
                "--target",
                "PIPELINE",
                "--project",
                "TP-002",
                "--project-registry",
                str(registry),
                "--chapter",
                str(CHAPTER),
                "--run-id",
                run_id,
            ]
        )

        _assert_project_error(result, "PROJECT_PATH_OUT_OF_SCOPE")
        assert not (ROOT / "运行记录" / run_id).exists()
    finally:
        if project_root.exists():
            shutil.rmtree(project_root)


def 测试A06统一项目入口调用当前项目入口而不是TP001(tmp_path: Path):
    project_root = _write_project(ROOT / "运行记录" / ("pytest-TP002-entry-" + uuid.uuid4().hex[:8]), "TP-002")
    registry = _registry(
        tmp_path / "projects.json",
        default_project="TP-002",
        projects={"TP-002": {"project_root": project_root.relative_to(ROOT).as_posix()}},
    )
    run_id = "pytest-a06-entry-" + uuid.uuid4().hex[:8]
    try:
        result = _run(
            [
                "--target",
                "PROJECT",
                "--project",
                "TP-002",
                "--project-registry",
                str(registry),
                "--run-id",
                run_id,
            ]
        )

        assert result.returncode == int(ExitCode.OK), result.stdout + result.stderr
        payload = json.loads(result.stdout)
        assert payload["target"] == "TP-002"
        assert "TP001运行入口.py" not in payload["entry"]
        marker = project_root / "reports" / f"{run_id}.json"
        assert json.loads(marker.read_text(encoding="utf-8"))["project_id"] == "TP-002"
    finally:
        if project_root.exists():
            shutil.rmtree(project_root)


def 测试A06直接L1未传章节时使用当前项目默认正文而不是TP001(tmp_path: Path):
    project_root = _write_project(ROOT / "运行记录" / ("pytest-TP002-l1-" + uuid.uuid4().hex[:8]), "TP-002")
    registry = _registry(
        tmp_path / "projects.json",
        default_project="TP-002",
        projects={"TP-002": {"project_root": project_root.relative_to(ROOT).as_posix()}},
    )
    out_dir = project_root / "l1-out"
    run_id = "pytest-a06-l1-" + uuid.uuid4().hex[:8]
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(L1_ENTRY),
                "--project",
                "TP-002",
                "--project-registry",
                str(registry),
                "--run-id",
                run_id,
                "--out-dir",
                str(out_dir),
            ],
            cwd=str(ROOT),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=30,
        )

        assert result.returncode in {int(ExitCode.OK), int(ExitCode.GATE_REJECTED), int(ExitCode.REVIEW_REQUIRED)}, result.stdout + result.stderr
        payload = json.loads(result.stdout)
        assert Path(payload["chapter"]).resolve() == (project_root / "chapters" / "ch01.md").resolve()
        report = json.loads(Path(payload["report_json"]).read_text(encoding="utf-8"))
        assert report["项目"] == "TP-002"
        assert report["章节路径"] == str((project_root / "chapters" / "ch01.md").resolve())
    finally:
        if project_root.exists():
            shutil.rmtree(project_root)


def 测试P11外部项目默认章节PIPELINE不读取TP001(tmp_path: Path):
    external = _write_project(tmp_path / "external-default", "EXT-PIPE")
    run_id = "pytest-p11-ext-default-" + uuid.uuid4().hex[:8]

    result = _run(
        [
            "--target",
            "PIPELINE",
            "--project-root",
            str(external),
            "--run-id",
            run_id,
        ]
    )

    assert result.returncode != PROJECT_ERROR, result.stdout + result.stderr
    manifest = json.loads((ROOT / "运行记录" / run_id / "流水线清单.json").read_text(encoding="utf-8"))
    assert manifest["input"]["original_path"] == str((external / "chapters" / "ch01.md").resolve())
    assert "TP-001_CleanHarness_IR_Runtime" not in manifest["input"]["original_path"]


def 测试P12_TP001流水线清单记录完整ProjectContext():
    run_id = "pytest-p12-tp001-" + uuid.uuid4().hex[:8]

    result = _run(
        [
            "--target",
            "PIPELINE",
            "--project",
            "TP-001",
            "--run-id",
            run_id,
        ]
    )

    assert (ROOT / "运行记录" / run_id / "流水线清单.json").exists(), result.stdout + result.stderr
    manifest = json.loads((ROOT / "运行记录" / run_id / "流水线清单.json").read_text(encoding="utf-8"))
    project = manifest["project"]
    assert project["project_id"] == "TP-001"
    assert Path(project["content_root"]).resolve() == (ROOT / "70_测试项目" / "TP-001_CleanHarness_IR_Runtime" / "chapters").resolve()
    assert Path(project["chapter_source"]).resolve() == Path(manifest["input"]["original_path"]).resolve()
    assert Path(project["entrypoint"]).name == "TP001运行入口.py"


def 测试P12外部项目流水线清单记录外部ProjectContext(tmp_path: Path):
    external = _write_project(tmp_path / "external-manifest", "EXT-MANIFEST")
    run_id = "pytest-p12-ext-" + uuid.uuid4().hex[:8]

    result = _run(
        [
            "--target",
            "PIPELINE",
            "--project-root",
            str(external),
            "--run-id",
            run_id,
        ]
    )

    assert (ROOT / "运行记录" / run_id / "流水线清单.json").exists(), result.stdout + result.stderr
    manifest = json.loads((ROOT / "运行记录" / run_id / "流水线清单.json").read_text(encoding="utf-8"))
    project = manifest["project"]
    assert project["project_id"] == "EXT-MANIFEST"
    assert project["source_scope"] == "external"
    assert Path(project["chapter_source"]).resolve() == (external / "chapters" / "ch01.md").resolve()
    assert "TP-001_CleanHarness_IR_Runtime" not in project["chapter_source"]


def 测试P11外部项目显式绝对章节PIPELINE先按ProjectContext解析(tmp_path: Path):
    external = _write_project(tmp_path / "external-explicit", "EXT-PIPE")
    chapter = (external / "chapters" / "ch01.md").resolve()
    run_id = "pytest-p11-ext-explicit-" + uuid.uuid4().hex[:8]

    result = _run(
        [
            "--target",
            "PIPELINE",
            "--project-root",
            str(external),
            "--chapter",
            str(chapter),
            "--run-id",
            run_id,
        ]
    )

    assert result.returncode != int(ExitCode.INPUT_INVALID), result.stdout + result.stderr
    assert result.returncode != PROJECT_ERROR, result.stdout + result.stderr
    manifest = json.loads((ROOT / "运行记录" / run_id / "流水线清单.json").read_text(encoding="utf-8"))
    assert manifest["input"]["original_path"] == str(chapter)


def 测试P11外部项目显式越界章节返回PROJECT_PATH_OUT_OF_SCOPE(tmp_path: Path):
    external = _write_project(tmp_path / "external-scope", "EXT-PIPE")
    outside = tmp_path / "outside.md"
    outside.write_text("# outside\n\n越界正文\n", encoding="utf-8")
    run_id = "pytest-p11-ext-scope-" + uuid.uuid4().hex[:8]

    result = _run(
        [
            "--target",
            "PIPELINE",
            "--project-root",
            str(external),
            "--chapter",
            str(outside.resolve()),
            "--run-id",
            run_id,
        ]
    )

    _assert_project_error(result, "PROJECT_PATH_OUT_OF_SCOPE")
    assert not (ROOT / "运行记录" / run_id).exists()


def 测试P11项目Root与显式Project不一致返回PROJECT_ID_MISMATCH(tmp_path: Path):
    external = _write_project(tmp_path / "external-mismatch", "EXT-PIPE")

    with pytest.raises(Exception) as excinfo:
        加载项目(ROOT, "OTHER", project_root=external)

    assert getattr(excinfo.value, "details", {})["reason"] == "PROJECT_ID_MISMATCH"


def 测试未知项目返回结构化PROJECT_RESOLUTION_FAILED且不创建运行记录():
    run_id = "pytest-loader-unknown-" + uuid.uuid4().hex[:8]
    result = _run(
        [
            "--target",
            "PIPELINE",
            "--chapter",
            str(CHAPTER),
            "--project",
            "UNKNOWN",
            "--run-id",
            run_id,
        ]
    )
    _assert_project_error(result, "PROJECT_RESOLUTION_FAILED")
    assert not (ROOT / "运行记录" / run_id).exists()


def 测试缺失项目目录返回结构化PROJECT_RESOLUTION_FAILED且不创建运行记录(tmp_path: Path):
    registry = _registry(
        tmp_path / "projects.json",
        projects={"TP-001": {"project_root": "70_测试项目/DOES_NOT_EXIST"}},
    )
    run_id = "pytest-loader-missing-" + uuid.uuid4().hex[:8]
    result = _run(
        [
            "--target",
            "PIPELINE",
            "--chapter",
            str(CHAPTER),
            "--run-id",
            run_id,
            "--project-registry",
            str(registry),
        ]
    )
    _assert_project_error(result, "PROJECT_RESOLUTION_FAILED")
    assert not (ROOT / "运行记录" / run_id).exists()


def 测试项目根越界返回结构化PROJECT_RESOLUTION_FAILED且不创建运行记录(tmp_path: Path):
    registry = _registry(
        tmp_path / "projects.json",
        projects={"TP-001": {"project_root": "../outside"}},
    )
    run_id = "pytest-loader-escape-" + uuid.uuid4().hex[:8]
    result = _run(
        [
            "--target",
            "PIPELINE",
            "--chapter",
            str(CHAPTER),
            "--run-id",
            run_id,
            "--project-registry",
            str(registry),
        ]
    )
    _assert_project_error(result, "PROJECT_RESOLUTION_FAILED")
    assert not (ROOT / "运行记录" / run_id).exists()
