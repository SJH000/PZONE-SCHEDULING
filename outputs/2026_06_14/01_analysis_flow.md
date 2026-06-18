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
