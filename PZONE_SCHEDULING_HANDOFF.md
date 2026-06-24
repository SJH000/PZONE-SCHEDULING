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

현재까지는 **1~7번 단계**를 완료했다. 1~5번은 로그 기반 병목 분석/진단이고, 6~7번은 현장 추가정보 없이 가능한 범위의 rule-based scheduling baseline과 로그 리플레이/가정 기반 시뮬레이션 평가다. 다음 단계는 **8번 LLM-assisted decision agent 설계**다.

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
| `build_rule_based_baseline.py` | 6번 rule-based scheduling baseline 생성, 5분 bucket state/action log/proxy 검증 산출 |
| `build_rule_replay_simulation.py` | 7번 rule replay와 counterfactual simulation 평가 산출 |
| `build_rule_progress_ppt.py` | 6~7번 진행 공유용 7장 PPT와 슬라이드별 발표 대본 생성 |
| `requirements.txt` | Python 의존성 |

### 재현 명령

처음부터 다시 생성할 때는 아래 순서로 실행한다.

```powershell
pip install -r requirements.txt
python run_pzone_analysis.py
python build_2026_06_14_package.py
python build_phase_1_to_5_analysis.py
python build_rule_based_baseline.py
python build_rule_replay_simulation.py
python build_rule_progress_ppt.py
```

초기 버전 PPT만 다시 만들고 싶다면:

```powershell
python build_pzone_ppt.py
```

1~5번 요약 PPT는 `build_phase_1_to_5_analysis.py`에서 생성된다. 6~7번 진행 공유 PPT는 `build_rule_progress_ppt.py`에서 생성된다.

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

### 6번 Rule Baseline 산출물

```text
outputs/2026_06_14/rule_baseline/
```

주요 파일:

| 파일 | 설명 |
|---|---|
| `rule_baseline_report.md` | rule-based baseline 설계, trigger 결과, 한계 정리 |
| `data/state_5min.csv` | 5분 bucket 단위 운영 state |
| `data/actions.csv` | rule 적용 결과 action log |
| `data/rule_trigger_counts.csv` | action별 trigger 횟수 |
| `data/rule_effect_proxy.csv` | rule이 병목 구간을 얼마나 감지했는지에 대한 proxy 검증 |
| `data/rule_thresholds.csv` | rule threshold와 기준값 |
| `figures/*.png` | trigger count, timeline, A3/A4/Rail rule 비교 그래프 |

6번 결과는 실제 제어 효과가 아니라, 기존 로그에서 병목 상황을 감지해 어떤 action 후보를 낼 수 있는지 확인한 것이다.

### 7번 Replay / Simulation 산출물

```text
outputs/2026_06_14/rule_replay/
outputs/2026_06_14/rule_simulation/
```

주요 파일:

| 파일 | 설명 |
|---|---|
| `rule_replay/rule_replay_report.md` | action 발생 전후 60분 비교 결과 |
| `rule_replay/data/replay_before_after.csv` | action trigger별 before/after metric |
| `rule_replay/data/replay_effect_summary.csv` | action별 평균 before/after/delta 요약 |
| `rule_replay/data/replay_action_quality.csv` | action별 개선/악화/관찰불가 품질 분류 |
| `rule_simulation/rule_simulation_report.md` | 10%, 20%, 30% 완화 가정 기반 counterfactual 평가 |
| `rule_simulation/data/counterfactual_scenarios.csv` | action별 가정 시나리오 결과 |
| `rule_simulation/data/simulation_effect_summary.csv` | 시나리오별 기대 감소량 요약 |
| `rule_replay/figures/*.png` | replay 평가 그래프 |
| `rule_simulation/figures/*.png` | counterfactual simulation 그래프 |

6~7번 진행 공유 PPT:

| 파일 | 설명 |
|---|---|
| `outputs/2026_06_14/PZONE_rule_baseline_replay_7slides.pptx` | 6~7번 진행 공유용 7장 PPT, 발표자 메모 포함 |
| `outputs/2026_06_14/PZONE_rule_baseline_replay_ppt_script_1min.md` | 각 슬라이드 1분용 대본 |

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

