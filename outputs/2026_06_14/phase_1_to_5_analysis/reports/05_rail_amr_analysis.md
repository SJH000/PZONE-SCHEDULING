# 05. 레일/AMR 이송 자원 분석

## 핵심 결과
- TRN_DEV_ID=1~4별 이벤트 수와 active bucket ratio를 계산했다.
- AMR_LD90과 AMR_LD250을 분리해 병목 순위, 대기 p90, alarm ratio를 요약했다.
- 현재 DB만으로는 TRN_DEV_ID의 물리 위치와 AMR 배정 지연 원인을 확정할 수 없다.

## 판단
레일/AMR은 공정 처리시간보다 공정 간 대기를 증폭시키는 공유 이송 자원으로 봐야 한다. 다만 물리 위치 매핑과 AMR dispatch 로그가 없으므로 현재 결과는 자원 병목 후보를 좁히는 분석으로 사용한다.
