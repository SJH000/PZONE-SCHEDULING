# P-ZONE Scheduling Project Handoff

작성일: 2026-06-18  
프로젝트 경로: `C:\Users\SHINJUNGHYUN\pzone_scheduling`

## 1. 프로젝트 개요

P-ZONE 스케줄링 프로젝트의 목표는 제조 라인의 전체 공정 로그를 이용해 병목 위치와 원인을 진단하고, 병목별로 스케줄링으로 개선 가능한지 또는 설비/버퍼/이송 자원 같은 물리적 개선이 필요한지를 구분하는 것이다.

초기에는 A9 공정만 보면 병목을 찾을 수 있을지 검토했지만, 단일 공정만 보는 방식으로는 전체 흐름 병목을 설명하기 어렵다는 결론이 나왔다. 이후 분석 방향은 DB 전체를 활용해 제품별 route, 처리시간, 공정 간 대기시간, WIP, 이송/레일 점유, OEE 상태를 함께 계산하는 방식으로 확장했다.

현재 분석의 핵심 관점은 다음과 같다.

- 제품은 `PRD1000`, `PRD2000`, `PRD3001`, `PRD3002` 네 종류를 대상으로 한다.
- 제품군별 route가 다르므로 정상 route를 먼저 확정한 뒤 분석한다.
- 모든 공정을 동일 지표로 1차 스크리닝한다.
- 병목 근거가 강한 A3, A4, A9, A7, A5, AMR/레일을 심층 분석한다.
- 매뉴얼의 공정 의미를 함께 사용해 숫자만이 아니라 병목 발생 구조를 해석한다.

현재까지는 **1~5번 분석/진단 단계**를 완료했다. 다음 단계는 **6번부터 시작되는 개선안 설계/검증 단계**다.

```text
1. 데이터/분석 검증
2. A3 병목 세분화
3. A4 공유 레일 blocking 검증
4. 제품군별 병목 분리
5. 레일/AMR 이송 자원 분석 고도화
6. Rule-based scheduling baseline 설계
7. 로그 리플레이/시뮬레이션 평가
8. LLM-assisted decision agent 설계
9. 현장 적용용 대시보드/리포트화
```

## 2. 입력 자료와 데이터 환경

### 원본 파일

루트 경로에 아래 자료가 있다.

| 파일 | 역할 |
|---|---|
| `jnb_db_dump_2026-05-07.sql` | P-ZONE DB 덤프 원본 |
| `jnb_db_dump_2026-05-07.zip` | SQL 덤프 압축본 |
| `DB_SCHEMA.pdf` | DB 테이블 구조 문서 |
| `SDF_OCS_SQL_detail_v3.xlsx` | SQL 상세 설명, 컬럼 정의, 공정별 변수 정의 |
| `전북대학교_매뉴얼_통합본_260323.pdf` | P-ZONE 공정 매뉴얼 |
| `PZONE_프로젝트_개요_및_수행계획.docx` | 초기 프로젝트 개요 및 수행계획 |

### DB 구축 방식

MariaDB에 적재하지 않고, SQL dump에서 필요한 테이블을 추출해 SQLite/CSV 기반으로 분석했다.

생성된 SQLite DB:

```text
data/pzone_analysis.sqlite
```

분석에 사용한 주요 테이블:

| 테이블 | 용도 |
|---|---|
| `prc_hist_tb` | 공정별 STR/END 이력, 처리시간 계산 |
| `prc_trns_tb` | 이송/레일/AMR 관련 이벤트, 점유/이동 흐름 분석 |
| `prc_oee_tb` | RUN/IDLE/ALARM 상태 비율 |
| `strg_buf_in`, `strg_buf_out` | 버퍼 WIP 계산 |
| `strg_fns_in`, `strg_fns_out` | 완제품 창고 입출고 계산 |
| `std_eqpmn_tb` | 설비 ID와 공정명 매핑 |
| `std_strg_cd` | 저장소 코드 의미 |
| `std_prdct_tb` | 제품 코드 정보 |

## 3. 코드 구조

### 핵심 스크립트