현재 6번 rule-based baseline과 7번 replay/simulation은 완료되어 있다. 따라서 다음 핵심 작업은 **8번 LLM-assisted Decision Agent 설계**다. 단, 바로 fine-tuning부터 시작하지 않는다. 먼저 LLM agent 구조를 구현하고, 현재 rule baseline과 같은 로그 replay/simulation 방식으로 비교한 뒤 학습 여부를 판단한다.

### 15.1 왜 바로 학습하지 않는가

현재 데이터는 실제 설비 제어 결과가 아니라 과거 로그다. 따라서 어떤 action을 냈을 때 실제 현장이 얼마나 개선되는지에 대한 정답 label이 없다. 이 상태에서 바로 학습하면 모델은 실제 최적 행동을 배우는 것이 아니라, 사람이 만든 rule이나 과거 로그 패턴을 흉내 낼 가능성이 높다.

현실적인 순서는 다음과 같다.

```text
1. rule-based baseline 완료
2. LLM decision agent 구조 구현
3. prompt 기반 zero-shot / few-shot action 생성
4. constraint verifier로 출력 검증
5. rule baseline과 동일한 replay/simulation 평가
6. 실패 케이스와 성공 케이스 수집
7. 필요할 때 학습 데이터셋 생성
8. fine-tuning 또는 preference tuning 검토
```

### 15.2 LLM Agent 입력 State

입력은 6번에서 만든 `state_5min.csv`를 기본으로 사용한다. LLM에 모든 raw log를 직접 넣지 않고, 5분 bucket 단위의 요약 state를 넣는다.

필수 입력 예시:

```json
{
  "bucket_5min": "2026-...",
  "buffer_wip": 82,
  "finished_storage_wip": 14,
  "a3_completed_count": 3,
  "a3_to_amr_wait_p90_recent": 1450,
  "a3_to_c2_wait_p90_recent": 2100,
  "a4_active_count": 1,
  "a4_long_count": 1,
  "rail_event_count": 620,
  "active_rail_count": 4,
  "handle_rail_events": 310,
  "room_mirror_rail_events": 280,
  "dominant_product_family": "HANDLE"
}
```

입력에 포함해야 하는 보조 정보:

- 허용 action 목록
- action별 의미
- 현재 데이터 한계
- 정상 route 기준
- 제품군 정의
- 병목 판단 기준
- 출력 JSON schema

### 15.3 LLM Agent 출력 Schema

LLM 출력은 자유 문장이 아니라 검증 가능한 JSON으로 제한한다.

권장 출력 schema:

```json
{
  "bucket_5min": "string",
  "action": "PRIORITIZE_DISCHARGE | DISPATCH_AMR | CONTROL_WIP | SCHEDULE_RAIL | HOLD_ENTRY | NO_ACTION",
  "target_process": "A3 | A4 | C2 | BUFFER | TR01 | AMR_LD250 | NONE",
  "target_resource": "string",
  "product_family_context": "HANDLE | ROOM_MIRROR | MIXED | UNKNOWN",
  "priority": "High | Medium | Low",
  "confidence": "High | Medium | Low",
  "reason": "string",
  "expected_effect": "string",
  "known_limitations": ["string"]
}
```

주의할 점:

- `AMR availability`, `C2 capacity`, `TRN_DEV_ID` 물리 위치는 현재 데이터에 없으므로 확정 표현하면 안 된다.
- LLM은 “가능성이 있다”, “우선 검증해야 한다” 수준으로 표현해야 한다.
- action은 기존 rule baseline의 action set과 맞춰야 replay/simulation 비교가 가능하다.

### 15.4 Constraint Verifier

LLM 출력 뒤에는 반드시 검증기를 둔다. 이 검증기는 LLM이 그럴듯하지만 불가능한 action을 내는 것을 막는 역할을 한다.

검증 항목:

