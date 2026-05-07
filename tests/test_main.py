"""
main.py 핸들러 회귀 테스트
- 각 메뉴 핸들러의 출력과 부수효과(파일 변경)를 검증
- input()을 mock해 CLI 입력을 시뮬레이션
"""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

import app.crud as crud_module
import main
from tests.conftest import read_file


# ================================================================
# _print_record / _print_records
# ================================================================

class TestPrintHelpers:
    RECORD = {"id": 1, "name": "홍길동", "age": 30, "email": "hong@example.com", "city": "서울"}

    def test_print_record_contains_all_fields(self, capsys):
        main._print_record(self.RECORD)
        out = capsys.readouterr().out
        assert "[1]" in out
        assert "홍길동" in out
        assert "30" in out
        assert "hong@example.com" in out
        assert "서울" in out

    def test_print_records_empty_shows_no_result_message(self, capsys):
        main._print_records([])
        assert "결과 없음" in capsys.readouterr().out

    def test_print_records_shows_all_entries(self, capsys):
        records = [
            {"id": 1, "name": "홍길동", "age": 30, "email": "a@a.com", "city": "서울"},
            {"id": 2, "name": "김철수", "age": 25, "email": "b@b.com", "city": "부산"},
        ]
        main._print_records(records)
        out = capsys.readouterr().out
        assert "홍길동" in out
        assert "김철수" in out


# ================================================================
# handle_create
# ================================================================

class TestHandleCreate:
    def test_valid_input_prints_success(self, capsys):
        with patch("builtins.input", side_effect=["박민준", "35", "park@test.com", "대전"]):
            main.handle_create()
        assert "생성 완료" in capsys.readouterr().out

    def test_valid_input_persists_to_file(self, data_file):
        with patch("builtins.input", side_effect=["박민준", "35", "park@test.com", "대전"]):
            main.handle_create()
        assert any(r["name"] == "박민준" for r in read_file(data_file))

    def test_empty_name_shows_error(self, capsys):
        with patch("builtins.input", side_effect=["", "35", "park@test.com", "대전"]):
            main.handle_create()
        assert "오류" in capsys.readouterr().out

    def test_empty_email_shows_error(self, capsys):
        with patch("builtins.input", side_effect=["박민준", "35", "", "대전"]):
            main.handle_create()
        assert "오류" in capsys.readouterr().out

    def test_non_numeric_age_shows_error(self, capsys):
        with patch("builtins.input", side_effect=["박민준", "서른다섯", "park@test.com", "대전"]):
            main.handle_create()
        assert "오류" in capsys.readouterr().out

    def test_invalid_age_negative_shows_validation_error(self, capsys):
        with patch("builtins.input", side_effect=["박민준", "-1", "park@test.com", "대전"]):
            main.handle_create()
        assert "검증 오류" in capsys.readouterr().out

    def test_invalid_age_does_not_persist(self, data_file, capsys):
        with patch("builtins.input", side_effect=["박민준", "-1", "park@test.com", "대전"]):
            main.handle_create()
        assert len(read_file(data_file)) == 3  # 레코드 수 변화 없음


# ================================================================
# handle_read
# ================================================================

class TestHandleRead:
    def test_read_all_shows_every_record(self, capsys):
        with patch("builtins.input", return_value="1"):
            main.handle_read()
        out = capsys.readouterr().out
        assert "홍길동" in out
        assert "김철수" in out
        assert "이영희" in out

    def test_read_by_id_found(self, capsys):
        with patch("builtins.input", side_effect=["2", "2"]):
            main.handle_read()
        assert "김철수" in capsys.readouterr().out

    def test_read_by_id_not_found_shows_absent_message(self, capsys):
        with patch("builtins.input", side_effect=["2", "999"]):
            main.handle_read()
        assert "없음" in capsys.readouterr().out

    def test_read_by_id_non_numeric_shows_error(self, capsys):
        with patch("builtins.input", side_effect=["2", "abc"]):
            main.handle_read()
        assert "오류" in capsys.readouterr().out

    def test_search_found(self, capsys):
        with patch("builtins.input", side_effect=["3", "city", "서울"]):
            main.handle_read()
        assert "홍길동" in capsys.readouterr().out

    def test_search_not_found_shows_no_result(self, capsys):
        with patch("builtins.input", side_effect=["3", "city", "광주"]):
            main.handle_read()
        assert "결과 없음" in capsys.readouterr().out

    def test_invalid_submenu_choice_shows_error(self, capsys):
        with patch("builtins.input", return_value="9"):
            main.handle_read()
        assert "잘못된" in capsys.readouterr().out


# ================================================================
# handle_update
# ================================================================

class TestHandleUpdate:
    def test_update_field_prints_success(self, capsys):
        # ID=1 선택 후 name 변경, 나머지 빈 입력(유지)
        with patch("builtins.input", side_effect=["1", "새이름", "", "", ""]):
            main.handle_update()
        assert "수정 완료" in capsys.readouterr().out

    def test_update_persists_to_file(self, data_file):
        with patch("builtins.input", side_effect=["1", "새이름", "", "", ""]):
            main.handle_update()
        record = next(r for r in read_file(data_file) if r["id"] == 1)
        assert record["name"] == "새이름"

    def test_update_not_found_shows_absent_message(self, capsys):
        with patch("builtins.input", return_value="999"):
            main.handle_update()
        assert "없음" in capsys.readouterr().out

    def test_update_no_changes_shows_no_change_message(self, capsys):
        with patch("builtins.input", side_effect=["1", "", "", "", ""]):
            main.handle_update()
        assert "변경 사항 없음" in capsys.readouterr().out

    def test_update_non_numeric_id_shows_error(self, capsys):
        with patch("builtins.input", return_value="abc"):
            main.handle_update()
        assert "오류" in capsys.readouterr().out

    def test_update_invalid_age_shows_validation_error(self, capsys):
        # name 빈 입력, age=-1 입력
        with patch("builtins.input", side_effect=["1", "", "-1", "", ""]):
            main.handle_update()
        assert "검증 오류" in capsys.readouterr().out


# ================================================================
# handle_delete
# ================================================================

class TestHandleDelete:
    def test_delete_confirmed_prints_success(self, capsys):
        with patch("builtins.input", side_effect=["1", "y"]):
            main.handle_delete()
        assert "삭제 완료" in capsys.readouterr().out

    def test_delete_confirmed_removes_from_file(self, data_file):
        with patch("builtins.input", side_effect=["1", "y"]):
            main.handle_delete()
        assert all(r["id"] != 1 for r in read_file(data_file))

    def test_delete_cancelled_prints_cancel_message(self, capsys):
        with patch("builtins.input", side_effect=["1", "n"]):
            main.handle_delete()
        assert "취소" in capsys.readouterr().out

    def test_delete_cancelled_keeps_record_in_file(self, data_file):
        with patch("builtins.input", side_effect=["1", "n"]):
            main.handle_delete()
        assert any(r["id"] == 1 for r in read_file(data_file))

    def test_delete_not_found_shows_absent_message(self, capsys):
        with patch("builtins.input", return_value="999"):
            main.handle_delete()
        assert "없음" in capsys.readouterr().out

    def test_delete_non_numeric_id_shows_error(self, capsys):
        with patch("builtins.input", return_value="abc"):
            main.handle_delete()
        assert "오류" in capsys.readouterr().out
