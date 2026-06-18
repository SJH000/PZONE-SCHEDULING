# P-ZONE 1~5번 분석 요약

## 완료 범위
- 1. 데이터/분석 검증
- 2. A3 병목 세분화
- 3. A4 공유 레일 blocking 검증
- 4. 제품군별 병목 분리
- 5. 레일/AMR 이송 자원 분석 고도화

## 핵심 결론
- 정상 route 분석 serial: 294 / 324
- A3는 자체 처리보다 AMR/C2 반출 대기와 BUFFER WIP가 큰 후단 배출 병목이다.
- A4는 long window와 공유 레일 overlap이 관측되는 blocking 후보이며, 현재 근거 강도는 **Strong**이다.
- HANDLE 상위 병목 후보: A3, A4, A9_2
- ROOM_MIRROR 상위 병목 후보: A3, A7, A9_1
- 레일/AMR 분석은 가능하지만 TRN_DEV_ID 물리 위치와 AMR dispatch 로그가 없어 원인 확정에는 추가 정보가 필요하다.

## 개선 단계 진입 조건
1~5번 분석으로 병목 후보와 원인 가설은 정리되었다. 다음 단계는 rule-based scheduling baseline을 설계하고 로그 리플레이/시뮬레이션으로 효과를 검증하는 것이다.
