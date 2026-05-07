from pathlib import Path

from json_filelib import (
    JsonParser,
    JsonWriter,
    JsonValidator,
    JsonTransformer,
    JsonParseError,
    SchemaValidationError,
)
from app.schema import RECORD_SCHEMA

DATA_FILE = Path(__file__).parent.parent / "data" / "records.json"

_parser = JsonParser()
_writer = JsonWriter()
_validator = JsonValidator(RECORD_SCHEMA)
_transformer = JsonTransformer()


# ---------- 내부 헬퍼 ----------

def _load() -> list[dict]:
    """파일에서 전체 레코드를 파싱해 반환."""
    try:
        data = _parser.parse_file(DATA_FILE)
        return data if isinstance(data, list) else []
    except JsonParseError:
        return []


def _save(records: list[dict]) -> None:
    """레코드 목록을 JSON 파일에 저장."""
    _writer.save_as_json(records, DATA_FILE, indent=2, ensure_ascii=False)


def _next_id(records: list[dict]) -> int:
    return max((r["id"] for r in records), default=0) + 1


# ---------- Create ----------

def create(name: str, age: int, email: str, city: str) -> dict:
    """새 레코드를 생성하고 파일에 저장."""
    # 1) 파싱: 기존 데이터 로드
    records = _load()

    # 2) 신규 레코드 구성 + 타입 강제 변환
    new_record = _transformer.coerce_types(
        {"id": _next_id(records), "name": name, "age": age, "email": email, "city": city},
        {"id": int, "age": int},
    )

    # 3) 스키마 검증
    _validator.validate(new_record)

    # 4) 저장
    records.append(new_record)
    _save(records)
    return new_record


# ---------- Read ----------

def read_all(fields: list[str] | None = None) -> list[dict]:
    """전체 레코드를 반환. fields 지정 시 해당 필드만 포함."""
    # 1) 파싱
    records = _load()

    # 2) 변환: 필드 필터링
    if fields:
        records = _transformer.filter_fields(records, include=fields)

    return records


def read_by_id(record_id: int) -> dict | None:
    """ID로 단일 레코드를 반환."""
    # 1) 파싱
    records = _load()

    # 2) ID 검색 (get_nested 활용)
    for record in records:
        if _parser.get_nested(record, "id") == record_id:
            return record
    return None


def search(key: str, value: str) -> list[dict]:
    """특정 필드 값으로 레코드를 검색."""
    # 1) 파싱
    records = _load()

    # 2) 변환: 검색 키 필드만 추출 후 값 비교
    result = []
    for record in records:
        field_val = _parser.get_nested(record, key)
        if field_val is not None and str(field_val).lower() == value.lower():
            result.append(record)
    return result


# ---------- Update ----------

def update(record_id: int, **fields) -> dict | None:
    """ID로 레코드를 찾아 지정한 필드를 수정."""
    # 1) 파싱
    records = _load()

    target = None
    for record in records:
        if _parser.get_nested(record, "id") == record_id:
            target = record
            break

    if target is None:
        return None

    # 2) 변환: 타입 강제 변환 후 필드 업데이트
    type_rules = {k: type(target[k]) for k in fields if k in target}
    coerced = _transformer.coerce_types(fields, type_rules)
    target.update(coerced)

    # 3) 검증
    _validator.validate(target)

    # 4) 저장
    _save(records)
    return target


# ---------- Delete ----------

def delete(record_id: int) -> bool:
    """ID로 레코드를 찾아 삭제."""
    # 1) 파싱
    records = _load()

    # 2) 변환: 해당 ID 제외한 목록 생성
    filtered = [r for r in records if _parser.get_nested(r, "id") != record_id]

    if len(filtered) == len(records):
        return False

    # 3) 저장
    _save(filtered)
    return True
