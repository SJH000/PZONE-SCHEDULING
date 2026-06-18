from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
OUT_ROOT = ROOT / "outputs"
SRC_DATA = OUT_ROOT / "data"
SRC_REPORT = OUT_ROOT / "report"
SRC_FIGURES = SRC_REPORT / "figures"
PKG = OUT_ROOT / "2026_06_14"


DATA_FILES = [
    "normal_route_summary.csv",
    "excluded_route_summary.csv",
    "bottleneck_ranking.csv",
    "schedulability_classification.csv",
    "equipment_processing_time_summary.csv",
    "transition_waiting_time.csv",
    "wip_summary.csv",
    "occupancy_summary.csv",
    "rail_timeseries.csv",
    "a4_blocking_windows.csv",
    "cross_product_delay_matrix.csv",
    "a4_downstream_lag.csv",
    "oee_summary.csv",
    "sql_extract_summary.csv",
]

FIGURE_MAP = {
    "bottleneck_ranking.png": "01_bottleneck_ranking.png",
    "processing_p90_top.png": "02_processing_p90_top.png",
    "waiting_p90_top.png": "03_waiting_p90_top.png",
    "rail_occupancy_timeseries.png": "04_rail_occupancy_timeseries.png",
    "a4_processing_vs_rail_occupancy.png": "05_a4_processing_vs_rail_occupancy.png",
    "a4_blocking_overlap_by_product_family.png": "06_a4_blocking_overlap_by_product_family.png",
    "a4_downstream_lag_effect.png": "07_a4_downstream_lag_effect.png",
}


def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(SRC_DATA / name)


def fmt_num(value, digits: int = 1) -> str:
    if pd.isna(value):
        return "-"
    try:
        return f"{float(value):,.{digits}f}"
    except Exception:
        return str(value)


def md_table(df: pd.DataFrame, n: int | None = None, cols: list[str] | None = None) -> str:
    if df.empty:
        return "_No data._"
    if cols:
        df = df[cols]
    if n is not None:
        df = df.head(n)
    return df.to_markdown(index=False)


def ensure_package_dirs() -> None:
    for sub in ["data", "figures", "tables"]:
        (PKG / sub).mkdir(parents=True, exist_ok=True)


def copy_assets() -> None:
    ensure_package_dirs()
    for name in DATA_FILES:
        src = SRC_DATA / name
        if src.exists():
            shutil.copy2(src, PKG / "data" / name)
    for src_name, dst_name in FIGURE_MAP.items():
        src = SRC_FIGURES / src_name
        if src.exists():
            shutil.copy2(src, PKG / "figures" / dst_name)
    for report_name in ["PZONE_bottleneck_analysis_report.md", "PZONE_process_semantics.md", "PZONE_analysis_summary.xlsx"]:
        src = SRC_REPORT / report_name
        if src.exists():
            shutil.copy2(src, PKG / report_name)


def build_context() -> dict:
    bottleneck = read_csv("bottleneck_ranking.csv")
    sched = read_csv("schedulability_classification.csv")
    routes = read_csv("normal_route_summary.csv")
    excluded = read_csv("excluded_route_summary.csv")
    proc = read_csv("equipment_processing_time_summary.csv")
    waits = read_csv("transition_waiting_time.csv")
    wip = read_csv("wip_summary.csv")
    a4_windows = read_csv("a4_blocking_windows.csv")
    cross = read_csv("cross_product_delay_matrix.csv")
    lag = read_csv("a4_downstream_lag.csv")
    extract = read_csv("sql_extract_summary.csv")

    top = bottleneck.iloc[0].to_dict() if not bottleneck.empty else {}
    a3 = bottleneck[bottleneck["process"] == "A3"].iloc[0].to_dict()
    a4 = bottleneck[bottleneck["process"] == "A4"].iloc[0].to_dict()
    a4_proc = proc[proc["logical_process"] == "A4"].iloc[0].to_dict()
    a3_wait_amr = waits[waits["transition"] == "A3->AMR_LD250"]
    a3_wait_c2 = waits[waits["transition"] == "A3->C2_FINISHED_STORAGE"]
    a3_wait_amr_row = a3_wait_amr.iloc[0].to_dict() if not a3_wait_amr.empty else {}
    a3_wait_c2_row = a3_wait_c2.iloc[0].to_dict() if not a3_wait_c2.empty else {}
    buffer = wip[wip["area"] == "BUFFER"].iloc[0].to_dict() if not wip[wip["area"] == "BUFFER"].empty else {}

    route_total = int(routes["serial_count_total"].sum()) if "serial_count_total" in routes else 0
    route_kept = int(routes["normal_serial_count"].sum()) if "normal_serial_count" in routes else 0
    route_excluded = int(excluded["PRD_SRL_NO"].nunique()) if not excluded.empty else 0

    return {
        "bottleneck": bottleneck,
        "sched": sched,
        "routes": routes,
        "excluded": excluded,
        "proc": proc,
        "waits": waits,
        "wip": wip,
        "a4_windows": a4_windows,
        "cross": cross,
        "lag": lag,
        "extract": extract,
        "top": top,
        "a3": a3,
        "a4": a4,
        "a4_proc": a4_proc,
        "a3_wait_amr": a3_wait_amr_row,
        "a3_wait_c2": a3_wait_c2_row,
        "buffer": buffer,
        "route_total": route_total,
        "route_kept": route_kept,
        "route_excluded": route_excluded,
    }


