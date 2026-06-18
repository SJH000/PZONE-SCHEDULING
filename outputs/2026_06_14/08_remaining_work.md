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
