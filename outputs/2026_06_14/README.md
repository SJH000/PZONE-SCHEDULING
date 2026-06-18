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
- 정상 route 기준 분석 대상 serial: `294` / `324`
- 제외 serial: `30`
- 최상위 병목: `A3`
- 현재 결론: A3는 후단 배출/AMR/C2 병목, A4는 복합 CELL 및 공유 레일 blocking 후보, A9/A7/A5/AMR은 연결 병목 후보

## 폴더 구조
- `data/`: 분석 근거 CSV
- `figures/`: 발표용 핵심 그래프
- `tables/`: Markdown 표
- `*.md`: 설명 문서
