# P-ZONE 6~7번 진행사항 및 LLM Todo 발표 가이드

작성 목적:  
이 문서는 `PZONE_rule_baseline_replay_7slides.pptx` 발표자가 6번 Rule-based Scheduling Baseline, 7번 Replay/Simulation 평가, 그리고 추가할 8페이지 LLM Todo 내용을 이해할 수 있도록 정리한 발표용 가이드다.

관련 PPT:

```text
C:\Users\SHINJUNGHYUN\pzone_scheduling\outputs\2026_06_14\PZONE_rule_baseline_replay_7slides.pptx
```

관련 대본:

```text
C:\Users\SHINJUNGHYUN\pzone_scheduling\outputs\2026_06_14\PZONE_rule_baseline_replay_ppt_script_1min.md
```

## 1. 발표 전체 메시지

이번 발표의 핵심은 다음 한 문장이다.

```text
1~5번에서 병목을 찾았고, 6~7번에서는 그 병목을 개선하기 위한 rule 후보를 만들고 기존 로그로 오프라인 검증했다.
다만 아직 실제 제어 효과를 확정한 것은 아니며, 다음 단계는 LLM decision agent 구조를 먼저 구현한 뒤 rule baseline과 비교 평가하는 것이다.
```

발표자가 반드시 구분해야 하는 내용:

- 1~5번: 병목 분석 단계
- 6번: 개선 action 후보를 만드는 rule baseline 설계 단계
- 7번: 만든 rule이 쓸 만한지 기존 로그로 replay/simulation 평가하는 단계
- 8번 Todo: LLM을 바로 학습시키는 것이 아니라, agent 구조와 verifier를 먼저 구현하는 단계

## 2. 프로젝트 배경 요약

P-ZONE 제조 라인에서는 제품군마다 공정 route가 다르지만, 일부 자원은 공유된다. 특히 A3 후단 반출, A4 복합 CELL, 레일/AMR 이송 자원은 병목 후보로 분석됐다.

1~5번 분석에서 나온 핵심 결론:

- A3는 후단 반출 병목이 가장 강하게 나타난다.
- A4는 처리시간이 긴 복합 CELL이며 공유 레일 blocking 후보이다.
- A9/A7/A5는 제품군별 route 차이에 따라 연결 병목 후보가 된다.
- 레일/AMR은 모든 제품 흐름에 영향을 주는 공유 이송 자원이다.
- 현장 추가정보 없이도 로그 기반 분석은 가능하지만, 실제 물리 위치나 AMR 배정 상태는 확정하기 어렵다.

이 흐름에서 6번과 7번은 “분석 결과를 실제 scheduling action 후보로 연결하는 단계”다.

## 3. 6번 Rule-based Scheduling Baseline이란?

6번의 목적은 실제 설비를 제어하는 것이 아니라, 기존 로그를 보고 “이런 상황이면 이런 scheduling action을 내야 한다”는 rule 후보를 만드는 것이다.

사용한 입력:

```text
outputs/data/product_routes.csv
outputs/data/transition_waiting_events.csv
outputs/data/wip_timeseries.csv
outputs/data/rail_timeseries.csv
outputs/2026_06_14/phase_1_to_5_analysis/data/*.csv
```

생성한 주요 출력:

```text
outputs/2026_06_14/rule_baseline/data/state_5min.csv
outputs/2026_06_14/rule_baseline/data/actions.csv
outputs/2026_06_14/rule_baseline/rule_baseline_report.md
```

핵심 방식:

- 기존 로그를 5분 단위 bucket으로 나눈다.
- 각 bucket마다 현재 운영 상태를 state로 만든다.
- state에는 buffer WIP, A3 후단 대기, A4 long window, rail event count 등이 들어간다.
- 이 state에 rule을 적용해 action log를 만든다.

주요 생성 결과:

| 항목 | 값 |
|---|---:|
| 5분 state bucket 수 | 24,221개 |
| action row 수 | 12,465개 |
| recent window | 60분 |
| bucket 크기 | 5분 |

## 4. 6번에서 정의한 Action 의미

6번에서 정의한 action은 다음과 같다.