| 검증 항목 | 설명 |
|---|---|
| action whitelist | 허용된 action인지 확인 |
| target validation | target process/resource가 실제 분석 범위에 있는지 확인 |
| confidence validation | 데이터 한계가 큰 action은 `High` confidence를 금지 |
| missing-field guard | AMR availability, C2 capacity 등 없는 정보를 확정 근거로 쓰지 못하게 함 |
| conflict check | 같은 bucket에서 `HOLD_ENTRY`와 무리한 반출 action이 충돌하지 않는지 확인 |
| route guard | 정상 route를 위반하는 제품 이동 지시를 생성하지 않도록 제한 |
| output schema check | JSON schema를 통과하지 못하면 action을 폐기하거나 `NO_ACTION` 처리 |

Verifier 결과는 별도 컬럼으로 남긴다.

```text
llm_action_raw.csv
llm_action_verified.csv
llm_action_rejected.csv
```

### 15.5 학습 데이터셋은 언제, 어떻게 만들 것인가

초기에는 학습하지 않고 prompt 기반으로 테스트한다. 학습은 아래 조건이 충족될 때 검토한다.

- LLM이 rule baseline보다 나은 판단을 하는 bucket이 일부 확인됨
- LLM이 반복적으로 틀리는 failure pattern이 수집됨
- 사람 또는 도메인 전문가가 일부 action label을 검수할 수 있음
- replay/simulation 평가에서 action 품질을 비교할 수 있음

학습 데이터셋 후보:

| 필드 | 내용 |
|---|---|
| input | 5분 bucket state, 최근 60분 rolling metric, 제품군 context |
| weak_label | rule baseline이 낸 action |
| llm_action | prompt 기반 LLM이 낸 action |
| verified_action | constraint verifier 통과 후 action |
| outcome_proxy | replay/simulation 기반 개선/악화 proxy |
| human_label | 사람이 수정하거나 승인한 action |
| rationale | action 선택 이유 |

초기 데이터셋은 `actions.csv`를 weak label로 사용할 수 있다. 다만 이것만으로 학습하면 rule을 복제하는 모델이 되므로, 반드시 rule 실패 케이스, LLM 대안 케이스, 사람 검수 label을 추가해야 한다.

### 15.6 8번 구현 산출물 제안

다음 구현에서는 아래 폴더를 새로 만든다.

```text
outputs/2026_06_14/llm_agent/
```

권장 산출물:

| 파일 | 설명 |
|---|---|
| `data/llm_input_states.csv` | LLM에 넣을 5분 bucket state |
| `data/llm_prompts.jsonl` | bucket별 prompt |
| `data/llm_actions_raw.jsonl` | LLM 원본 출력 |
| `data/llm_actions_verified.csv` | verifier 통과 후 action |
| `data/llm_actions_rejected.csv` | 폐기된 action과 사유 |
| `data/llm_vs_rule_comparison.csv` | LLM action과 rule baseline action 비교 |
| `data/llm_replay_effect_summary.csv` | LLM action replay 평가 요약 |
| `llm_agent_design.md` | agent 구조, prompt, schema, verifier 설계 문서 |
| `llm_agent_evaluation_report.md` | rule baseline 대비 평가 결과 |
| `figures/*.png` | LLM vs Rule action count, agreement rate, replay metric 그래프 |

### 15.7 8번 평가 기준

LLM agent가 의미 있는지 판단하려면 다음을 본다.

- rule baseline과 action이 얼마나 일치하는가
- rule baseline과 다르게 판단한 bucket에서 이유가 타당한가
- verifier rejection rate가 너무 높지 않은가
- `PRIORITIZE_DISCHARGE`, `CONTROL_WIP`, `SCHEDULE_RAIL` 같은 주요 action을 데이터 상황에 맞게 내는가
- replay/simulation proxy에서 rule 대비 악화되지 않는가
- 없는 정보를 근거로 확정 표현하지 않는가

1차 성공 기준:

```text
- JSON schema 통과율 95% 이상
- verifier rejection rate 10~20% 이하
- rule baseline과 주요 병목 bucket에서 큰 충돌 없음
- LLM이 rule과 다른 action을 낸 경우 사람이 읽을 수 있는 타당한 reason 제공
- replay/simulation proxy가 rule baseline보다 명확히 나쁘지 않음
```