def write(path: str, content: str) -> None:
    (PKG / path).write_text(content.strip() + "\n", encoding="utf-8")


def write_tables(ctx: dict) -> None:
    tables = {
        "bottleneck_top10.md": md_table(
            ctx["bottleneck"],
            10,
            ["rank", "process", "bottleneck_score", "processing_p90_sec", "waiting_p90_sec", "wip_p90", "occupancy_p90_sec"],
        ),
        "schedulability.md": md_table(
            ctx["sched"],
            17,
            ["rank", "process", "schedulability", "recommended_action", "judgement_reason"],
        ),
        "normal_routes.md": md_table(
            ctx["routes"],
            None,
            ["PRD_CD", "normal_route", "normal_serial_count", "serial_count_total", "normal_serial_ratio"],
        ),
        "transition_waiting_top.md": md_table(
            ctx["waits"],
            15,
            ["transition", "count", "count_clean", "p90_wait_sec_clean", "max_wait_sec_clean", "outlier_count"],
        ),
        "processing_top.md": md_table(
            ctx["proc"],
            15,
            ["logical_process", "equipment_name", "count_clean", "p90_sec_clean", "max_sec_clean", "outlier_count"],
        ),
    }
    for name, table in tables.items():
        (PKG / "tables" / name).write_text(table + "\n", encoding="utf-8")


def doc_readme(ctx: dict) -> str:
    return f"""
# P-ZONE 분석 패키지: 2026_06_14

이 폴더는 P-ZONE 전체 공정 병목 분석 결과를 발표/보고서/PPT 제작용으로 다시 정리한 패키지입니다.

## 읽는 순서
1. `00_executive_summary.md`: 핵심 결론만 빠르게 확인
2. `01_analysis_flow.md`: 처음부터 끝까지 어떤 방식으로 분석했는지 확인
3. `04_all_process_screening.md`: 모든 공정을 같은 기준으로 비교한 결과 확인
4. `05_key_bottleneck_deep_dive.md`: A3, A4, A9, A7/A5, AMR/레일 심층 해석
5. `06_shared_rail_blocking.md`: A4와 공유 레일 blocking 가능성 확인
6. `07_schedulability_and_actions.md`: 스케줄링 가능성 및 추천 액션 확인
7. `09_ppt_briefing_for_gpt.md`: PPT 생성을 위해 GPT에게 줄 수 있는 브리핑

## 핵심 결론
- 정상 route 기준 분석 대상 serial: `{ctx['route_kept']}` / `{ctx['route_total']}`
- 제외 serial: `{ctx['route_excluded']}`
- 최상위 병목: `{ctx['top'].get('process', '-')}`
- 현재 결론: A3는 후단 배출/AMR/C2 병목, A4는 복합 CELL 및 공유 레일 blocking 후보, A9/A7/A5/AMR은 연결 병목 후보

## 폴더 구조
- `data/`: 분석 근거 CSV
- `figures/`: 발표용 핵심 그래프
- `tables/`: Markdown 표
- `*.md`: 설명 문서
"""


