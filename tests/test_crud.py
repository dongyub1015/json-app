"""
app/crud.py 회귀 테스트
- 내부 헬퍼(_next_id, _load)와 CRUD 함수 전체 커버
- 각 테스트는 임시 JSON 파일을 사용하므로 실제 데이터를 건드리지 않음
"""
from pathlib import Path
from unittest.mock import patch

import pytest

from json_filelib import SchemaValidationError
import app.crud as crud_module
from app import crud
from tests.conftest import read_file


# ================================================================
# _next_id
# ================================================================

class TestNextId:
    def test_empty_list_returns_one(self):
        assert crud_module._next_id([]) == 1

    def test_sequential_ids(self):
        records = [{"id": 1}, {"id": 2}, {"id": 3}]
        assert crud_module._next_id(records) == 4

    def test_non_contiguous_ids_uses_max(self):
        records = [{"id": 1}, {"id": 10}]
        assert crud_module._next_id(records) == 11


# ================================================================
# _load
# ================================================================

class TestLoad:
    def test_valid_file_returns_list(self):
        records = crud_module._load()
        assert isinstance(records, list)
        assert len(records) == 3

    def test_missing_file_returns_empty_list(self, tmp_path):
        with patch.object(crud_module, "DATA_FILE", tmp_path / "nonexistent.json"):
            assert crud_module._load() == []

    def test_non_list_json_returns_empty_list(self, data_file):
        data_file.write_text('{"key": "value"}', encoding="utf-8")
        assert crud_module._load() == []

    def test_empty_array_returns_empty_list(self, data_file):
        data_file.write_text("[]", encoding="utf-8")
        assert crud_module._load() == []


# ================================================================
# create
# ================================================================

class TestCreate:
    def test_returns_dict_with_correct_fields(self):
        record = crud.create("박민준", 35, "park@example.com", "대전")
        assert record == {
            "id": 4,
            "name": "박민준",
            "age": 35,
            "email": "park@example.com",
            "city": "대전",
        }

    def test_id_is_max_plus_one(self):
        record = crud.create("박민준", 35, "park@example.com", "대전")
        assert record["id"] == 4  # SAMPLE_RECORDS max id=3

    def test_persists_to_file(self, data_file):
        crud.create("박민준", 35, "park@example.com", "대전")
        saved = read_file(data_file)
        assert len(saved) == 4
        assert saved[-1]["name"] == "박민준"

    def test_first_record_on_empty_file_gets_id_one(self, data_file):
        data_file.write_text("[]", encoding="utf-8")
        record = crud.create("첫번째", 20, "first@example.com", "서울")
        assert record["id"] == 1

    def test_negative_age_raises_schema_error(self):
        with pytest.raises(SchemaValidationError):
            crud.create("테스트", -1, "t@t.com", "서울")

    def test_age_over_150_raises_schema_error(self):
        with pytest.raises(SchemaValidationError):
            crud.create("테스트", 200, "t@t.com", "서울")

    def test_empty_name_raises_schema_error(self):
        with pytest.raises(SchemaValidationError):
            crud.create("", 25, "t@t.com", "서울")

    def test_empty_email_raises_schema_error(self):
        with pytest.raises(SchemaValidationError):
            crud.create("테스트", 25, "", "서울")

    def test_empty_city_raises_schema_error(self):
        with pytest.raises(SchemaValidationError):
            crud.create("테스트", 25, "t@t.com", "")

    def test_file_not_mutated_on_validation_failure(self, data_file):
        with pytest.raises(SchemaValidationError):
            crud.create("테스트", -1, "t@t.com", "서울")
        assert len(read_file(data_file)) == 3  # 원본 유지


# ================================================================
# read_all
# ================================================================

class TestReadAll:
    def test_returns_all_records(self):
        assert len(crud.read_all()) == 3

    def test_returns_empty_list_on_empty_file(self, data_file):
        data_file.write_text("[]", encoding="utf-8")
        assert crud.read_all() == []

    def test_fields_filter_includes_only_specified_fields(self):
        records = crud.read_all(fields=["name", "city"])
        for r in records:
            assert set(r.keys()) == {"name", "city"}

    def test_no_filter_returns_all_fields(self):
        expected = {"id", "name", "age", "email", "city"}
        for r in crud.read_all():
            assert set(r.keys()) == expected

    def test_order_is_preserved(self):
        ids = [r["id"] for r in crud.read_all()]
        assert ids == [1, 2, 3]