| Action | 의미 | 주로 보는 병목 |
|---|---|---|
| `PRIORITIZE_DISCHARGE` | 후단 반출 우선 | A3, BUFFER, C2 |
| `DISPATCH_AMR` | AMR 배정 필요 후보 | A3 -> AMR |
| `CONTROL_WIP` | A4 주변 WIP/진입 제어 | A4 |
| `SCHEDULE_RAIL` | 레일 혼잡 시 이송 스케줄링 필요 | TR01, TRN_DEV_ID |
| `HOLD_ENTRY` | A4 long과 rail 혼잡이 겹칠 때 진입 보류 후보 | A4 entry, rail |
| `NO_ACTION` | 별도 action 없음 | 정상 또는 판단 불필요 |

중요한 점:

- 이 action들은 실제 현장 제어 명령이 아니다.
- “이런 상황이면 이런 제어를 검토해야 한다”는 후보 action이다.
- AMR availability, C2 capacity, TRN_DEV_ID 물리 위치가 없기 때문에 일부 action은 confidence가 낮다.

## 5. 6번 Rule Trigger 결과

Rule trigger count는 아래와 같다.

| Action | Trigger 수 | 해석 |
|---|---:|---|
| `PRIORITIZE_DISCHARGE` | 10,945 | A3 후단/BUFFER 조건이 자주 발생 |
| `SCHEDULE_RAIL` | 1,292 | rail event p90 이상인 혼잡 구간 |
| `CONTROL_WIP` | 127 | A4 long window 감지 |
| `HOLD_ENTRY` | 87 | A4 long과 rail 혼잡이 동시에 발생 |
| `DISPATCH_AMR` | 14 | A3 완료와 AMR 대기 조건이 함께 강하게 나타난 구간 |

발표 시 해석:

- `PRIORITIZE_DISCHARGE`가 가장 많다는 것은 A3 후단 반출 문제가 넓게 나타난다는 뜻이다.
- `SCHEDULE_RAIL`은 rail event가 높은 구간을 잡아낸다.
- `CONTROL_WIP`와 `HOLD_ENTRY`는 A4 long window와 연결되어 더 좁은 구간에서 발생한다.
- `DISPATCH_AMR`은 적게 발생했는데, 이는 AMR 실제 사용 가능 여부가 로그에 없어서 보수적으로 잡았기 때문이다.

## 6. 6번 Proxy 검증 결과

Proxy 검증은 “rule이 실제 병목 후보 구간을 잘 감지했는가”를 보는 것이다. 여기서 중요한 점은 proxy 검증이 실제 개선 효과를 의미하지 않는다는 것이다.

주요 결과:

| Proxy | Coverage | Precision | 해석 |
|---|---:|---:|---|
| A3 rule vs high A3 downstream wait | 1.00 | 0.03 | A3 고대기 구간은 모두 잡았지만 trigger가 너무 넓음 |
| A4 rule vs A4 long window | 1.00 | 1.00 | A4 long window를 정확히 잡음 |
| Rail rule vs rail congestion | 1.00 | 1.00 | 정의한 rail congestion 구간과 일치 |
| Hold entry vs A4+rail combined congestion | 1.00 | 1.00 | A4와 rail 혼잡 동시 구간을 잡음 |

발표 시 표현:

```text
A4와 rail rule은 정의한 병목 proxy를 정확히 감지했다.
반면 A3 rule은 고대기 구간을 놓치지는 않았지만, 너무 넓게 trigger되어 정밀도 개선이 필요하다.
```

## 7. 7번 Replay 평가란?

7번 replay는 rule action이 발생한 시점 전후 60분을 비교하는 평가다.

비교 방식:

```text
trigger 이전 60분 평균
trigger 이후 60분 평균
delta = after - before
```

주의:

- 실제로 rule을 적용한 결과가 아니다.
- 기존 로그에서 action이 trigger된 시점 주변의 지표 변화를 관찰한 것이다.
- 그래서 “개선이 확정됐다”가 아니라 “이 action이 어떤 지표와 연결되는지 관찰했다”라고 말해야 한다.

## 8. 7번 Replay 주요 결과

### A3 관련 Action

`PRIORITIZE_DISCHARGE`:

| Metric | Before | After | Delta | 해석 |
|---|---:|---:|---:|---|
| A3 -> AMR wait p90 recent | 175.5 | 172.1 | -3.5 | 소폭 감소 |
| A3 -> C2 wait p90 recent | 44.8 | 67.1 | +22.4 | 증가 |
| buffer WIP | 81.0 | 81.0 | +0.03 | 거의 변화 없음 |

해석:

- A3 -> AMR 대기는 약간 줄었지만, C2 대기와 buffer WIP는 명확히 개선됐다고 보기 어렵다.
- 즉 A3 rule은 방향성은 맞지만 조건이 너무 넓고, C2/BUFFER 조건과 결합해 정밀화해야 한다.