def doc_exec(ctx: dict) -> str:
    return f"""
# 00. Executive Summary

## 한 문장 결론
P-ZONE 전체 공정을 정상 제품/정상 route 기준으로 분석한 결과, **A3 후단 배출 흐름이 가장 강한 운영 병목**이고, **A4는 처리시간이 긴 복합 CELL이자 공유 레일 blocking 후보**로 나타났다.

## 핵심 수치
- 분석 대상 정상 serial: `{ctx['route_kept']}` / `{ctx['route_total']}`
- 전체 병목 1위: `{ctx['top'].get('process', '-')}`, score `{fmt_num(ctx['top'].get('bottleneck_score'), 3)}`
- A3 대기 p90: `{fmt_num(ctx['a3'].get('waiting_p90_sec'), 1)}초`
- A3 WIP p90: `{fmt_num(ctx['a3'].get('wip_p90'), 1)}`
- A4 처리시간 p90: `{fmt_num(ctx['a4_proc'].get('p90_sec_clean'), 1)}초`
- A4 long window 수: `{len(ctx['a4_windows'])}`

## 병목 우선순위
{md_table(ctx['bottleneck'], 10, ['rank', 'process', 'bottleneck_score', 'processing_p90_sec', 'waiting_p90_sec', 'wip_p90', 'occupancy_p90_sec'])}

## 해석
- A3는 처리시간 자체는 짧지만 A3 이후 AMR/C2 반출 대기와 버퍼 WIP가 커서 병목 점수가 높다.
- A4는 처리시간 p90이 가장 크며, 매뉴얼상 사상/마킹/로봇/툴체인저/틸팅/버퍼가 결합된 복합 CELL이다.
- A4 장시간 처리 구간 중 공유 레일 이벤트와 다른 제품군 이벤트가 겹치는 구간이 있어, 공유 레일 blocking 가능성을 추가 검증해야 한다.
- A9, A7, A5, AMR은 독립 병목이라기보다 A3/A4와 연결된 흐름 병목 후보로 해석한다.
"""


def doc_flow(ctx: dict) -> str:
    return """
# 01. Analysis Flow

## 1단계: 데이터 준비
- MariaDB 서버에 적재하지 않고 SQL 덤프에서 핵심 테이블만 추출했다.
- 사용 테이블: `prc_hist_tb`, `prc_trns_tb`, `prc_oee_tb`, `strg_buf_in/out`, `strg_fns_in/out`, `std_eqpmn_tb`.
- 산출 DB: `data/pzone_analysis.sqlite`.

## 2단계: 정상 제품/정상 route 확정
- 대상 제품은 `PRD1000`, `PRD2000`, `PRD3001`, `PRD3002`.
- 제품별 route 빈도를 계산해 대표 route를 선정했다.
- AMR/C2는 route 검증에서는 optional 이동/후단 저장 단계로 보고 제거한 뒤 정상 여부를 판단했다.
- 정상 route 또는 정상 prefix에 속하지 않는 serial은 제외했다.

## 3단계: 공통 지표 계산
- 처리시간: 공정 `END - STR`.
- 대기시간: 다음 공정 `STR - 현재 공정 END`.
- WIP: 버퍼/완제품 창고 입출고 누적.
- 점유/이송: `TRN_CD`, `TRN_DEV_ID`, `TRN_QNT`, `STR/ARV`.
- OEE: RUN/IDLE/ALARM 비율.

## 4단계: 전체 공정 스크리닝
- 모든 공정을 동일 기준으로 병목 점수화했다.
- 병목 점수에는 처리시간 p90, 대기시간 p90, WIP p90, 점유시간 p90, alarm ratio가 반영된다.

## 5단계: 심층 분석
- A3: 후단 배출/AMR/C2 병목.
- A4: 처리시간 + 공유 레일 blocking 후보.
- A9/A7/A5/AMR: 연결 병목 후보.

## 6단계: 스케줄링 가능성 분류
- `Scheduling Feasible`, `Partially Feasible`, `Physically Constrained`로 분류했다.
- 추천 액션은 `PRIORITIZE_DISCHARGE`, `DISPATCH_AMR`, `CONTROL_WIP`, `SCHEDULE_RAIL`, `HOLD_ENTRY`, `REQUIRE_PHYSICAL_CHANGE` 중심이다.
"""


