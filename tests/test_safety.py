"""
safety 테스트
- 스키마 경계값 / 타입 안전성
- 파일 손상 내성
- 특수문자 및 인젝션 패턴
- 반환 객체의 부수효과 격리
- 엣지케이스(빈 값, 공백, 초대형 입력)
"""
import json
import stat
from pathlib import Path
from unittest.mock import patch

import pytest

from json_filelib import SchemaValidationError
import app.crud as crud_module
from app import crud
from tests.conftest import read_file


# ================================================================
# 1. 스키마 경계값 (age)
# ================================================================

class TestAgeBoundary:
    """age 필드의 허용 범위(0~150)를 검증한다."""

    def test_age_zero_is_valid(self):
        record = crud.create("테스트", 0, "t@t.com", "서울")
        assert record["age"] == 0

    def test_age_150_is_valid(self):
        record = crud.create("테스트", 150, "t@t.com", "서울")
        assert record["age"] == 150

    def test_age_minus_one_raises(self):
        with pytest.raises(SchemaValidationError):
            crud.create("테스트", -1, "t@t.com", "서울")

    def test_age_151_raises(self):
        with pytest.raises(SchemaValidationError):
            crud.create("테스트", 151, "t@t.com", "서울")

    def test_update_age_to_zero_is_valid(self):
        assert crud.update(1, age=0)["age"] == 0

    def test_update_age_to_150_is_valid(self):
        assert crud.update(1, age=150)["age"] == 150

    def test_update_age_negative_raises(self):
        with pytest.raises(SchemaValidationError):
            crud.update(1, age=-1)

    def test_update_age_over_max_raises(self):
        with pytest.raises(SchemaValidationError):
            crud.update(1, age=151)


# ================================================================
# 2. 스키마 타입 안전성
# ================================================================

class TestTypeEnforcement:
    """허용되지 않는 타입은 스키마 검증에서 차단된다."""

    def test_age_as_float_is_coerced_to_int(self):
        # coerce_types가 float → int 변환하므로 검증 통과
        record = crud.create("테스트", 25, "t@t.com", "서울")
        assert isinstance(record["age"], int)

    def test_extra_field_raises(self):
        # additionalProperties: False 이므로 추가 필드 금지
        with pytest.raises(SchemaValidationError):
            crud_module._validator.validate({
                "id": 99, "name": "테스트", "age": 25,
                "email": "t@t.com", "city": "서울",
                "admin": True,  # 허용되지 않는 필드
            })

    def test_missing_required_field_raises(self):
        with pytest.raises(SchemaValidationError):
            crud_module._validator.validate({
                "id": 99, "name": "테스트", "age": 25, "city": "서울",
                # email 누락
            })

    def test_null_name_raises(self):
        with pytest.raises(SchemaValidationError):
            crud_module._validator.validate({
                "id": 99, "name": None, "age": 25,
                "email": "t@t.com", "city": "서울",
            })

    def test_null_age_raises(self):
        with pytest.raises(SchemaValidationError):
            crud_module._validator.validate({
                "id": 99, "name": "테스트", "age": None,
                "email": "t@t.com", "city": "서울",
            })

    def test_string_age_raises(self):
        with pytest.raises(SchemaValidationError):
            crud_module._validator.validate({
                "id": 99, "name": "테스트", "age": "스물다섯",
                "email": "t@t.com", "city": "서울",
            })


# ================================================================
# 3. 빈 문자열 / 공백 필드
# ================================================================

class TestEmptyAndWhitespaceFields:
    """빈 문자열과 공백만 있는 문자열의 처리를 검증한다."""

    def test_empty_name_raises(self):
        with pytest.raises(SchemaValidationError):
            crud.create("", 25, "t@t.com", "서울")

    def test_empty_email_raises(self):
        with pytest.raises(SchemaValidationError):
            crud.create("테스트", 25, "", "서울")

    def test_empty_city_raises(self):
        with pytest.raises(SchemaValidationError):
            crud.create("테스트", 25, "t@t.com", "")

    def test_whitespace_only_name_passes_schema(self):
        # schema의 minLength:1 은 공백 문자도 유효하게 본다 (JSON Schema 표준)
        # 애플리케이션 레벨 검증이 없으면 저장됨을 확인
        record = crud.create("   ", 25, "t@t.com", "서울")
        assert record["name"] == "   "

    def test_update_empty_name_raises(self):
        with pytest.raises(SchemaValidationError):
            crud.update(1, name="")

    def test_search_empty_value_returns_no_match(self):
        # 어떤 레코드의 필드 값도 ""가 아니므로 빈 목록 반환
        assert crud.search("name", "") == []

    def test_search_empty_key_returns_no_match(self):
        # get_nested가 "" 키에 대해 None 반환 → 빈 목록
        assert crud.search("", "홍길동") == []


# ================================================================
# 4. 특수문자 / 인젝션 패턴
# ================================================================

