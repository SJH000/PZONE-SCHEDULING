# P-ZONE 6~7번 진행 공유 PPT 1분 대본

## 1. 6~7번 진행 목적

이 장은 6번과 7번의 목적을 설명하는 장입니다. 1~5번에서 병목 위치를 찾았고, 6번부터는 개선 가능성을 보기 위한 rule baseline을 만들었습니다. 다만 현장 추가정보가 없기 때문에 실제 설비 제어가 아니라 기존 로그 기반의 오프라인 평가입니다. 6번은 어떤 상황에서 어떤 action을 낼지 정했고, 7번은 그 action이 발생한 시점 전후로 병목 지표가 어떻게 변했는지와 완화 가정 시 어떤 지표가 민감한지 확인했습니다.

## 2. Rule-based Scheduling Baseline 설계

두 번째 장은 rule baseline의 설계 내용입니다. 핵심 action은 다섯 가지입니다. A3 후단 대기나 버퍼 WIP가 높으면 PRIORITIZE_DISCHARGE를 내고, A3 완료품과 AMR 대기가 같이 보이면 DISPATCH_AMR을 냅니다. A4 long window가 있으면 CONTROL_WIP, A4 long과 rail 혼잡이 같이 있으면 HOLD_ENTRY, rail 이벤트가 과도하면 SCHEDULE_RAIL을 냅니다. 단, AMR 가능 여부와 rail 물리 위치 정보가 없기 때문에 action마다 신뢰도를 따로 두었습니다.

## 3. State / Action Log 생성 결과

세 번째 장은 state와 action log 생성 결과입니다. 기존 로그를 5분 단위로 재구성해서 2만 4천여 개 state bucket을 만들었고, 그 위에 rule을 적용해 1만 2천여 개 action row를 생성했습니다. 가장 많이 발생한 것은 PRIORITIZE_DISCHARGE입니다. 이는 A3 후단 압박과 BUFFER WIP를 넓게 잡기 때문입니다. SCHEDULE_RAIL은 rail event p90 이상일 때만 발생하도록 조정했고, DISPATCH_AMR은 AMR availability가 없어서 보수적으로 적게 발생했습니다.

## 4. Replay 평가: A3 후단 반출 Rule

네 번째 장은 A3 후단 반출 rule의 replay 평가입니다. 그래프는 action 발생 전 60분과 후 60분을 비교한 것입니다. PRIORITIZE_DISCHARGE는 A3에서 AMR로 가는 대기는 소폭 낮아지는 경향이 있지만, A3에서 C2로 이어지는 저장 대기와 BUFFER WIP는 뚜렷하게 개선됐다고 보기 어렵습니다. DISPATCH_AMR은 A3->AMR 대기는 줄어드는 방향이지만 trigger 수가 14건으로 적고, AMR 실제 가용 여부가 없기 때문에 확정할 수는 없습니다. 따라서 A3 rule은 우선 검증 후보지만 후단 C2와 buffer 문제를 함께 봐야 합니다.

## 5. Replay 평가: A4 / Rail Rule

다섯 번째 장은 A4와 Rail rule의 replay 결과입니다. CONTROL_WIP는 A4 long count와 A4 processing max가 소폭 낮아지는 관찰 결과가 있습니다. 하지만 HOLD_ENTRY는 trigger 이후 오히려 A4 지표가 증가하는 경향이 있어, 현재 rule만으로는 충분하지 않을 수 있습니다. SCHEDULE_RAIL도 trigger 이후 rail event count가 증가하는 관찰 결과가 있어 자연 개선 신호가 강하지 않습니다. 특히 rail은 TRN_DEV_ID의 물리 위치가 없기 때문에 실제 어느 구간을 조정해야 하는지 확정할 수 없습니다.

## 6. Counterfactual 시뮬레이션 결과

여섯 번째 장은 counterfactual 시뮬레이션입니다. 여기서는 실제 설비가 제어된 것이 아니기 때문에, action이 효과적이었다고 가정하고 after 지표를 10%, 20%, 30% 줄여봤습니다. 이 분석은 실제 개선율을 말하는 것이 아니라, 어떤 지표가 완화율에 민감한지를 보는 것입니다. 결과적으로 A3 후단 대기와 BUFFER WIP는 완화 가정에 민감하게 반응합니다. 즉 A3 우선 반출이나 AMR/C2 연계 개선이 실제로 가능하다면 효과가 날 여지가 큽니다. 다만 이 수치는 가정 기반이므로 실제 제어 효과로 표현하면 안 됩니다.

## 7. 현재 판단과 다음 단계

마지막 장은 현재 판단과 다음 단계입니다. 6번과 7번 결과를 보면, A3 우선 반출 rule은 가장 먼저 검증할 후보입니다. 다만 BUFFER WIP만으로 너무 넓게 trigger되는 문제가 있으므로 후단 대기 조건과 결합해서 정교화해야 합니다. A4 CONTROL_WIP는 보조 개선 후보로 유지할 수 있지만, HOLD_ENTRY는 현재 rule을 재조정할 필요가 있습니다. Rail scheduling은 물리 위치 정보가 없어서 구체 제어로 가기 어렵습니다. 다음 단계는 이 rule baseline을 기준으로 LLM decision agent의 state, action schema, constraint verifier를 설계하고 같은 replay framework로 비교 평가하는 것입니다.