`DISPATCH_AMR`:

| Metric | Before | After | Delta | 해석 |
|---|---:|---:|---:|---|
| A3 -> AMR wait p90 recent | 3328.6 | 3113.2 | -215.5 | 감소 방향 |
| A3 -> C2 wait p90 recent | 188.8 | 2048.7 | +1859.9 | 크게 증가 |
| buffer WIP | 29.4 | 31.5 | +2.2 | 증가 |

해석:

- A3 -> AMR 대기는 줄어드는 방향이지만 trigger 수가 14건으로 적다.
- AMR availability가 없기 때문에 실제로 AMR 배정이 가능한 상황인지는 확정할 수 없다.
- C2 대기가 증가했기 때문에 AMR만 보내는 것으로는 충분하지 않고, C2 적재/완제품 창고 흐름까지 함께 봐야 한다.

### A4 관련 Action

`CONTROL_WIP`:

| Metric | Before | After | Delta | 해석 |
|---|---:|---:|---:|---|
| A4 long count | 0.430 | 0.415 | -0.015 | 소폭 감소 |
| A4 processing max sec | 653.3 | 650.6 | -2.7 | 소폭 감소 |

해석:

- A4는 CONTROL_WIP가 trigger된 뒤 지표가 약간 좋아지는 방향을 보였다.
- 다만 효과가 크지는 않으므로 보조 개선 후보로 보는 것이 맞다.

`HOLD_ENTRY`:

| Metric | Before | After | Delta | 해석 |
|---|---:|---:|---:|---|
| A4 long count | 0.442 | 0.454 | +0.012 | 증가 |
| A4 processing max sec | 489.6 | 511.8 | +22.2 | 증가 |

해석:

- 현재 HOLD_ENTRY rule은 trigger 이후 A4 지표가 좋아졌다고 보기 어렵다.
- A4와 rail이 동시에 혼잡한 구간을 잡기는 하지만, 실제 hold 조건은 더 정교하게 설계해야 한다.

### Rail 관련 Action

`SCHEDULE_RAIL`:

| Metric | Before | After | Delta | 해석 |
|---|---:|---:|---:|---|
| active rail count | 2.967 | 2.969 | +0.002 | 거의 변화 없음 |
| rail event count | 250.8 | 266.6 | +15.8 | 증가 |

해석:

- 현재 rail rule은 혼잡 구간을 감지하지만, trigger 이후 자연스럽게 혼잡이 줄었다는 증거는 약하다.
- `TRN_DEV_ID=1~4`가 실제 어느 rail 구간인지 모르기 때문에 구체적인 제어 action으로 연결하기 어렵다.

## 9. 7번 Counterfactual Simulation이란?

Counterfactual simulation은 “만약 action이 after 지표를 10%, 20%, 30% 완화한다고 가정하면 얼마나 좋아질 수 있는가”를 계산한 것이다.

중요한 해석:

- 실제 개선 효과가 아니다.
- 가정 기반 민감도 분석이다.
- 어떤 지표가 개선 action에 민감한지 보는 용도다.

예시:

```text
PRIORITIZE_DISCHARGE가 실제로 buffer WIP를 20% 낮출 수 있다고 가정하면,
buffer WIP는 약 81 수준에서 약 65 수준으로 낮아지는 시나리오가 나온다.
```

발표 시 표현:

```text
이 결과는 실제 제어 검증이 아니라, rule이 효과를 낸다고 가정했을 때 어떤 지표가 크게 반응하는지 보는 민감도 분석입니다.
```

## 10. 6~7번 결과의 현재 판단

현재 판단은 다음과 같다.

1. A3 우선 반출은 가장 먼저 검증해야 하는 action 후보이다.
   - 이유: A3 후단 병목이 가장 강하고, trigger도 가장 많다.
   - 한계: rule이 너무 넓게 trigger되어 정밀도 개선이 필요하다.

2. A4 CONTROL_WIP는 보조 개선 후보이다.
   - 이유: replay에서 A4 long count와 processing max가 소폭 감소했다.
   - 한계: 효과가 크지는 않고, A4 blocking 원인은 물리 매핑 없이는 확정하기 어렵다.

3. HOLD_ENTRY는 현재 rule을 그대로 쓰기 어렵다.
   - 이유: trigger 이후 A4 지표가 오히려 나빠지는 방향이 관찰됐다.
   - 필요 작업: hold 조건을 더 좁히거나, A4/rail/C2 상태를 함께 반영해야 한다.