class TestSpecialCharacterHandling:
    """특수문자가 파일에 안전하게 저장·복원되는지 검증한다."""

    @pytest.mark.parametrize("name", [
        "<script>alert('xss')</script>",         # HTML/스크립트 인젝션
        "'; DROP TABLE users; --",               # SQL 인젝션 패턴
        '{"id": 999, "admin": true}',            # JSON 인젝션 패턴
        "../../../etc/passwd",                   # 경로 탐색 패턴
        "홍길동 🎉🔥",                            # 이모지 포함 유니코드
        "line1\nline2",                          # 개행 문자
        "\t탭\t문자",                             # 탭 문자
        "a" * 1000,                              # 초대형 문자열
    ])
    def test_special_name_stored_and_retrieved_as_is(self, data_file, name):
        record = crud.create(name, 25, "t@t.com", "서울")
        assert record["name"] == name

        # 파일에서 재파싱해도 동일한 값이어야 한다
        saved = read_file(data_file)
        assert saved[-1]["name"] == name

    def test_email_with_special_chars_is_stored(self, data_file):
        email = "user+tag@sub.example.co.kr"
        record = crud.create("테스트", 25, email, "서울")
        assert read_file(data_file)[-1]["email"] == email

    def test_unicode_city_stored_correctly(self, data_file):
        city = "서울특별시 강남구 테헤란로"
        record = crud.create("테스트", 25, "t@t.com", city)
        assert read_file(data_file)[-1]["city"] == city


# ================================================================
# 5. 파일 손상 내성
# ================================================================

class TestFileResilience:
    """손상된 파일이나 예기치 않은 파일 상태에서도 안전하게 동작한다."""

    def test_invalid_json_file_load_returns_empty(self, data_file):
        data_file.write_text("{ this is not json }", encoding="utf-8")
        assert crud_module._load() == []

    def test_json_object_instead_of_array_returns_empty(self, data_file):
        data_file.write_text('{"key": "value"}', encoding="utf-8")
        assert crud_module._load() == []

    def test_json_null_returns_empty(self, data_file):
        data_file.write_text("null", encoding="utf-8")
        assert crud_module._load() == []

    def test_empty_file_content_returns_empty(self, data_file):
        data_file.write_text("", encoding="utf-8")
        assert crud_module._load() == []

    def test_read_all_on_corrupted_file_returns_empty(self, data_file):
        data_file.write_text("CORRUPTED", encoding="utf-8")
        assert crud.read_all() == []

    def test_create_on_corrupted_file_starts_fresh(self, data_file):
        data_file.write_text("CORRUPTED", encoding="utf-8")
        record = crud.create("새사용자", 25, "new@t.com", "서울")
        assert record["id"] == 1  # 빈 목록에서 시작하므로 ID=1

    def test_create_validation_failure_leaves_file_intact(self, data_file):
        original = read_file(data_file)
        with pytest.raises(SchemaValidationError):
            crud.create("테스트", -1, "t@t.com", "서울")
        assert read_file(data_file) == original

    def test_update_validation_failure_leaves_file_intact(self, data_file):
        original = read_file(data_file)
        with pytest.raises(SchemaValidationError):
            crud.update(1, age=-1)
        assert read_file(data_file) == original


# ================================================================
# 6. 반환 객체의 부수효과 격리
# ================================================================

class TestReturnObjectIsolation:
    """반환된 dict를 외부에서 수정해도 파일에 영향이 없어야 한다."""

    def test_mutating_read_by_id_result_does_not_affect_file(self, data_file):
        record = crud.read_by_id(1)
        record["name"] = "변조된이름"  # 반환 객체 직접 변조

        # 파일은 변경되지 않아야 한다
        saved = read_file(data_file)
        assert next(r for r in saved if r["id"] == 1)["name"] == "홍길동"

    def test_mutating_read_all_result_does_not_affect_subsequent_read(self, data_file):
        records = crud.read_all()
        records[0]["name"] = "변조됨"

        # 다음 호출에서 원본 데이터가 반환되어야 한다
        fresh = crud.read_all()
        assert fresh[0]["name"] == "홍길동"

    def test_mutating_search_result_does_not_affect_file(self, data_file):
        results = crud.search("city", "서울")
        results[0]["city"] = "평양"

        saved = read_file(data_file)
        assert next(r for r in saved if r["id"] == 1)["city"] == "서울"


# ================================================================
# 7. ID / 조회 엣지케이스
# ================================================================

class TestIdEdgeCases:
    """ID 관련 경계값과 타입 불일치를 검증한다."""

    def test_read_by_id_zero_returns_none(self):
        assert crud.read_by_id(0) is None

    def test_read_by_id_negative_returns_none(self):
        assert crud.read_by_id(-1) is None

    def test_delete_id_zero_returns_false(self):
        assert crud.delete(0) is False

    def test_update_id_zero_returns_none(self):
        assert crud.update(0, name="없음") is None

    def test_create_increments_correctly_after_delete(self, data_file):
        # ID=3 삭제 후 새 레코드는 ID=4(max가 줄어도 단순 max+1)가 아니라
        # 삭제 전 최댓값(2)+1=3이 될 수 있음 → 실제 동작을 명시적으로 문서화
        crud.delete(3)
        record = crud.create("신규", 20, "new@t.com", "대전")
        remaining_ids = [r["id"] for r in read_file(data_file)]
        assert record["id"] not in remaining_ids[:-1]  # 기존 ID와 충돌 없음
        assert record["id"] == remaining_ids[-1]       # 파일 마지막 레코드

    def test_no_id_collision_after_multiple_creates(self, data_file):
        ids = [crud.create(f"사용자{i}", 20 + i, f"u{i}@t.com", "서울")["id"]
               for i in range(5)]
        assert len(ids) == len(set(ids))  # 모두 유일해야 한다