| 파일 | 설명 |
|---|---|
| `run_pzone_analysis.py` | SQL dump 추출, SQLite/CSV 생성, 정상 route 필터, 병목 지표 계산, 기본 보고서/그래프 생성 |
| `build_2026_06_14_package.py` | 기존 분석 결과를 `outputs/2026_06_14` 패키지로 정리 |
| `build_phase_1_to_5_analysis.py` | 1~5번 분석 심화, 추가 CSV/그래프/리포트/PPT 생성 |
| `build_pzone_ppt.py` | 초기 7장 PPT 생성 스크립트 |
| `requirements.txt` | Python 의존성 |

### 재현 명령

처음부터 다시 생성할 때는 아래 순서로 실행한다.

```powershell
pip install -r requirements.txt
python run_pzone_analysis.py
python build_2026_06_14_package.py
python build_phase_1_to_5_analysis.py
```

초기 버전 PPT만 다시 만들고 싶다면:

```powershell
python build_pzone_ppt.py
```

현재 최종 PPT는 `build_phase_1_to_5_analysis.py`에서 생성된다.

## 4. 주요 산출물 위치

### 기본 분석 산출물

```text
outputs/data/
outputs/report/
outputs/report/figures/
```

주요 파일:

| 파일 | 설명 |
|---|---|
| `outputs/data/product_routes.csv` | 정상 route 필터 이후 제품별 공정 이벤트 |
| `outputs/data/all_product_routes_before_filter.csv` | 필터 전 전체 route 이벤트 |
| `outputs/data/equipment_processing_events.csv` | 처리시간 이벤트 |
| `outputs/data/transition_waiting_events.csv` | 공정 간 대기 이벤트 |
| `outputs/data/bottleneck_ranking.csv` | 전체 병목 순위 |
| `outputs/report/PZONE_bottleneck_analysis_report.md` | 기본 병목 분석 보고서 |
| `outputs/report/PZONE_process_semantics.md` | 매뉴얼 기반 공정 의미 정리 |
| `outputs/report/PZONE_analysis_summary.xlsx` | 요약 Excel |

### 2026-06-14 정리 패키지

```text
outputs/2026_06_14/
```

주요 문서:

| 파일 | 설명 |
|---|---|
| `README.md` | 결과물 읽는 순서 |
| `00_executive_summary.md` | 핵심 결론 요약 |
| `01_analysis_flow.md` | 분석 흐름 |
| `02_data_scope_and_cleaning.md` | 데이터 범위와 clean 기준 |
| `03_normal_routes.md` | 제품별 정상 route |
| `04_all_process_screening.md` | 전체 공정 병목 스크리닝 |
| `05_key_bottleneck_deep_dive.md` | 주요 병목 심층 분석 |
| `06_shared_rail_blocking.md` | A4와 공유 레일 blocking 분석 |
| `07_schedulability_and_actions.md` | 스케줄링 가능성 및 추천 액션 |
| `08_remaining_work.md` | 남은 작업 |
| `09_ppt_briefing_for_gpt.md` | PPT 생성을 위한 브리핑 |

### 1~5번 심화 분석 패키지

```text
outputs/2026_06_14/phase_1_to_5_analysis/
```

주요 파일:

| 파일 | 설명 |
|---|---|
| `phase_1_to_5_summary.md` | 1~5번 분석 요약 |
| `required_field_gap_report.md` | 현재 데이터로 확정 불가능한 정보와 필요한 현장 정보 |
| `reports/01_data_validation.md` | 데이터/route/페어링 검증 |
| `reports/02_a3_deep_dive.md` | A3 병목 세분화 |
| `reports/03_a4_shared_rail_validation.md` | A4 공유 레일 검증 |
| `reports/04_product_family_analysis.md` | 제품군별 병목 분리 |
| `reports/05_rail_amr_analysis.md` | 레일/AMR 이송 자원 분석 |

주요 PPT:

| 파일 | 설명 |
|---|---|
| `outputs/2026_06_14/PZONE_bottleneck_phase1_5_summary_7slides.pptx` | 최종 7장 PPT, 발표자 메모 포함 |
| `outputs/2026_06_14/PZONE_bottleneck_phase1_5_ppt_script.md` | PPT 발표 대본 |
| `outputs/2026_06_14/PZONE_bottleneck_phase1_5_ppt_script_1min.md` | 각 슬라이드 1분용 대본 |

## 5. 정상 제품과 정상 Route 기준

분석 대상 제품은 다음 네 종류다.

```text
PRD1000
PRD2000
PRD3001
PRD3002
```