# ================================================================
# read_by_id
# ================================================================

class TestReadById:
    def test_found_returns_correct_record(self):
        record = crud.read_by_id(1)
        assert record is not None
        assert record["name"] == "홍길동"

    def test_returns_different_records_by_id(self):
        assert crud.read_by_id(2)["name"] == "김철수"
        assert crud.read_by_id(3)["name"] == "이영희"

    def test_not_found_returns_none(self):
        assert crud.read_by_id(999) is None

    def test_returns_complete_record(self):
        record = crud.read_by_id(1)
        assert set(record.keys()) == {"id", "name", "age", "email", "city"}


# ================================================================
# search
# ================================================================

class TestSearch:
    def test_search_by_name(self):
        results = crud.search("name", "홍길동")
        assert len(results) == 1
        assert results[0]["id"] == 1

    def test_search_by_city(self):
        results = crud.search("city", "부산")
        assert len(results) == 1
        assert results[0]["id"] == 2

    def test_search_by_age(self):
        results = crud.search("age", "30")
        assert len(results) == 1
        assert results[0]["name"] == "홍길동"

    def test_no_match_returns_empty_list(self):
        assert crud.search("city", "광주") == []

    def test_case_insensitive_match(self):
        results = crud.search("email", "HONG@EXAMPLE.COM")
        assert len(results) == 1

    def test_unknown_key_returns_empty_list(self):
        # 존재하지 않는 키: get_nested가 None 반환 → 결과 없음
        assert crud.search("phone", "010-0000-0000") == []

    def test_multiple_matches(self, data_file):
        import json
        records = json.loads(data_file.read_text(encoding="utf-8"))
        records.append({"id": 4, "name": "박서울", "age": 22, "email": "s@s.com", "city": "서울"})
        data_file.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")

        results = crud.search("city", "서울")
        assert len(results) == 2


# ================================================================
# update
# ================================================================

class TestUpdate:
    def test_single_field_updated(self):
        updated = crud.update(1, city="광주")
        assert updated["city"] == "광주"

    def test_non_updated_fields_are_preserved(self):
        updated = crud.update(1, city="광주")
        assert updated["name"] == "홍길동"
        assert updated["age"] == 30
        assert updated["email"] == "hong@example.com"

    def test_multiple_fields_updated(self):
        updated = crud.update(2, name="김영수", age=26)
        assert updated["name"] == "김영수"
        assert updated["age"] == 26

    def test_not_found_returns_none(self):
        assert crud.update(999, city="서울") is None

    def test_persists_to_file(self, data_file):
        crud.update(1, city="대구")
        saved = read_file(data_file)
        assert next(r for r in saved if r["id"] == 1)["city"] == "대구"

    def test_does_not_affect_other_records(self, data_file):
        crud.update(1, city="대구")
        saved = read_file(data_file)
        assert next(r for r in saved if r["id"] == 2)["city"] == "부산"

    def test_invalid_age_raises_schema_error(self):
        with pytest.raises(SchemaValidationError):
            crud.update(1, age=-5)

    def test_file_not_mutated_on_validation_failure(self, data_file):
        with pytest.raises(SchemaValidationError):
            crud.update(1, age=-5)
        saved = read_file(data_file)
        assert next(r for r in saved if r["id"] == 1)["age"] == 30


# ================================================================
# delete
# ================================================================

class TestDelete:
    def test_existing_record_returns_true(self):
        assert crud.delete(1) is True

    def test_non_existing_record_returns_false(self):
        assert crud.delete(999) is False

    def test_record_removed_from_file(self, data_file):
        crud.delete(2)
        saved = read_file(data_file)
        assert all(r["id"] != 2 for r in saved)

    def test_file_count_decreases_by_one(self, data_file):
        crud.delete(1)
        assert len(read_file(data_file)) == 2

    def test_other_records_not_affected(self, data_file):
        crud.delete(1)
        saved = read_file(data_file)
        remaining_ids = [r["id"] for r in saved]
        assert 2 in remaining_ids
        assert 3 in remaining_ids

    def test_double_delete_second_returns_false(self):
        crud.delete(1)
        assert crud.delete(1) is False
