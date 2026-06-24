# Rule-based Scheduling Baseline Report

## 목적
현장 추가정보 없이 6번 단계를 진행하기 위해, 기존 로그만으로 rule-based scheduling baseline 후보를 만들고 오프라인 proxy 검증을 수행했다.

이 결과는 실제 설비 제어 효과 확정이 아니다. AMR availability, C2 capacity, `TRN_DEV_ID=1~4` 물리 위치가 없으므로 action은 운영 규칙 후보이며, 각 action에 confidence와 limitation을 함께 기록했다.

## 생성 범위
- State bucket: 24,221개
- Action row: 12,465개
- 분석 bucket 크기: `5min`
- recent window: `60min`
- 출력 경로: `outputs/2026_06_14/rule_baseline/`

## Rule Trigger Counts
| action               |   trigger_count |   bucket_count | confidence_modes   |
|:---------------------|----------------:|---------------:|:-------------------|
| PRIORITIZE_DISCHARGE |           10945 |          10945 | High               |
| SCHEDULE_RAIL        |            1292 |           1292 | Low                |
| CONTROL_WIP          |             127 |            127 | Medium             |
| HOLD_ENTRY           |              87 |             87 | Medium             |
| DISPATCH_AMR         |              14 |             14 | Medium             |

## Proxy 검증
| proxy                                     |   target_bucket_count |   trigger_bucket_count |   overlap_bucket_count |   coverage |   precision |
|:------------------------------------------|----------------------:|-----------------------:|-----------------------:|-----------:|------------:|
| A3 rule vs high A3 downstream wait        |                   330 |                  10945 |                    330 |          1 |   0.0301508 |
| A4 rule vs A4 long window                 |                   127 |                    127 |                    127 |          1 |   1         |
| Rail rule vs rail congestion              |                  1292 |                   1292 |                   1292 |          1 |   1         |
| Hold entry vs A4+rail combined congestion |                    87 |                     87 |                     87 |          1 |   1         |

해석 기준:
- coverage: 실제 병목 proxy bucket 중 rule이 감지한 비율
- precision: rule trigger bucket 중 병목 proxy와 겹친 비율
- 이 값은 개선율이 아니라 감지 성능이다.

## Thresholds
| metric                       |   threshold | used_by                | reason                       |
|:-----------------------------|------------:|:-----------------------|:-----------------------------|
| buffer_wip                   |        70   | PRIORITIZE_DISCHARGE   | BUFFER WIP p90 73.1 근처에서 시작  |
| a3_to_amr_wait_p90_recent    |      1200   | PRIORITIZE_DISCHARGE   | A3->AMR high wait 감지         |
| a3_to_c2_wait_p90_recent     |      1800   | PRIORITIZE_DISCHARGE   | A3->C2 high wait 감지          |
| dispatch_amr_wait_p90_recent |       900   | DISPATCH_AMR           | AMR dispatch 후보 감지           |
| a4_long_threshold_sec        |       686.9 | CONTROL_WIP/HOLD_ENTRY | 기존 A4 long threshold         |
| rail_event_count_p90         |       583   | SCHEDULE_RAIL          | 현재 데이터 rail event p90        |
| active_rail_count            |         4   | SCHEDULE_RAIL          | TRN_DEV_ID=1~4 모두 active인 구간 |

## Product Family Context
| action               | product_family_context   |   trigger_count |
|:---------------------|:-------------------------|----------------:|
| CONTROL_WIP          | HANDLE                   |             113 |
| CONTROL_WIP          | MIXED_OR_NONE            |               9 |
| CONTROL_WIP          | ROOM_MIRROR              |               5 |
| DISPATCH_AMR         | HANDLE                   |               8 |
| DISPATCH_AMR         | MIXED_OR_NONE            |               4 |
| DISPATCH_AMR         | ROOM_MIRROR              |               2 |
| HOLD_ENTRY           | HANDLE                   |              82 |
| HOLD_ENTRY           | ROOM_MIRROR              |               5 |
| PRIORITIZE_DISCHARGE | MIXED_OR_NONE            |            9532 |
| PRIORITIZE_DISCHARGE | HANDLE                   |            1256 |
| PRIORITIZE_DISCHARGE | ROOM_MIRROR              |             157 |
| SCHEDULE_RAIL        | HANDLE                   |            1031 |
| SCHEDULE_RAIL        | ROOM_MIRROR              |             251 |
| SCHEDULE_RAIL        | MIXED_OR_NONE            |              10 |

## 한계
- `DISPATCH_AMR`는 AMR availability가 없기 때문에 실제 배정 가능 여부를 판단하지 않는다.
- `SCHEDULE_RAIL`은 `TRN_DEV_ID=1~4` 물리 위치가 없어 구체 레일 구간 제어로 해석하지 않는다.
- `PRIORITIZE_DISCHARGE`는 A3 후단 대기와 BUFFER WIP를 감지하지만, AMR 문제인지 C2 포화인지는 확정하지 않는다.
- `HOLD_ENTRY`는 A4 long window와 rail congestion이 같은 bucket에 있는 경우의 후보 action이며, 실제 설비 blocking 확정이 아니다.

## 다음 단계
1. 이 baseline action log를 사용해 LLM decision agent의 입력 state와 출력 action schema를 정의한다.
2. 현장 정보가 확보되면 `TRN_DEV_ID` 물리 위치, AMR dispatch 상태, C2 capacity를 state에 추가한다.
3. 그 후 rule trigger가 실제 대기시간/WIP를 줄이는지 로그 리플레이 또는 시뮬레이션으로 평가한다.