def doc_data(ctx: dict) -> str:
    return f"""
# 02. Data Scope and Cleaning

## 데이터 범위
{md_table(ctx['extract'], None)}

## 정상 route 기준
- 전체 serial: `{ctx['route_total']}`
- 정상 route 또는 prefix serial: `{ctx['route_kept']}`
- 제외 serial: `{ctx['route_excluded']}`

## Clean 기준
Clean 지표는 원본 로그에서 분석 왜곡 가능성이 큰 값을 제외한 지표다.

제외/flag 대상:
- `STR` 없이 `END`만 있는 기록
- `END` 없이 `STR`만 있는 기록
- 음수 처리시간 또는 음수 대기시간
- 설비별 `Q3 + 1.5*IQR` 초과 처리시간
- 기본 상한을 초과하는 장시간 처리/대기/점유 로그

Raw는 데이터 품질과 이상 상황 확인용이고, 병목 판단은 clean 기준을 우선한다.
"""


def doc_routes(ctx: dict) -> str:
    return f"""
# 03. Normal Routes

## 제품별 정상 route
{md_table(ctx['routes'], None, ['PRD_CD', 'normal_route', 'normal_serial_count', 'serial_count_total', 'normal_serial_ratio'])}

## 제외 route
정상 route에서 벗어난 전이는 분석에서 제외했다. 대표적으로 `A5 -> A3`는 제품별 정상 route에 없어서 제외됐다.

제외 route 예시:
{md_table(ctx['excluded'], 20, ['PRD_CD', 'PRD_SRL_NO', 'normalized_route', 'filter_reason'])}

## 해석
- `PRD1000/PRD2000`은 핸들 계열이며 A4, A5, A6, A7, A9_2, A8 흐름을 가진다.
- `PRD3001/PRD3002`는 룸미러 계열이며 A7, A5, A9_1, A3 흐름을 가진다.
- 따라서 `A7 -> A5`는 룸미러 계열 정상 route이고, 예외가 아니다.
"""


def doc_screening(ctx: dict) -> str:
    return f"""
# 04. All Process Screening

## 전체 병목 순위
{md_table(ctx['bottleneck'], 17, ['rank', 'process', 'bottleneck_score', 'processing_p90_sec', 'waiting_p90_sec', 'wip_p90', 'occupancy_p90_sec'])}

## 설비별 처리시간
{md_table(ctx['proc'], 15, ['logical_process', 'equipment_name', 'count_clean', 'p90_sec_clean', 'max_sec_clean', 'outlier_count'])}

## 공정 간 대기시간
{md_table(ctx['waits'], 15, ['transition', 'count', 'count_clean', 'p90_wait_sec_clean', 'max_wait_sec_clean', 'outlier_count'])}

## 판단
- 모든 공정을 먼저 같은 기준으로 비교했다.
- A3는 처리시간보다 후단 대기/WIP가 강한 병목이다.
- A4는 처리시간과 점유 측면에서 강한 구조 병목 후보이다.
- A9/A7/A5/AMR은 연결 병목 후보이며 제품군별로 해석해야 한다.
- A1/A2/A6/A8/C1/C2는 현재 데이터상 핵심 병목 우선순위는 낮지만 모니터링 대상이다.
"""


