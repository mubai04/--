from __future__ import annotations

from pathlib import Path

from L3模型 import L2修复单, L3执行任务
from IR输入映射校验 import 映射IR
from ProjectHarness运行校验 import 默认候选目标, 相对


def 任务类型(form: L2修复单) -> str:
    if form.主失败类型 == "字数不足":
        return "正文扩写任务规划"
    if form.接收模块 in {"L2-05", "L2-02"}:
        return "正文局部修复任务规划"
    return "正文改写任务规划"


def 生成(forms: list[L2修复单], source_file: str, run_id: str, root: Path, harness: Path) -> list[L3执行任务]:
    tasks: list[L3执行任务] = []
    for idx, form in enumerate(forms, start=1):
        formal_chapters = [相对(root, path) for path in sorted((harness / "chapters").glob("ch*.md"))]
        tasks.append(
            L3执行任务(
                执行编号=f"L3RUN-{run_id}-{idx:03d}",
                来源层=form.接收模块,
                来源文件=source_file,
                ProjectHarness根=相对(root, harness),
                任务类型=任务类型(form),
                输入材料=form.输入问题,
                IR输入=映射IR(form, root, harness),
                目标文件=默认候选目标(root, harness, run_id, idx),
                禁止修改文件=[
                    *formal_chapters,
                    "20_L1_闸门层/*",
                    "30_L1.5_路由矩阵层/*",
                    "40_L2_正式能力层/*",
                    "50_L3_执行协议层/*",
                ],
                修复方向=form.修复动作,
                修复产物要求=form.修复产物,
                回流验收位置=form.回流位置,
                是否允许改正式正文="否",
                是否需要备份="不适用",
            )
        )
    return tasks