정상 route는 제품별 로그를 통계적으로 집계해 산출했다. AMR/C2 등 후단 선택적 이송 이벤트는 route validation에서는 제외하고, 공정 흐름 분석에서는 별도로 해석했다.

| 제품 | 정상 route | 총 serial | 정확 일치 수 |
|---|---|---:|---:|
| `PRD1000` | `C1_RAW_STORAGE > A1 > A2 > A4 > A5 > A6_KONA > A7 > A9_2 > A8 > A9_2 > A3` | 137 | 51 |
| `PRD2000` | `C1_RAW_STORAGE > A1 > A2 > A4 > A5 > A6_TESLA > A7 > A9_2 > A8 > A9_2 > A3` | 95 | 50 |
| `PRD3001` | `C1_RAW_STORAGE > A1 > A2 > A7 > A5 > A9_1 > A3` | 53 | 34 |
| `PRD3002` | `C1_RAW_STORAGE > A1 > A2 > A7 > A5 > A9_1 > A3` | 39 | 26 |

최종 분석 대상:

```text
정상 route/prefix serial: 294 / 324
제외 serial: 30
```

중요한 해석:

- `A7 -> A5`는 룸미러 계열(`PRD3001`, `PRD3002`)의 정상 route다.
- `A5 -> A3` 같은 제품별 정상 route에서 벗어난 전이는 제외했다.
- 정상 route 기준을 세우지 않으면 제품군별 정상 차이와 비정상 로그가 섞여 병목 분석이 왜곡된다.

## 6. 주요 지표 계산 방식

### 처리시간

`prc_hist_tb`의 동일 제품/설비 STR, END 이벤트를 페어링해 계산했다.

```text
processing_sec = END_TIME - STR_TIME
```

### 대기시간

제품별 공정 이벤트를 시간순으로 정렬한 뒤, 현재 공정 종료와 다음 공정 시작 사이의 차이를 계산했다.

```text
waiting_sec = next_start_time - current_end_time
```

주의:

- 이 값은 물리 layout의 확정 경로가 아니라 로그상 다음 공정 이벤트 기준이다.
- 예를 들어 일부 serial에서 `A3 -> C2`가 잡히더라도, 이것은 물리적으로 AMR 없이 C2로 직행했다는 뜻이 아니다.
- 실제 흐름은 기본적으로 `A3 -> AMR_LD250 -> C2`로 해석하되, 로그상 AMR 이벤트가 누락되거나 C2 저장 이벤트가 바로 다음으로 잡힌 경우가 있다.

### WIP

버퍼와 완제품 창고 입출고 이벤트를 누적합으로 계산했다.

```text
WIP = 입고 누적 - 출고 누적
```

사용 테이블:

- `strg_buf_in`
- `strg_buf_out`
- `strg_fns_in`
- `strg_fns_out`

### 이송/레일 점유

`prc_trns_tb`에서 이송 이벤트를 분석했다.

주요 컬럼:

| 컬럼 | 의미 |
|---|---|
| `TRN_CD` | 이동 장치 코드 |
| `TRN_DEV_ID` | 이송 장치 ID |
| `MBL_NMBR` | 이송 설비 번호 |
| `PRD_WRK_CD` | 이송 작업 코드. `STR`: 출발, `ARV`: 도착 |
| `TRN_QNT` | 이송 수량 |

확인된 코드:

| `TRN_CD` | 의미 |
|---|---|
| `TR01` | `MON_TRACK` |
| `TR02` | `Omron AMR` |
| `TR03` | `KUKA AMR` |
| `TR04` | `MIR AMR` |
| `TR05` | `neuromeka AMR` |

현재 데이터에서 주로 사용된 값:

- `TR01`, `TRN_DEV_ID=1~4`: 공유 레일/이송 장치 ID로 해석
- `TR02`: AMR 관련 이송 코드로 해석

단, `TRN_DEV_ID=1,2,3,4` 각각이 실제 설비 layout에서 어느 물리 레일 구간인지는 현재 DB/문서만으로 확정할 수 없다.

### 병목 점수

병목 점수는 서로 단위가 다른 지표를 표준화한 뒤 합산했다.

```text
bottleneck_score =
  z(processing_p90_sec)
+ z(waiting_p90_sec)
+ z(wip_p90)
+ z(occupancy_p90_sec)
+ z(alarm_ratio)
```

여기서:

```text
z(x) = (x - 전체 공정 평균) / 전체 공정 표준편차
```

