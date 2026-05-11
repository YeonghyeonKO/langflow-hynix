# NAS PV + SQLite 초기 배포 시 Alembic migration race condition

## 현상

NAS PV(Network Attached Storage Persistent Volume)에 SQLite DB를 저장하는 Helm 배포 환경에서, **최초 배포 시 Pod가 1~2회 재시작 후 정상 기동**되는 현상 발생.

### 에러 로그

```
_run_migrations raise RuntimeError(msg) from RuntimeError:
Error initializing alembic
Online migration expected to match one row when updating
'7843803a87b5' to 'f5ee9749d1a6' in 'alembic_version'
0 found
```

## 원인

Langflow 시작 시 `run_migrations()`가 `alembic_version` 테이블 존재 여부를 확인하여 초기화 필요 여부를 판단합니다:

```python
# 기존 로직 (src/backend/base/langflow/services/database/service.py)
try:
    await session.exec(text("SELECT * FROM alembic_version"))
except Exception:
    should_initialize_alembic = True  # 테이블 없으면 초기화
```

### 문제 시나리오

```
1. Pod 최초 시작
   -> SQLite DB 생성 (NAS PV에 저장)
   -> Alembic 초기화 시작
   -> alembic_version 테이블 CREATE
   -> upgrade 실행 중...

2. NAS I/O 지연 또는 readiness probe 실패로 Pod crash

3. Pod 재시작
   -> SQLite DB 이미 존재 (NAS PV에 남아있음)
   -> alembic_version 테이블 존재 (CREATE는 완료됨)
   -> BUT 테이블이 비어있음 (version row INSERT가 commit되기 전 crash)
   -> SELECT * FROM alembic_version -> 성공 (테이블 존재)
   -> should_initialize_alembic = False (초기화 불필요로 판단)

4. Alembic upgrade 실행
   -> UPDATE alembic_version SET version='f5ee9749d1a6'
      WHERE version='7843803a87b5'
   -> 0 rows matched -> RuntimeError!
```

**핵심: 테이블 "존재 여부"만 체크하고, 테이블이 "비어있는지"는 체크하지 않음.**

## 수정

`run_migrations()`에서 테이블 존재 + 행 존재 여부를 함께 확인:

```python
# 수정된 로직
try:
    result = await session.exec(text("SELECT * FROM alembic_version"))
    rows = result.all()
    if not rows:
        # 테이블은 있지만 비어있음 -> 이전 crash로 인한 불완전 상태
        await session.exec(text("DROP TABLE alembic_version"))
        await session.commit()
        should_initialize_alembic = True  # clean upgrade from base
except Exception:
    should_initialize_alembic = True
```

## 영향 범위

| 환경 | 영향 |
|------|------|
| NAS PV + SQLite | **해당** (이 이슈 발생) |
| 로컬 PV + SQLite | 해당 없음 (Pod 재생성 시 DB도 초기화) |
| PostgreSQL | 해당 없음 (트랜잭션 안정성이 높음) |
| 수정 후 기존 정상 DB | 영향 없음 (rows 있으면 기존 로직 동일) |

## 재현 조건

1. Helm chart로 NAS PV에 SQLite 저장하는 구성으로 배포
2. 최초 배포 (DB 없는 상태)
3. Pod 시작 후 Alembic migration 중 crash 발생 (또는 강제 kill)
4. Pod 재시작 시 에러 발생

## 관련 커밋

- `ba8affab5b` (v1.9.1-hynix-rc28)

## 수정 파일

- `src/backend/base/langflow/services/database/service.py` — `run_migrations()` 메서드
