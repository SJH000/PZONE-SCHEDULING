# 07. Schedulability and Actions

## 스케줄링 가능성 분류
|   rank | process             | schedulability      | recommended_action   | judgement_reason                                     |
|-------:|:--------------------|:--------------------|:---------------------|:-----------------------------------------------------|
|      1 | A3                  | Scheduling Feasible | PRIORITIZE_DISCHARGE | 후단 반출/저장 흐름의 대기 비중이 커서 AMR/모바일 이송 및 배출 우선순위 조정 여지가 큼 |
|      2 | A4                  | Partially Feasible  | CONTROL_WIP          | 대기/WIP/점유 지표가 있어 투입 제한과 우선순위 조정으로 일부 완화 가능           |
|      3 | AMR_LD90            | Partially Feasible  | CONTROL_WIP          | 대기/WIP/점유 지표가 있어 투입 제한과 우선순위 조정으로 일부 완화 가능           |
|      4 | A7                  | Partially Feasible  | CONTROL_WIP          | 대기/WIP/점유 지표가 있어 투입 제한과 우선순위 조정으로 일부 완화 가능           |
|      5 | A9_1                | Partially Feasible  | CONTROL_WIP          | 대기/WIP/점유 지표가 있어 투입 제한과 우선순위 조정으로 일부 완화 가능           |
|      6 | A5                  | Partially Feasible  | CONTROL_WIP          | 대기/WIP/점유 지표가 있어 투입 제한과 우선순위 조정으로 일부 완화 가능           |
|      7 | A9_2                | Partially Feasible  | CONTROL_WIP          | 대기/WIP/점유 지표가 있어 투입 제한과 우선순위 조정으로 일부 완화 가능           |
|      8 | A6_TESLA            | Partially Feasible  | CONTROL_WIP          | 대기/WIP/점유 지표가 있어 투입 제한과 우선순위 조정으로 일부 완화 가능           |
|      9 | A1                  | Partially Feasible  | CONTROL_WIP          | 대기/WIP/점유 지표가 있어 투입 제한과 우선순위 조정으로 일부 완화 가능           |
|     10 | C2_FINISHED_STORAGE | Scheduling Feasible | PRIORITIZE_DISCHARGE | 후단 반출/저장 흐름의 대기 비중이 커서 AMR/모바일 이송 및 배출 우선순위 조정 여지가 큼 |
|     11 | BUFFER              | Scheduling Feasible | PRIORITIZE_DISCHARGE | 후단 반출/저장 흐름의 대기 비중이 커서 AMR/모바일 이송 및 배출 우선순위 조정 여지가 큼 |
|     12 | AMR_LD250           | Scheduling Feasible | DISPATCH_AMR         | 후단 반출/저장 흐름의 대기 비중이 커서 AMR/모바일 이송 및 배출 우선순위 조정 여지가 큼 |
|     13 | A2                  | Partially Feasible  | CONTROL_WIP          | 대기/WIP/점유 지표가 있어 투입 제한과 우선순위 조정으로 일부 완화 가능           |
|     14 | A6_KONA             | Partially Feasible  | CONTROL_WIP          | 공정 자체 처리시간 비중이 커서 순서 조정보다는 설비 작업량/공간/버퍼 구조 영향이 큼     |
|     15 | A8                  | Partially Feasible  | CONTROL_WIP          | 대기/WIP/점유 지표가 있어 투입 제한과 우선순위 조정으로 일부 완화 가능           |
|     16 | C1_RAW_STORAGE      | Partially Feasible  | CONTROL_WIP          | 대기/WIP/점유 지표가 있어 투입 제한과 우선순위 조정으로 일부 완화 가능           |
|     17 | FINISHED_STORAGE    | Scheduling Feasible | PRIORITIZE_DISCHARGE | 후단 반출/저장 흐름의 대기 비중이 커서 AMR/모바일 이송 및 배출 우선순위 조정 여지가 큼 |

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