4. Rail scheduling은 감지는 가능하지만 제어 action 확정은 어렵다.
   - 이유: `TRN_DEV_ID=1~4`의 실제 물리 위치가 없다.
   - 필요 작업: 물리 위치가 없으면 “어느 구간을 제어할지” 확정할 수 없다.

5. 6~7번은 실제 개선 효과 확정이 아니라 다음 단계 agent 설계를 위한 baseline이다.
   - 이후 LLM agent도 이 baseline과 비교해야 한다.

## 11. 슬라이드별 발표 해설

### Slide 1. 6~7번 진행 목적

핵심 메시지:

```text
1~5번에서 병목을 찾았고, 6~7번에서는 개선 action 후보를 만들고 오프라인으로 평가했다.
```

설명할 내용:

- 6번은 rule baseline 설계
- 7번은 replay/simulation 평가
- 현장 추가정보가 없기 때문에 실제 제어가 아니라 로그 기반 평가임

발표 포인트:

```text
이 발표는 설비를 실제로 제어한 결과가 아니라, 기존 로그를 기준으로 어떤 scheduling action이 필요한지 검증한 결과입니다.
```

### Slide 2. Rule-based Scheduling Baseline 설계

핵심 메시지:

```text
병목 상황을 5개 주요 action으로 매핑했다.
```

설명할 action:

- A3 후단 대기 높음 -> `PRIORITIZE_DISCHARGE`
- A3 완료 후 AMR 대기 높음 -> `DISPATCH_AMR`
- A4 long window -> `CONTROL_WIP`
- rail event 많음 -> `SCHEDULE_RAIL`
- A4 long과 rail 혼잡이 동시에 있음 -> `HOLD_ENTRY`

주의해서 말할 점:

```text
이 action들은 실제 PLC나 AMR 제어 명령이 아니라, 이후 제어 후보를 판단하기 위한 의사결정 label입니다.
```

### Slide 3. State / Action Log 생성 결과

핵심 메시지:

```text
5분 단위 state 24,221개와 action row 12,465개를 만들었다.
```

설명할 그래프:

- action별 trigger count 그래프
- `PRIORITIZE_DISCHARGE`가 압도적으로 많음
- `SCHEDULE_RAIL`, `CONTROL_WIP`, `HOLD_ENTRY`, `DISPATCH_AMR` 순서로 적어짐

해석:

- A3 후단 문제는 광범위하게 나타남
- A4와 rail 문제는 특정 구간에서 집중적으로 나타남
- AMR 관련 action은 실제 availability 정보가 없어 보수적으로 잡힘

### Slide 4. Replay 평가: A3 후단 반출 Rule

핵심 메시지:

```text
A3 rule은 가장 중요한 후보지만, C2/BUFFER까지 함께 봐야 한다.
```

설명할 그래프:

- A3 action 발생 전후 대기시간 비교
- buffer WIP 변화 비교

해석:

- `PRIORITIZE_DISCHARGE`는 A3 -> AMR 대기를 약간 줄이는 방향
- 하지만 A3 -> C2 대기와 buffer WIP는 명확히 개선되지 않음
- `DISPATCH_AMR`은 A3 -> AMR 대기를 줄이는 신호가 있으나 trigger 수가 적고 C2 대기는 증가

발표 포인트:

```text
A3 문제는 단순히 AMR만 빨리 보내면 해결되는 구조가 아니라, C2 적재와 buffer 흐름까지 함께 봐야 합니다.
```

### Slide 5. Replay 평가: A4 / Rail Rule

핵심 메시지:

```text
A4 CONTROL_WIP는 일부 가능성이 있지만, HOLD_ENTRY와 Rail rule은 정교화가 필요하다.
```

설명할 그래프:

- A4 before/after long count 그래프
- rail before/after congestion 그래프

해석:

- `CONTROL_WIP`는 A4 지표가 소폭 개선되는 방향
- `HOLD_ENTRY`는 오히려 A4 지표가 증가하는 방향
- `SCHEDULE_RAIL`은 혼잡 감지는 하지만 이후 혼잡 완화 신호가 약함

발표 포인트:

```text
특히 rail은 TRN_DEV_ID의 물리 위치가 없기 때문에 어느 구간을 제어해야 하는지 확정할 수 없습니다.
```

### Slide 6. Counterfactual 시뮬레이션 결과

핵심 메시지:

```text
가정 기반으로 보면 A3 후단 대기와 buffer WIP가 개선 action에 민감하다.
```