해석:

- 점수는 절대 점수가 아니라 상대 점수다.
- A3가 5점 만점이라는 뜻이 아니다.
- 전체 공정 대비 처리/대기/WIP/점유/alarm 중 하나 이상이 유난히 큰 공정이 높은 점수를 받는다.

## 7. 현재까지 핵심 분석 결과

### 전체 병목 순위

정상 제품/정상 route 기준 전체 공정 병목 순위 상위는 다음과 같다.

| 순위 | 공정 | 병목 점수 | 처리 p90 | 대기 p90 | WIP p90 | 점유 p90 |
|---:|---|---:|---:|---:|---:|---:|
| 1 | `A3` | 4.999 | 62.2초 | 2707.1초 | 73.1 | 2567.9초 |
| 2 | `A4` | 1.911 | 554.8초 | 78.6초 | 0.0 | 2747.2초 |
| 3 | `AMR_LD90` | 1.683 | 123.8초 | 174.2초 | 0.0 | 0.0초 |
| 4 | `A7` | 1.509 | 419.9초 | 635.7초 | 0.0 | 2420.1초 |
| 5 | `A9_1` | 1.384 | 458.4초 | 71.5초 | 0.0 | 2776.7초 |
| 6 | `A5` | 1.154 | 326.9초 | 635.7초 | 0.0 | 2680.0초 |
| 7 | `A9_2` | 1.051 | 192.9초 | 930.6초 | 0.0 | 3133.3초 |

핵심 해석:

- `A3`: 처리 자체보다 후단 반출 대기와 버퍼 WIP가 큰 병목
- `A4`: 처리시간과 점유시간이 큰 복합 CELL 병목 후보
- `A9/A7/A5/AMR`: A3/A4 주변 지연을 연결하거나 증폭시키는 후보

## 8. A3 병목 세분화

A3는 현재 데이터 기준 가장 강한 병목이다. 다만 A3 자체 처리시간이 매우 긴 것은 아니다.

| 요소 | 값 | 해석 |
|---|---:|---|
| `A3_PROCESS` | 62.2초 | A3 자체 처리 p90 |
| `AMR_DISPATCH_WAIT` | 1628.4초 | A3 이후 AMR_LD250 대기 p90 |
| `C2_STORAGE_WAIT` | 2707.1초 | A3 이후 C2 저장 대기 p90 |
| `BUFFER_ACCUMULATION` | 73.1 WIP | 버퍼 WIP p90 |
| `FINISHED_STORAGE_ACCUMULATION` | 1.0 WIP | 완제품 창고 WIP p90 |

해석:

- A3는 설비 처리 자체보다 후단 반출 대기가 핵심이다.
- A3 이후 대기는 `AMR_LD250`, `C2_FINISHED_STORAGE`, `BUFFER`와 연결된다.
- 실제 물리 흐름은 `A3 -> AMR_LD250 -> C2`로 보는 것이 맞다.
- 로그상 `A3 -> C2`가 잡히는 경우는 AMR 이벤트가 중간에 기록되지 않았거나, C2 저장 이벤트가 A3 다음 이벤트로 잡힌 경우로 해석해야 한다.

현재 데이터로 확정 가능한 것:

- A3 이후 대기시간이 A3 처리시간보다 훨씬 크다.
- BUFFER WIP가 높다.
- A3 후단 반출이 병목의 핵심 후보이다.

현재 데이터만으로 확정하기 어려운 것:

- AMR 호출/배정 지연이 원인인지
- C2 완제품 창고 slot 포화가 원인인지
- A3 출구 스토퍼/적재부 capacity가 원인인지

## 9. A4 공유 레일 Blocking 분석

A4는 매뉴얼상 단순 공정이 아니라 복합 CELL이다.

매뉴얼 기반 의미:

- 사상 제거
- 레이저 마킹
- 산업용 로봇
- 협동로봇
- 툴체인저
- 틸팅 유닛
- 3개 파렛트 버퍼

따라서 A4 처리시간이 긴 것은 단순 지연일 수도 있지만, 구조적으로 공정 부하가 큰 결과일 수도 있다.

현재 A4 분석 결과:

| 지표 | 값 |
|---|---:|
| A4 long window 기준 | 686.9초 |
| A4 long window 수 | 38개 |
| long/normal 다른 제품군 overlap 비율 | 133.79 |
| blocking 가설 근거 강도 | Strong |