def doc_deep_dive(ctx: dict) -> str:
    return f"""
# 05. Key Bottleneck Deep Dive

## A3: 후단 배출 병목
- 병목 순위 1위.
- A3 처리시간 p90은 `{fmt_num(ctx['a3'].get('processing_p90_sec'), 1)}초`로 길지 않다.
- 하지만 A3 대기 p90은 `{fmt_num(ctx['a3'].get('waiting_p90_sec'), 1)}초`, 버퍼 WIP p90은 `{fmt_num(ctx['a3'].get('wip_p90'), 1)}`이다.
- A3 -> AMR_LD250 p90 대기: `{fmt_num(ctx['a3_wait_amr'].get('p90_wait_sec_clean'), 1)}초`
- A3 -> C2 p90 대기: `{fmt_num(ctx['a3_wait_c2'].get('p90_wait_sec_clean'), 1)}초`
- 해석: A3 자체 작업보다 A3 이후 AMR/C2 반출과 저장 흐름이 병목이다.

## A4: 구조 병목 + 공유 레일 후보
- A4 처리시간 p90은 `{fmt_num(ctx['a4_proc'].get('p90_sec_clean'), 1)}초`로 가장 크다.
- 매뉴얼상 A4는 사상 제거, 레이저 마킹, 산업용 로봇, 협동로봇, 툴체인저, 틸팅 유닛, 3개 파렛트 버퍼가 결합된 복합 CELL이다.
- A4 장시간 처리 window는 `{len(ctx['a4_windows'])}`개다.
- 해석: A4는 순수 스케줄링만으로 해결하기 어려운 구조적 병목 가능성이 크고, 레일 blocking 여부를 함께 봐야 한다.

## A9_1/A9_2: 후단 검사/조립 연결 병목
- A9_1은 처리시간과 점유시간 측면에서 상위권이다.
- A9_2는 A8/A9 반복 흐름 및 A3 반출 상태와 연결된다.
- 해석: A9 자체만 보기보다 A3 반출 가능 여부와 같이 봐야 한다.

## A7/A5: 제품군별 중간 병목
- 핸들 계열과 룸미러 계열의 route가 다르다.
- 룸미러 계열에서 `A7 -> A5`는 정상 route다.
- 통합 그래프만 보면 순서가 이상해 보일 수 있으므로 제품군별 분석이 후속 과제다.

## AMR/레일
- AMR_LD90은 원자재 투입 쪽, AMR_LD250은 완제품 반출 쪽으로 해석한다.
- 레일은 모든 제품이 공유하므로 공정 병목이 레일 병목으로 전파될 수 있다.
"""


def doc_shared_rail(ctx: dict) -> str:
    return f"""
# 06. Shared Rail Blocking Analysis

## 분석 목적
A4가 단순히 처리시간이 긴 공정인지, 아니면 공유 레일을 막아 다른 제품군까지 지연시키는지 확인한다.

## 분석 방법
- `TR01`, `TRN_DEV_ID=1~4`를 공유 레일/이송 자원으로 해석했다.
- A4 처리시간 상위 25% 이상을 A4 long window로 정의했다.
- A4 long window와 같은 시간대의 레일 이벤트, 다른 제품군 이벤트, 대기 이벤트를 계산했다.
- A4 종료 후 5/10/30분 downstream 이벤트 변화를 계산했다.

## A4 long window 상위
{md_table(ctx['a4_windows'], 12, ['PRD_SRL_NO', 'PRD_CD', 'a4_processing_sec', 'rail_event_count_overlap', 'rail_product_count_overlap', 'active_rail_count_overlap', 'other_family_rail_events', 'other_family_product_count', 'overlap_wait_event_count', 'overlap_wait_p90_sec'])}

## 제품군 overlap
{md_table(ctx['cross'], None)}

## A4 종료 후 lag
{md_table(ctx['lag'].groupby('lag_minutes', as_index=False).agg(
    a4_window_count=('PRD_SRL_NO', 'count'),
    mean_rail_events_after=('rail_event_count_after', 'mean'),
    mean_products_after=('rail_product_count_after', 'mean'),
    mean_wait_events_after=('waiting_event_count_after', 'mean'),
    mean_room_mirror_events_after=('room_mirror_rail_events_after', 'mean'),
    mean_handle_events_after=('handle_rail_events_after', 'mean')
), None)}

## 해석
- 일부 A4 long window에서 다른 제품군, 특히 룸미러 계열 레일 이벤트가 동시에 관측된다.
- 이는 A4 장시간 처리와 공유 레일 혼잡이 시간적으로 겹친다는 정황이다.
- 단, 현재 로그만으로 “특정 제품이 A4 때문에 직접 막혔다”고 단정하지 않는다.
- 후속 단계에서는 A4 long window와 normal window를 비교해 대조군 기반 검증을 해야 한다.
"""