설명할 그래프:

- scenario wait reduction
- scenario WIP reduction
- scenario action comparison

해석:

- 10%, 20%, 30% 완화 가정 적용
- A3 관련 지표가 완화율에 민감하게 반응
- 다만 실제 개선 효과가 아니라 가정 기반 가능성 평가임

발표 포인트:

```text
이 슬라이드는 실제 효과를 증명하는 것이 아니라, 어떤 지표가 개선되면 전체 병목 완화 가능성이 큰지 보여주는 민감도 분석입니다.
```

### Slide 7. 현재 판단과 다음 단계

핵심 메시지:

```text
A3 우선 반출을 1순위로 보고, A4/Rail rule은 보조 검증과 정교화가 필요하다.
```

정리:

- A3: 최우선 개선 후보
- A4: CONTROL_WIP는 후보, HOLD_ENTRY는 재설계 필요
- Rail: 물리 위치 정보 없이는 제어 확정 어려움
- 다음 단계: LLM decision agent 설계

발표 포인트:

```text
6~7번은 최종 scheduling 알고리즘이 아니라, 이후 LLM agent와 비교할 기준선입니다.
```

## 12. 추가 Slide 8 Todo 내용

슬라이드 제목:

```text
TODO: LLM Scheduling Agent 적용 방향
```

슬라이드 본문 5개 항목:

```text
1. LLM 학습보다 Agent 구조 구현을 먼저 진행
   - 5분 bucket state를 입력으로 받고, scheduling action JSON을 출력

2. Constraint Verifier로 LLM 출력 검증
   - 불가능한 action, 데이터에 없는 확정 판단, schema 오류를 차단

3. Rule Baseline과 동일한 방식으로 오프라인 평가
   - replay/simulation으로 LLM action과 기존 rule action을 비교

4. 실패/성공 케이스를 수집해 학습 데이터셋 후보 생성
   - state, rule action, LLM action, verifier 결과, proxy outcome 저장

5. 평가 결과가 충분할 때 fine-tuning 여부 판단
   - 우선은 prompt + verifier 방식으로 검증하고, 필요 시 학습 단계로 확장
```

Slide 8 발표 대본:

```text
다음 Todo는 LLM을 스케줄링 의사결정에 어떻게 적용할지 정리한 것입니다.

우선 지금 단계에서는 바로 LLM을 학습시키기보다는, agent 구조를 먼저 구현하는 것이 맞습니다.
현재 6번에서 만든 5분 단위 state를 입력으로 넣고, LLM은 PRIORITIZE_DISCHARGE, CONTROL_WIP, SCHEDULE_RAIL 같은 action을 JSON 형태로 출력하게 합니다.

그 다음에는 constraint verifier가 필요합니다.
LLM이 데이터에 없는 AMR 사용 가능 여부나 C2 capacity를 확정해서 말하거나, 실제로 불가능한 action을 내는 것을 막기 위한 검증 단계입니다.

이 구조가 만들어지면 기존 rule baseline과 같은 방식으로 replay와 simulation 평가를 수행합니다.
즉 LLM action이 기존 rule보다 나은지, 최소한 더 나빠지지는 않는지를 오프라인으로 비교합니다.

이 과정에서 성공 케이스와 실패 케이스를 모으면 이후 학습 데이터셋으로 사용할 수 있습니다.
다만 학습은 바로 진행하지 않고, prompt 기반 agent와 verifier 구조가 충분히 동작하는지 확인한 뒤에 fine-tuning 여부를 판단하는 흐름이 적절합니다.
```

## 13. 발표자가 알아야 할 핵심 용어

### State

5분 단위로 요약한 라인 상태다. 예를 들어 buffer WIP, A3 후단 대기, A4 long count, rail event count 등이 들어간다.

### Action

해당 state에서 내릴 수 있는 scheduling 판단 후보다. 실제 설비 제어 명령이 아니라, “이런 제어를 검토해야 한다”는 label이다.

### Replay

Action이 trigger된 시점 전후 60분을 비교하는 관찰 평가다. 실제 action을 적용한 결과가 아니다.

### Counterfactual Simulation

Action이 효과가 있다고 가정하고 after 지표를 10%, 20%, 30% 낮춰 보는 민감도 분석이다.

### Proxy

직접적인 정답 label이 없을 때 사용하는 대체 지표다. 예를 들어 high A3 downstream wait, A4 long window, rail congestion 등이 proxy다.

### Constraint Verifier

