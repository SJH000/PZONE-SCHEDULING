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
   - 정상 route serial `294`개 사용.

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
