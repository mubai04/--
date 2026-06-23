from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
公共组件 = ROOT / "00_工程总控" / "工程执行层" / "公共组件"
L3工程 = ROOT / "00_工程总控" / "工程执行层" / "L3工程"
执行层 = ROOT / "00_工程总控" / "工程执行层"
for path in [L3工程, 公共组件, 执行层]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


@pytest.fixture
def root_case(tmp_path: Path):
    path = tmp_path / ("pytest-路径安全-" + uuid.uuid4().hex[:8])
    path.mkdir(parents=True)
    yield path


@pytest.fixture
def test_io_env(tmp_path: Path) -> dict[str, str]:
    token = tmp_path / "xcue-test-io-token.txt"
    token.write_text("XCUE_TEST_EXTERNAL_IO_TOKEN_V1", encoding="utf-8")
    return {**os.environ, "XCUE_TEST_ALLOW_EXTERNAL_IO": "1", "XCUE_TEST_IO_TOKEN_FILE": str(token)}