LLM이 만든 action이 실제로 가능한지, schema를 지키는지, 데이터에 없는 정보를 확정하지 않는지 검사하는 모듈이다.

## 14. 예상 질문과 답변

### Q1. 6~7번에서 실제 개선 효과가 검증된 건가?

아니다. 실제 설비를 제어한 것이 아니기 때문에 개선 효과를 확정할 수는 없다. 6~7번은 rule 후보를 만들고, 기존 로그에서 그 rule이 병목 상황을 잘 감지하는지와 어떤 지표에 민감한지를 오프라인으로 평가한 것이다.

### Q2. 왜 A3가 가장 중요하게 나오나?

1~5번 분석에서 A3 후단 반출 대기와 BUFFER WIP가 강하게 나타났다. 6번 rule trigger에서도 `PRIORITIZE_DISCHARGE`가 가장 많이 발생했다. 이는 A3 후단 흐름이 전체 병목과 강하게 연결되어 있음을 의미한다.

### Q3. A3는 AMR만 빨리 보내면 해결되나?

아니다. Replay에서 A3 -> AMR 대기는 일부 줄어드는 방향이 보였지만, A3 -> C2 대기와 buffer WIP는 명확히 개선되지 않았다. 따라서 AMR 배정뿐 아니라 C2 적재, 완제품 창고, buffer 흐름을 함께 봐야 한다.

### Q4. A4는 병목이 아닌가?

A4는 병목 후보가 맞다. 다만 A3처럼 가장 직접적인 후단 병목은 아니고, 복합 CELL 처리시간과 rail overlap 때문에 blocking 후보로 보는 것이 정확하다. `CONTROL_WIP`는 일부 개선 가능성이 있지만, 물리 위치 정보 없이는 원인을 확정하기 어렵다.

### Q5. Rail scheduling은 왜 확정하기 어렵나?

DB에는 `TRN_DEV_ID=1~4`가 있지만 이 값이 실제 어느 rail 구간을 의미하는지 확정할 정보가 없다. 따라서 rail 혼잡은 감지할 수 있지만, 어느 물리 구간을 제어해야 하는지는 확정하기 어렵다.

### Q6. LLM은 바로 학습하면 안 되나?

바로 학습하는 것은 비추천이다. 현재 데이터에는 action을 실제 적용했을 때의 정답 label이 없다. 따라서 먼저 LLM agent 구조와 constraint verifier를 구현하고, rule baseline과 같은 방식으로 비교 평가한 뒤 학습 데이터셋을 만들지 결정하는 것이 안전하다.

### Q7. LLM 학습 데이터셋은 어떻게 만들 수 있나?

초기에는 `state_5min.csv`를 input으로, `actions.csv`의 rule action을 weak label로 사용할 수 있다. 이후 LLM action, verifier 결과, replay/simulation outcome, 사람이 수정한 label을 함께 저장해 학습 데이터셋 후보를 만들 수 있다.

## 15. 발표 시 주의할 표현

사용해도 되는 표현:

```text
기존 로그 기준으로 관찰했다.
오프라인 replay 평가를 수행했다.
가정 기반 counterfactual simulation을 수행했다.
개선 가능성이 있는 후보로 볼 수 있다.
추가 검증이 필요하다.
```

피해야 할 표현:

```text
실제로 개선됐다.
현장 적용 시 효과가 보장된다.
AMR 문제로 확정된다.
C2 포화로 확정된다.
이 rail 구간이 문제다.
LLM을 학습하면 바로 최적 scheduling이 가능하다.
```

## 16. 발표 마무리 멘트 예시

```text
정리하면, 6번에서는 기존 병목 분석 결과를 바탕으로 rule-based scheduling baseline을 만들었고,
7번에서는 이 rule을 기존 로그에 replay하고 완화율 가정을 적용해 개선 가능성을 평가했습니다.

현재 가장 먼저 볼 action은 A3 우선 반출이며, A4 CONTROL_WIP는 보조 후보입니다.
Rail과 HOLD_ENTRY는 감지는 가능하지만 물리 위치와 제어 조건이 부족해 정교화가 필요합니다.

다음 단계는 이 rule baseline을 기준선으로 삼아 LLM decision agent를 구현하는 것입니다.
단, 바로 학습하지 않고 prompt 기반 agent와 constraint verifier를 먼저 만들고,
동일한 replay/simulation framework로 rule baseline과 비교한 뒤 학습 여부를 결정하는 흐름이 적절합니다.
```