용어:

- `family`: 제품군. `HANDLE`은 `PRD1000/PRD2000`, `ROOM_MIRROR`는 `PRD3001/PRD3002`
- `overlap`: A4 처리 window와 같은 시간대에 발생한 rail event
- `same family rail events`: A4에 있던 제품과 같은 제품군의 레일 이벤트
- `other family rail events`: A4에 있던 제품과 다른 제품군의 레일 이벤트

현재 해석:

- A4 long window 중 공유 이송 이벤트가 시간상 겹친다.
- A4가 오래 걸리는 동안 다른 제품군 rail event도 같이 발생한다.
- 따라서 A4는 공유 레일 blocking 후보로 볼 수 있다.

주의:

- 시간상 overlap은 “실제 물리 blocking 확정”과 다르다.
- `TRN_DEV_ID=1~4` 각각의 물리 위치가 없으므로 어느 레일 구간을 실제로 막았는지는 확정할 수 없다.

## 10. 제품군별 병목 분리

제품군별 route가 다르므로 병목도 제품군별로 나눠야 한다.

제품군:

| 제품군 | 제품 |
|---|---|
| `HANDLE` | `PRD1000`, `PRD2000` |
| `ROOM_MIRROR` | `PRD3001`, `PRD3002` |

현재 제품군별 상위 병목 후보:

| 제품군 | 상위 병목 후보 |
|---|---|
| `HANDLE` | `A3`, `A4`, `A9_2` |
| `ROOM_MIRROR` | `A3`, `A7`, `A9_1` |

해석:

- A3는 두 제품군 모두에서 공통 병목이다.
- 핸들 계열은 A4와 A9_2가 중요하다.
- 룸미러 계열은 A7, A5, A9_1 흐름이 중요하다.
- 스케줄링 규칙도 제품군별로 분리해야 한다.

예시:

- 핸들 계열: A4 진입 제어, A4 주변 WIP cap, A9_2 후단 흐름 관리
- 룸미러 계열: A7 -> A5 -> A9_1 흐름의 대기 완화
- 공통: A3 후단 반출 우선순위

## 11. 레일/AMR 이송 자원 분석

레일/AMR은 특정 제품군만 쓰는 자원이 아니라 모든 제품군이 공유하는 이송 자원이다. 따라서 설비 처리시간이 짧더라도 이송 자원이 막히면 공정 간 대기가 길어질 수 있다.

### TRN_DEV_ID 사용 현황

`TR01`은 `MON_TRACK`으로 확인되며, 현재 데이터에서는 `TRN_DEV_ID=1~4`가 사용된다.

| TRN_DEV_ID | active bucket ratio |
|---:|---:|
| 1 | 0.687 |
| 2 | 0.688 |
| 3 | 0.665 |
| 4 | 0.608 |

해석:

- `TRN_DEV_ID=1~4` 모두 활발하게 사용된다.
- `1~3`은 특히 사용 비율이 높다.
- 하지만 active bucket ratio는 “이벤트 발생 비율”이지 “정체 확정”이 아니다.
- 어느 ID가 실제 어느 물리 위치인지 알아야 병목 위치를 확정할 수 있다.

### AMR_LD90 / AMR_LD250

| 자원 | 해석 |
|---|---|
| `AMR_LD90` | 주로 원자재/초기 투입 쪽 이송 자원으로 해석 |
| `AMR_LD250` | 후단 완제품 반출 쪽 이송 자원으로 해석 |

현재 판단:

- `AMR_LD250`은 A3 후단 반출 대기와 연결된다.
- 다만 AMR 호출 시각, 배정 시각, 취소/대기 상태 로그가 없어 AMR 자체가 원인인지 C2 포화로 AMR이 대기한 것인지 확정할 수 없다.

## 12. 매뉴얼 기반 공정 의미 해석

분석은 숫자만 보지 않고 매뉴얼의 설비 구조도 함께 반영했다.

### A3

의미:

- 완제품/NG 분류
- 협동로봇 이송
- 2단 적재 대기
- IN/OUT 컨베이어
- 스토퍼 기반 1개씩 배출 구조

해석:

- A3는 단순 처리 공정이 아니라 후단 반출의 입구다.
- 처리시간보다 배출/반출/저장 대기가 병목으로 나타날 수 있다.