### 15.8 이후 학습 방향

LLM 구조 평가 후 학습을 진행한다면 세 가지 방향이 있다.

1. **Fine-tuning**
   - 목적: state를 보고 안정적으로 action JSON을 생성
   - 데이터: 검수된 `state -> verified_action` 쌍
   - 한계: 실제 최적 제어 label이 없으면 rule 복제에 가까워질 수 있음

2. **Preference tuning**
   - 목적: 같은 state에서 더 나은 action/rationale을 선호하도록 학습
   - 데이터: `(state, action A, action B, preferred)` 형태
   - 장점: rule action과 LLM 대안 action을 비교하기 좋음

3. **학습 없이 prompt + verifier 유지**
   - 목적: 데이터가 부족할 때 가장 안전한 운영 방식
   - 장점: 근거 수정, rule 변경, 제약 추가가 쉬움
   - 현재 프로젝트에는 이 방식이 가장 현실적인 1차안이다.

## 16. 다음 담당자가 가장 먼저 해야 할 일

우선순위는 아래 순서가 좋다.

1. `outputs/2026_06_14/PZONE_bottleneck_phase1_5_summary_7slides.pptx`를 열어 1~5번 병목 분석 결론을 확인한다.
2. `outputs/2026_06_14/PZONE_rule_baseline_replay_7slides.pptx`를 열어 6~7번 rule baseline/replay/simulation 결과를 확인한다.
3. `outputs/2026_06_14/rule_baseline/rule_baseline_report.md`를 읽어 rule trigger 기준과 action log 생성 방식을 확인한다.
4. `outputs/2026_06_14/rule_replay/rule_replay_report.md`와 `outputs/2026_06_14/rule_simulation/rule_simulation_report.md`를 읽어 rule 효과 가능성과 한계를 확인한다.
5. 8번 LLM agent 구현 시 `state_5min.csv`를 입력으로, `actions.csv`를 rule baseline 비교 대상으로 사용한다.
6. 먼저 prompt 기반 agent와 constraint verifier를 구현하고, 그 뒤에 학습 데이터셋 생성 여부를 판단한다.

## 17. 주의사항

- 현재 분석은 실제 설비 제어가 아니라 로그 기반 병목 진단과 오프라인 rule 평가다.
- 6~7번 결과는 실제 개선 효과 확정이 아니라 “rule 후보가 병목 상황을 감지하는지”와 “가정 기반 효과 가능성”을 본 것이다.
- `A3 -> C2` 전이를 물리적 직행으로 해석하지 말아야 한다.
- `A7 -> A5`는 룸미러 계열 정상 route다.
- `TRN_DEV_ID=1~4`는 이송 장치 ID이지, 현재 문서만으로 물리 구간명이 아니다.
- A4 blocking은 강한 후보지만 확정 원인은 아니다.
- AMR 지연과 C2 포화는 현재 데이터만으로 분리 확정할 수 없다.
- LLM agent는 현재 데이터에 없는 AMR availability, C2 slot capacity, rail physical segment를 확정 근거로 쓰면 안 된다.
- 병목 점수와 replay/simulation 결과는 상대 비교 및 proxy 평가이며 절대 성능 점수가 아니다.

## 18. 한 줄 요약

현재까지의 결론은 다음과 같다.

```text
P-ZONE 병목은 A3 후단 반출에서 가장 강하게 나타나고,
A4는 복합 CELL 처리시간과 공유 레일 overlap 때문에 blocking 후보로 보인다.
제품군별 route 차이가 크므로 핸들/룸미러를 분리해 분석해야 하며,
현재는 rule-based baseline과 replay/simulation 평가까지 완료했다.
다음 단계는 학습부터 시작하지 않고 LLM decision agent 구조와 constraint verifier를 먼저 구현한 뒤,
rule baseline과 같은 오프라인 평가 방식으로 비교하고 학습 필요성을 판단하는 것이다.
```
