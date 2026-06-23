from __future__ import annotations

from pathlib import Path


def 读文本(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"文件不存在：{path}")
    return path.read_text(encoding="utf-8-sig")


def 读标准(root: Path) -> dict[str, str]:
    files = {
        "L1-01": root / "20_L1_闸门层" / "L1-01_五大创作问题_技术护栏闭环图.md",
        "L1-02": root / "20_L1_闸门层" / "L1-02_读者投入意愿工程图.md",
        "L1-03": root / "20_L1_闸门层" / "L1-03_发布锁验收工程图.md",
        "L1.5": root / "30_L1.5_路由矩阵层" / "L1.5_Routing_Matrix.md",
        "L2-99": root / "40_L2_正式能力层" / "L2-99_能力层接口总表_v0.1.1_自检修正版.md",
    }
    return {name: 读文本(path) for name, path in files.items()}
