from json_filelib import SchemaValidationError

from app import crud


# ---------- 출력 헬퍼 ----------

def _print_record(record: dict) -> None:
    print(
        f"  [{record['id']}] {record['name']} | 나이: {record['age']} "
        f"| 이메일: {record['email']} | 도시: {record['city']}"
    )


def _print_records(records: list[dict]) -> None:
    if not records:
        print("  결과 없음.")
        return
    for r in records:
        _print_record(r)


# ---------- 메뉴 핸들러 ----------

def handle_create() -> None:
    print("\n[신규 레코드 등록]")
    name  = input("  이름: ").strip()
    age   = input("  나이: ").strip()
    email = input("  이메일: ").strip()
    city  = input("  도시: ").strip()

    if not all([name, age, email, city]):
        print("  오류: 모든 필드를 입력해야 합니다.")
        return

    try:
        record = crud.create(name, int(age), email, city)
        print(f"  생성 완료:")
        _print_record(record)
    except ValueError:
        print("  오류: 나이는 숫자여야 합니다.")
    except SchemaValidationError as e:
        print(f"  검증 오류: {e}")


def handle_read() -> None:
    print("\n[조회]")
    print("  1) 전체 목록")
    print("  2) ID로 검색")
    print("  3) 필드 값으로 검색")
    choice = input("  선택: ").strip()

    if choice == "1":
        print("\n  --- 전체 목록 ---")
        _print_records(crud.read_all())

    elif choice == "2":
        try:
            rid = int(input("  ID: ").strip())
            record = crud.read_by_id(rid)
            if record:
                _print_record(record)
            else:
                print(f"  ID {rid} 레코드 없음.")
        except ValueError:
            print("  오류: ID는 숫자여야 합니다.")

    elif choice == "3":
        key   = input("  검색 필드 (name/age/email/city): ").strip()
        value = input("  검색 값: ").strip()
        results = crud.search(key, value)
        print(f"\n  --- '{key}' = '{value}' 검색 결과 ---")
        _print_records(results)

    else:
        print("  잘못된 선택.")


def handle_update() -> None:
    print("\n[레코드 수정]")
    try:
        rid = int(input("  수정할 ID: ").strip())
    except ValueError:
        print("  오류: ID는 숫자여야 합니다.")
        return

    record = crud.read_by_id(rid)
    if not record:
        print(f"  ID {rid} 레코드 없음.")
        return

    print(f"  현재 데이터: ", end="")
    _print_record(record)
    print("  수정할 필드와 값을 입력하세요. (빈 입력 시 유지)")

    fields = {}
    for field in ("name", "age", "email", "city"):
        val = input(f"  {field} [{record[field]}]: ").strip()
        if val:
            fields[field] = int(val) if field == "age" else val

    if not fields:
        print("  변경 사항 없음.")
        return

    try:
        updated = crud.update(rid, **fields)
        print("  수정 완료:")
        _print_record(updated)
    except (ValueError, TypeError) as e:
        print(f"  오류: {e}")
    except SchemaValidationError as e:
        print(f"  검증 오류: {e}")


def handle_delete() -> None:
    print("\n[레코드 삭제]")
    try:
        rid = int(input("  삭제할 ID: ").strip())
    except ValueError:
        print("  오류: ID는 숫자여야 합니다.")
        return

    record = crud.read_by_id(rid)
    if not record:
        print(f"  ID {rid} 레코드 없음.")
        return

    print(f"  삭제 대상: ", end="")
    _print_record(record)
    confirm = input("  삭제하시겠습니까? (y/N): ").strip().lower()

    if confirm == "y":
        crud.delete(rid)
        print(f"  ID {rid} 삭제 완료.")
    else:
        print("  삭제 취소.")


# ---------- 메인 루프 ----------

def main() -> None:
    print("=" * 50)
    print("  JSON CRUD 애플리케이션 (json-filelib 기반)")
    print("=" * 50)

    handlers = {
        "1": handle_create,
        "2": handle_read,
        "3": handle_update,
        "4": handle_delete,
    }

    while True:
        print("\n[메뉴]")
        print("  1) 생성 (Create)")
        print("  2) 조회 (Read)")
        print("  3) 수정 (Update)")
        print("  4) 삭제 (Delete)")
        print("  0) 종료")

        choice = input("\n선택: ").strip()

        if choice == "0":
            print("종료합니다.")
            break

        handler = handlers.get(choice)
        if handler:
            handler()
        else:
            print("  잘못된 선택입니다.")


if __name__ == "__main__":
    main()