### A4

의미:

- 사상 제거
- 레이저 마킹
- 다중 로봇
- 툴체인저
- 틸팅 유닛
- 3개 파렛트 버퍼

해석:

- A4는 복합 CELL이므로 처리시간 자체가 구조적으로 길 수 있다.
- 제품 혼합, 툴체인지, 버퍼 점유, 레일 공유가 병목 요인이 될 수 있다.

### A9

의미:

- 코어 검사
- 비전 검사
- 조립 검사
- 볼트 공급/체결
- 툴체인저와 팔레트 대기/버퍼

해석:

- A9는 후단 검사/조립 공정이다.
- A3 반출 흐름과 연결된 후단 병목 후보로 본다.

### C2 / EQ15

의미:

- 완제품 창고
- 제품별 그립툴
- 산업용 로봇 분류 적재
- 룸미러/핸들 적재 공간

해석:

- C2는 A3 이후 최종 저장 흐름과 연결된다.
- C2 slot capacity와 포화 상태 로그가 있어야 저장 병목 여부를 확정할 수 있다.

## 13. 현재까지의 PPT 자료

최종 발표용 PPT:

```text
outputs/2026_06_14/PZONE_bottleneck_phase1_5_summary_7slides.pptx
```

구성:

1. 분석 목적과 현재 완료 범위
2. 데이터 검증과 정상 route 기준
3. 전체 병목 스크리닝 결과
4. A3 병목 세분화
5. A4 공유 레일 blocking 검증
6. 제품군별 병목 + 레일/AMR 자원 분석
7. 현재 결론과 개선 단계 진입 조건

대본:

```text
outputs/2026_06_14/PZONE_bottleneck_phase1_5_ppt_script.md
outputs/2026_06_14/PZONE_bottleneck_phase1_5_ppt_script_1min.md
```

PPT에는 슬라이드별 발표자 메모도 포함되어 있다.

## 14. 현재 데이터로 확정할 수 없는 정보

아래 정보는 현재 DB/CSV/문서만으로 확정할 수 없다.

| 필요한 정보 | 필요한 이유 |
|---|---|
| `TRN_DEV_ID=1~4`의 실제 물리 위치/구간 | A4가 실제 어느 레일 구간을 막는지 확정하기 위해 필요 |
| AMR 호출/배정/취소/대기 상태 로그 | AMR 배정 지연인지 C2 포화로 인한 대기인지 분리하기 위해 필요 |
| C2 완제품 창고 slot capacity와 포화 상태 | A3 후단 병목이 C2 저장 공간 문제인지 확인하기 위해 필요 |
| OEE `IDLE`의 정확한 의미 | 정상 대기인지 설비 비가동인지 구분하기 위해 필요 |
| 버퍼/스토퍼별 실제 capacity와 blocked 상태 | A3/A4 주변 WIP와 blocking 원인을 확정하기 위해 필요 |

이 정보가 없을 때는 아래처럼 표현해야 한다.

```text
가능한 표현:
- A4는 공유 레일 blocking 후보다.
- A3 후단 반출 대기가 크다.
- AMR/C2/BUFFER가 A3 병목과 연결된다.

피해야 할 표현:
- A4가 특정 레일 구간을 실제로 막았다.
- AMR 배정 지연이 원인이다.
- C2 창고 포화가 원인이다.
```

## 15. 앞으로 해야 할 일

### 15.1 분석 고도화

1. A3 병목 세분화 강화
   - A3 자체 문제인지, AMR_LD250 배정 문제인지, C2 적재 문제인지 분리
   - A3 후단 반출 우선순위 규칙 설계
   - AMR dispatch 로그 확보 시 A3 -> AMR 호출 대기, AMR 이동, C2 적재 대기 구간을 분리

2. A4 공유 레일 blocking 검증 강화
   - A4 long window와 normal window 대조군 비교
   - A4 지연이 다른 제품군 대기 증가와 실제로 연결되는지 검증
   - `TRN_DEV_ID=1~4` 물리 위치 매핑 후 구간별 blocking 분석

3. 제품군별 병목 분리
   - 핸들 계열 `PRD1000/PRD2000`
   - 룸미러 계열 `PRD3001/PRD3002`
   - 제품군별 병목 순위와 스케줄링 액션 분리

