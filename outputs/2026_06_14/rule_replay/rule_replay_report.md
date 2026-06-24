# Rule Replay Report

## 목적
6번 rule baseline이 기존 로그에서 trigger된 이후 병목 지표가 어떻게 변했는지 전후 60분 기준으로 관찰했다.

이 결과는 실제 개선 효과 확정이 아니다. action이 실제로 적용된 로그가 아니므로, trigger 이후 자연 변화와 rule 타이밍의 적절성을 보는 오프라인 replay 평가다.

## Replay Effect Summary
| action               | action_group   | metric                    |   trigger_metric_rows |   before_mean |   after_mean |    delta_mean |   delta_ratio_mean |   improved_ratio |   worsened_ratio |   unchanged_ratio | interpretation         |
|:---------------------|:---------------|:--------------------------|----------------------:|--------------:|-------------:|--------------:|-------------------:|-----------------:|-----------------:|------------------:|:-----------------------|
| CONTROL_WIP          | A4             | a4_long_count             |                   127 |      0.430446 |     0.415354 |   -0.0150919  |         0.670042   |       0.496063   |       0.456693   |         0.0472441 | improved_after_trigger |
| CONTROL_WIP          | A4             | a4_processing_max_sec     |                   127 |    653.285    |   650.624    |   -2.66049    |         1.07495    |       0.496063   |       0.488189   |         0.015748  | improved_after_trigger |
| DISPATCH_AMR         | A3             | a3_to_amr_wait_p90_recent |                    14 |   3328.64     |  3113.17     | -215.473      |         7.67837    |       0.5        |       0.5        |         0         | improved_after_trigger |
| DISPATCH_AMR         | A3             | a3_to_c2_wait_p90_recent  |                    14 |    188.821    |  2048.69     | 1859.87       |         1.66667    |       0          |       0.285714   |         0.714286  | worse_after_trigger    |
| DISPATCH_AMR         | A3             | buffer_wip                |                    14 |     29.381    |    31.5357   |    2.15476    |         0.0898358  |       0.0714286  |       0.928571   |         0         | worse_after_trigger    |
| HOLD_ENTRY           | A4             | a4_long_count             |                    87 |      0.441571 |     0.454023 |    0.0124521  |         0.91321    |       0.448276   |       0.517241   |         0.0344828 | worse_after_trigger    |
| HOLD_ENTRY           | A4             | a4_processing_max_sec     |                    87 |    489.55     |   511.778    |   22.2273     |         1.34181    |       0.45977    |       0.528736   |         0.0114943 | worse_after_trigger    |
| PRIORITIZE_DISCHARGE | A3             | a3_to_amr_wait_p90_recent |                 10939 |    175.546    |   172.076    |   -3.46982    |         2.69811    |       0.0187403  |       0.018009   |         0.963251  | improved_after_trigger |
| PRIORITIZE_DISCHARGE | A3             | a3_to_c2_wait_p90_recent  |                 10939 |     44.7592   |    67.1245   |   22.3653     |         5.10437    |       0.00411372 |       0.00722187 |         0.988664  | worse_after_trigger    |
| PRIORITIZE_DISCHARGE | A3             | buffer_wip                |                 10939 |     80.9541   |    80.9795   |    0.0253451  |         0.00043763 |       0.016912   |       0.0340982  |         0.94899   | worse_after_trigger    |
| SCHEDULE_RAIL        | RAIL           | active_rail_count         |                  1292 |      2.96717  |     2.96949  |    0.00232237 |         0.412352   |       0.373065   |       0.355263   |         0.271672  | worse_after_trigger    |
| SCHEDULE_RAIL        | RAIL           | rail_event_count          |                  1292 |    250.785    |   266.588    |   15.8038     |         2.75798    |       0.477554   |       0.508514   |         0.0139319 | worse_after_trigger    |

## Action Quality / Window Status
| action               | action_group   | window_status       |   metric_row_count |   trigger_bucket_count |
|:---------------------|:---------------|:--------------------|-------------------:|-----------------------:|
| CONTROL_WIP          | A4             | ok                  |                254 |                    127 |
| DISPATCH_AMR         | A3             | ok                  |                 42 |                     14 |
| HOLD_ENTRY           | A4             | ok                  |                174 |                     87 |
| PRIORITIZE_DISCHARGE | A3             | insufficient_window |                 18 |                  10945 |
| PRIORITIZE_DISCHARGE | A3             | ok                  |              32817 |                  10945 |
| SCHEDULE_RAIL        | RAIL           | ok                  |               2584 |                   1292 |

## 해석 기준
- `delta_mean < 0`: trigger 이후 평균 지표가 낮아진 관찰 결과
- `delta_mean > 0`: trigger 이후 평균 지표가 높아진 관찰 결과
- `improved_ratio`: 개별 trigger-window 중 after가 before보다 낮았던 비율
- `insufficient_window`: trigger 전후 60분 자료가 충분하지 않은 경우

## 한계
- AMR availability, C2 capacity, TRN_DEV_ID 물리 위치가 없다.
- replay는 실제 제어 적용 결과가 아니라 기존 로그의 전후 관찰이다.
- 개선 확정이 아니라 rule 개선과 다음 단계 시뮬레이션/agent 설계를 위한 참고 자료다.
