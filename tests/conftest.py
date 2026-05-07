import json
from pathlib import Path
from unittest.mock import patch

import pytest

import app.crud as crud_module

SAMPLE_RECORDS = [
    {"id": 1, "name": "홍길동", "age": 30, "email": "hong@example.com", "city": "서울"},
    {"id": 2, "name": "김철수", "age": 25, "email": "kim@example.com", "city": "부산"},
    {"id": 3, "name": "이영희", "age": 28, "email": "lee@example.com", "city": "인천"},
]


@pytest.fixture
def data_file(tmp_path: Path) -> Path:
    """각 테스트 전에 샘플 데이터가 담긴 임시 JSON 파일을 생성."""
    f = tmp_path / "records.json"
    f.write_text(
        json.dumps(SAMPLE_RECORDS, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return f


@pytest.fixture(autouse=True)
def patch_data_file(data_file: Path):
    """DATA_FILE을 임시 파일로 교체해 실제 데이터 파일을 보호."""
    with patch.object(crud_module, "DATA_FILE", data_file):
        yield data_file


def read_file(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))