4. 레일/AMR 해석 정교화
   - 레일별 동시 사용률, idle rail 여부 계산
   - AMR_LD90과 AMR_LD250 역할 분리
   - AMR 사용 가능 상태와 호출 대기 상태 분리

### 15.2 개선안 설계

다음 단계는 rule-based scheduling baseline 설계다.

후보 규칙:

| 상황 | 액션 |
|---|---|
| A3 WIP가 높음 | `PRIORITIZE_DISCHARGE` |
| AMR_LD250 사용 가능 | `DISPATCH_AMR` |
| A4 주변 WIP가 높음 | `CONTROL_WIP` |
| 레일 혼잡도 높음 | `SCHEDULE_RAIL` |
| A4/C2 포화 가능성 높음 | `HOLD_ENTRY` |
| 물리 제약이 강함 | `REQUIRE_PHYSICAL_CHANGE` |

### 15.3 효과 검증

rule-based baseline을 만든 뒤 기존 로그로 리플레이 또는 시뮬레이션을 수행한다.

검증 지표:

- 전체 throughput
- 제품군별 throughput
- A3 후단 대기 p90
- A4 처리/대기 p90
- BUFFER WIP p90
- AMR 대기 p90
- 레일 active bucket ratio
- 제품군별 공정 간 대기 p90

비교 시나리오:

1. 현재 로그 기준 baseline
2. A3 우선 반출 규칙 적용
3. A4 WIP cap 적용
4. 레일 혼잡 시 진입 hold 적용
5. 제품군별 우선순위 적용

### 15.4 LLM-assisted Decision Agent 설계

rule-based baseline이 정리된 뒤 LLM agent를 설계한다.

필요 구성:

1. 입력 state 정의
   - 공정별 WIP
   - 제품군
   - 현재 대기시간
   - AMR 상태
   - 레일 상태
   - A3/A4 주변 queue

2. 출력 JSON schema 정의
   - action
   - target equipment
   - target product/serial
   - priority
   - reason
   - expected effect

3. constraint verifier 정의
   - 정상 route 위반 금지
   - AMR 중복 배정 금지
   - 설비 capacity 초과 금지
   - 물리적으로 불가능한 이동 금지

4. 평가
   - rule-based baseline과 비교
   - 대기시간/WIP/throughput 개선율 비교
   - 불가능한 action 발생률 측정

## 16. 다음 담당자가 가장 먼저 해야 할 일

우선순위는 아래 순서가 좋다.

1. `outputs/2026_06_14/PZONE_bottleneck_phase1_5_summary_7slides.pptx`를 열어 전체 결론을 확인한다.
2. `outputs/2026_06_14/PZONE_bottleneck_phase1_5_ppt_script_1min.md`를 읽어 발표용 요약 흐름을 이해한다.
3. `outputs/2026_06_14/phase_1_to_5_analysis/required_field_gap_report.md`를 확인해 현장에 요청할 정보를 정리한다.
4. 현장 담당자에게 `TRN_DEV_ID=1~4` 물리 위치, AMR dispatch 로그, C2 slot capacity 정보를 요청한다.
5. 정보가 확보되면 A3와 A4 분석을 재실행/보강한다.
6. 그 다음 rule-based scheduling baseline 설계로 넘어간다.

## 17. 주의사항

- 현재 분석은 실제 설비 제어가 아니라 로그 기반 병목 진단이다.
- `A3 -> C2` 전이를 물리적 직행으로 해석하지 말아야 한다.
- `A7 -> A5`는 룸미러 계열 정상 route다.
- `TRN_DEV_ID=1~4`는 이송 장치 ID이지, 현재 문서만으로 물리 구간명이 아니다.
- A4 blocking은 강한 후보지만 확정 원인은 아니다.
- AMR 지연과 C2 포화는 현재 데이터만으로 분리 확정할 수 없다.
- 병목 점수는 상대 점수이며 절대 성능 점수가 아니다.

## 18. 한 줄 요약

현재까지의 결론은 다음과 같다.

```text
P-ZONE 병목은 A3 후단 반출에서 가장 강하게 나타나고,
A4는 복합 CELL 처리시간과 공유 레일 overlap 때문에 blocking 후보로 보인다.
제품군별 route 차이가 크므로 핸들/룸미러를 분리해 분석해야 하며,
다음 단계는 현장 매핑 정보를 보강한 뒤 rule-based scheduling baseline을 설계하는 것이다.
```