def doc_actions(ctx: dict) -> str:
    return f"""
# 07. Schedulability and Actions

## 스케줄링 가능성 분류
{md_table(ctx['sched'], 17, ['rank', 'process', 'schedulability', 'recommended_action', 'judgement_reason'])}

## 병목별 액션
- A3: `PRIORITIZE_DISCHARGE`, `DISPATCH_AMR`
- A4: `CONTROL_WIP`, `HOLD_ENTRY`, 필요 시 `REQUIRE_PHYSICAL_CHANGE`
- A9: `CONTROL_WIP`, A3 반출 상태와 연동
- A7/A5: 제품군별 WIP cap 및 순서 제어
- AMR/레일: `SCHEDULE_RAIL`, `DISPATCH_AMR`

## Rule-based baseline 초안
```text
IF A3_WIP >= threshold AND AMR_LD250_available:
    recommended_action = DISPATCH_AMR

IF A3_to_C2_wait_high:
    recommended_action = PRIORITIZE_DISCHARGE

IF A4_processing_or_queue_high:
    recommended_action = CONTROL_WIP or HOLD_ENTRY

IF rail_occupancy_high AND waiting_products_exist:
    recommended_action = SCHEDULE_RAIL

IF physical_constraint_detected:
    recommended_action = REQUIRE_PHYSICAL_CHANGE
```
"""


def doc_remaining(ctx: dict) -> str:
    return """
# 08. Remaining Work

## 1. A3 병목 세분화
- A3 자체 처리 문제인지, AMR_LD250 배정 문제인지, C2 적재 문제인지 분리한다.
- A3 후단 반출 우선순위 규칙을 설계한다.

## 2. A4 공유 레일 blocking 검증 강화
- A4 long window와 normal window를 비교한다.
- A4 지연이 다른 제품군 대기에 미치는 영향을 대조군 기반으로 검증한다.

## 3. 제품군별 병목 분리
- 핸들 계열: `PRD1000/PRD2000`
- 룸미러 계열: `PRD3001/PRD3002`
- 제품군별 병목 순위와 액션을 따로 만든다.

## 4. 레일/AMR 해석 정교화
- `TRN_DEV_ID=1~4`의 물리 위치를 확인한다.
- 레일 동시 가동률과 idle rail 여부를 계산한다.
- AMR_LD90과 AMR_LD250의 역할을 분리한다.

## 5. Rule-based baseline과 LLM Agent
- Rule-based action baseline을 먼저 만든다.
- 이후 LLM Agent는 병목/원인/액션을 설명하고 추천하는 decision layer로 설계한다.
"""


