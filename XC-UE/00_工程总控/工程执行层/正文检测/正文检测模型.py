from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class 段落:
    编号: int
    文本: str
    字数: int


@dataclass
class 证据:
    段落: int
    摘句: str


@dataclass
class 检测项:
    闸门: str
    名称: str
    状态: str
    说明: str
    证据: list[证据] = field(default_factory=list)
    严重级别: str = "info"
    失败类型: str = ""
    候选模块: str = ""
    回流验收位置: str = ""
    修复方向: str = ""


@dataclass
class 闸门结果:
    闸门: str
    判断结果: str
    失败类型: list[str]
    失败位置: list[证据]
    是否进入L15: str
    调用方向: list[str]
    回流验收位置: str
    最终状态: str
    检测项: list[检测项]


@dataclass
class 正文检测结果:
    run_id: str
    项目: str
    章节路径: str
    章节标题: str
    当前字数: int
    段落数: int
    方法声明: str
    闸门结果: list[闸门结果]
    失败包: list[检测项]
    路由建议: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
