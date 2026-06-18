# Required Field Gap Report

현재 DB/CSV 로그만으로 원인을 확정하기 어려운 정보는 아래와 같다.

- **TRN_DEV_ID_PHYSICAL_LOCATION**: TRN_DEV_ID=1~4의 실제 물리 위치/구간 매핑 필요
- **AMR_DISPATCH_TIMESTAMPS**: AMR 호출, 배정, 취소, 대기 상태 로그 필요
- **C2_SLOT_CAPACITY**: C2 완제품 창고 slot capacity와 포화 상태 로그 필요
- **OEE_IDLE_DEFINITION**: IDLE이 정상 대기인지 설비 비가동인지 코드 정의 필요
- **BUFFER_STOPPER_CAPACITY**: 스토퍼/버퍼별 실제 capacity와 blocked 상태 로그 필요

## 사용 원칙
위 정보가 없을 때는 AMR 지연, C2 포화, 레일 물리 blocking을 확정 표현하지 않는다. 대신 로그 기반 후보 원인으로 분류하고, 현장 매핑이 확보되면 재검증한다.
