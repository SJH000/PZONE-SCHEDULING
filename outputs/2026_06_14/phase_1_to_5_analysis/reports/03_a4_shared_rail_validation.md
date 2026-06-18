# 03. A4 공유 레일 Blocking 검증

## 핵심 결과
- A4 long window 기준: 686.9초
- A4 long window 수: 38개
- long/normal 다른 제품군 overlap 비율: 133.79
- A4 blocking 가설 근거 강도: **Strong**

## 판단
A4는 처리시간이 긴 복합 CELL이며, long window 중 공유 레일 이벤트와 다른 제품군 overlap이 관측된다. 다만 `TRN_DEV_ID`의 실제 물리 위치가 DB에 없으므로, 현재 결론은 공유 레일 blocking 후보 검증 결과로 해석해야 한다.
