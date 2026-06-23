from __future__ import annotations

from L3模型 import L3执行任务


VALID_RETURNS = {"L1-00", "L1-01", "L1-02", "L1-03", "L1.5"}


def 校验(task: L3执行任务) -> list[str]:
    if task.回流验收位置 not in VALID_RETURNS:
        return [f"回流验收位置异常：{task.回流验收位置}"]
    return []