def doc_ppt(ctx: dict) -> str:
    return f"""
# 09. PPT Briefing for GPT

이 문서는 PPT 생성을 위해 GPT에게 그대로 제공할 수 있는 브리핑이다.

## 발표 제목
P-ZONE 전체 공정 병목 분석 및 스케줄링 가능성 판단

## 핵심 메시지
1. 전체 공정을 동일 기준으로 스크리닝했다.
2. 정상 제품/정상 route 기준으로 예외 route를 제거했다.
3. A3는 가장 강한 운영 병목이다. 원인은 A3 자체 처리보다 후단 AMR/C2 반출 대기다.
4. A4는 가장 강한 구조 병목 후보다. 처리시간이 길고 공유 레일 blocking 가능성이 있다.
5. A9/A7/A5/AMR은 A3/A4와 연결된 병목 후보로 봐야 한다.
6. 스케줄링으로 개선 가능한 영역과 물리 개선이 필요한 영역을 분리해야 한다.

## 추천 슬라이드 구성
1. 프로젝트 목표
   - P-ZONE 전체 공정에서 병목을 식별하고, 스케줄링 가능성을 판단한다.

2. 데이터와 분석 범위
   - SQL 덤프, 공정 이력, 이송 이력, OEE, 버퍼/창고 로그.
   - 정상 route serial `{ctx['route_kept']}`개 사용.

3. 제품별 정상 route
   - PRD1000/2000과 PRD3001/3002의 route 차이를 보여준다.
   - `A7 -> A5`는 룸미러 계열 정상 route임을 설명한다.

4. 전체 공정 병목 순위
   - 그래프: `figures/01_bottleneck_ranking.png`
   - 메시지: A3, A4, AMR_LD90, A7, A9_1 순으로 병목 근거가 강하다.

5. 처리시간 기준 병목
   - 그래프: `figures/02_processing_p90_top.png`
   - 메시지: A4 처리시간 p90이 가장 크며 복합 CELL 구조와 일치한다.

6. 대기시간 기준 병목
   - 그래프: `figures/03_waiting_p90_top.png`
   - 메시지: A3 -> C2, A3 -> AMR_LD250 대기가 크다.

7. A3 Deep Dive
   - A3는 처리시간은 짧지만 후단 배출 대기와 WIP가 크다.
   - 액션: `PRIORITIZE_DISCHARGE`, `DISPATCH_AMR`.

8. A4 Deep Dive
   - A4는 사상/마킹/로봇/툴체인저/틸팅/버퍼가 결합된 복합 CELL.
   - 액션: `CONTROL_WIP`, `HOLD_ENTRY`, 필요 시 물리 개선.

9. 공유 레일 Blocking 분석
   - 그래프: `figures/04_rail_occupancy_timeseries.png`
   - 그래프: `figures/05_a4_processing_vs_rail_occupancy.png`
   - 그래프: `figures/06_a4_blocking_overlap_by_product_family.png`
   - 메시지: A4 long window와 다른 제품군 레일 이벤트가 겹치는 구간이 있다.

10. A4 이후 downstream lag
    - 그래프: `figures/07_a4_downstream_lag_effect.png`
    - 메시지: A4 종료 후 5/10/30분 downstream 이벤트 변화를 확인했다.

11. 스케줄링 가능성 분류
    - A3: Scheduling Feasible.
    - A4/A9/A7/A5: Partially Feasible.
    - 일부 구조 문제는 physical improvement 필요.

12. 다음 단계
    - A3 병목 세분화.
    - A4 long vs normal 대조군 분석.
    - 제품군별 병목 분리.
    - 레일/AMR 물리 위치 확인.
    - Rule-based baseline 및 LLM-assisted Decision Agent 설계.

## 사용할 그래프 설명
- `01_bottleneck_ranking.png`: 모든 공정을 종합 점수로 비교한 최종 병목 순위.
- `02_processing_p90_top.png`: 공정 자체 처리시간이 긴 설비 확인. A4가 핵심.
- `03_waiting_p90_top.png`: 공정 간 대기시간 확인. A3 후단이 핵심.
- `04_rail_occupancy_timeseries.png`: 공유 레일 점유 추이.
- `05_a4_processing_vs_rail_occupancy.png`: A4 처리시간과 같은 시간대 레일 이벤트 overlap.
- `06_a4_blocking_overlap_by_product_family.png`: A4 window 중 같은 제품군/다른 제품군 overlap.
- `07_a4_downstream_lag_effect.png`: A4 종료 후 downstream 이벤트 변화.

## 발표 시 주의할 점
- 현재 결과는 로그 기반 진단이며 실제 제어 실험 결과는 아니다.
- 공유 레일 blocking은 인과 확정이 아니라 시간 겹침 기반 정황 분석이다.
- 따라서 결론은 “A4가 직접 막았다”가 아니라 “A4가 공유 레일 blocking 후보로 볼 근거가 있다”로 표현해야 한다.
"""


def write_docs(ctx: dict) -> None:
    docs = {
        "README.md": doc_readme(ctx),
        "00_executive_summary.md": doc_exec(ctx),
        "01_analysis_flow.md": doc_flow(ctx),
        "02_data_scope_and_cleaning.md": doc_data(ctx),
        "03_normal_routes.md": doc_routes(ctx),
        "04_all_process_screening.md": doc_screening(ctx),
        "05_key_bottleneck_deep_dive.md": doc_deep_dive(ctx),
        "06_shared_rail_blocking.md": doc_shared_rail(ctx),
        "07_schedulability_and_actions.md": doc_actions(ctx),
        "08_remaining_work.md": doc_remaining(ctx),
        "09_ppt_briefing_for_gpt.md": doc_ppt(ctx),
    }
    for path, content in docs.items():
        write(path, content)


def main() -> int:
    copy_assets()
    ctx = build_context()
    write_tables(ctx)
    write_docs(ctx)
    print(f"Package written to {PKG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
