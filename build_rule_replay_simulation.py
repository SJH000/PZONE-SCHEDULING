from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


BASE = Path("outputs/2026_06_14")
RULE_DATA = BASE / "rule_baseline" / "data"
REPLAY = BASE / "rule_replay"
REPLAY_DATA = REPLAY / "data"
REPLAY_FIG = REPLAY / "figures"
SIM = BASE / "rule_simulation"
SIM_DATA = SIM / "data"
SIM_FIG = SIM / "figures"

WINDOW_MINUTES = 60
MIN_WINDOW_BUCKETS = 6
SCENARIO_REDUCTION_RATES = [0.10, 0.20, 0.30]

ACTION_METRICS = {
    "PRIORITIZE_DISCHARGE": ["a3_to_amr_wait_p90_recent", "a3_to_c2_wait_p90_recent", "buffer_wip"],
    "DISPATCH_AMR": ["a3_to_amr_wait_p90_recent", "a3_to_c2_wait_p90_recent", "buffer_wip"],
    "CONTROL_WIP": ["a4_long_count", "a4_processing_max_sec"],
    "HOLD_ENTRY": ["a4_long_count", "a4_processing_max_sec"],
    "SCHEDULE_RAIL": ["rail_event_count", "active_rail_count"],
}

ACTION_GROUP = {
    "PRIORITIZE_DISCHARGE": "A3",
    "DISPATCH_AMR": "A3",
    "CONTROL_WIP": "A4",
    "HOLD_ENTRY": "A4",
    "SCHEDULE_RAIL": "RAIL",
}


def ensure_dirs() -> None:
    for path in [REPLAY, REPLAY_DATA, REPLAY_FIG, SIM, SIM_DATA, SIM_FIG]:
        path.mkdir(parents=True, exist_ok=True)


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    state = pd.read_csv(RULE_DATA / "state_5min.csv", parse_dates=["bucket_5min"])
    actions = pd.read_csv(RULE_DATA / "actions.csv", parse_dates=["bucket_5min"])
    thresholds = pd.read_csv(RULE_DATA / "rule_thresholds.csv")
    state = state.sort_values("bucket_5min").reset_index(drop=True)
    actions = actions.sort_values(["bucket_5min", "action_priority"]).reset_index(drop=True)
    return state, actions, thresholds


def fmt(value: float, digits: int = 2) -> str:
    if pd.isna(value):
        return "-"
    return f"{float(value):,.{digits}f}"


def evaluate_trigger_windows(state: pd.DataFrame, actions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    state_idx = state.set_index("bucket_5min").sort_index()
    before_delta = pd.Timedelta(minutes=WINDOW_MINUTES)
    after_delta = pd.Timedelta(minutes=WINDOW_MINUTES)

    for action_row in actions.itertuples(index=False):
        action = action_row.action
        metrics = ACTION_METRICS.get(action, [])
        if not metrics:
            continue
        trigger_time = action_row.bucket_5min
        before = state_idx[(state_idx.index >= trigger_time - before_delta) & (state_idx.index < trigger_time)]
        after = state_idx[(state_idx.index > trigger_time) & (state_idx.index <= trigger_time + after_delta)]
        has_window = len(before) >= MIN_WINDOW_BUCKETS and len(after) >= MIN_WINDOW_BUCKETS
        for metric in metrics:
            before_mean = float(before[metric].mean()) if has_window else math.nan
            after_mean = float(after[metric].mean()) if has_window else math.nan
            delta = after_mean - before_mean if has_window else math.nan
            delta_ratio = delta / before_mean if has_window and before_mean not in (0, math.nan) and before_mean != 0 else math.nan
            rows.append(
                {
                    "bucket_5min": trigger_time,
                    "action": action,
                    "action_group": ACTION_GROUP[action],
                    "metric": metric,
                    "before_mean": before_mean,
                    "after_mean": after_mean,
                    "delta": delta,
                    "delta_ratio": delta_ratio,
                    "before_bucket_count": len(before),
                    "after_bucket_count": len(after),
                    "window_status": "ok" if has_window else "insufficient_window",
                    "product_family_context": action_row.product_family_context,
                    "confidence": action_row.confidence,
                }
            )
    return pd.DataFrame(rows)


def summarize_replay(before_after: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    ok = before_after[before_after["window_status"] == "ok"].copy()
    if ok.empty:
        summary = pd.DataFrame()
    else:
        summary = (
            ok.groupby(["action", "action_group", "metric"], dropna=False)
            .agg(
                trigger_metric_rows=("metric", "size"),
                before_mean=("before_mean", "mean"),
                after_mean=("after_mean", "mean"),
                delta_mean=("delta", "mean"),
                delta_ratio_mean=("delta_ratio", "mean"),
                improved_ratio=("delta", lambda s: float((s < 0).mean())),
                worsened_ratio=("delta", lambda s: float((s > 0).mean())),
                unchanged_ratio=("delta", lambda s: float((s == 0).mean())),
            )
            .reset_index()
        )
        summary["interpretation"] = summary.apply(
            lambda r: "improved_after_trigger"
            if r["delta_mean"] < 0
            else "worse_after_trigger"
            if r["delta_mean"] > 0
            else "no_average_change",
            axis=1,
        )

    quality = (
        before_after.groupby(["action", "action_group", "window_status"], dropna=False)
        .size()
        .rename("metric_row_count")
        .reset_index()
    )
    action_trigger_counts = before_after.groupby(["action", "action_group"])["bucket_5min"].nunique().rename("trigger_bucket_count").reset_index()
    quality = quality.merge(action_trigger_counts, on=["action", "action_group"], how="left")
    return summary, quality


def build_counterfactual(before_after: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    ok = before_after[before_after["window_status"] == "ok"].copy()
    rows: list[dict[str, object]] = []
    for row in ok.itertuples(index=False):
        for rate in SCENARIO_REDUCTION_RATES:
            simulated_after = row.after_mean * (1 - rate)
            simulated_delta = simulated_after - row.before_mean
            simulated_delta_ratio = simulated_delta / row.before_mean if row.before_mean else math.nan
            rows.append(
                {
                    "bucket_5min": row.bucket_5min,
                    "action": row.action,
                    "action_group": row.action_group,
                    "metric": row.metric,
                    "reduction_rate": rate,
                    "before_mean": row.before_mean,
                    "observed_after_mean": row.after_mean,
                    "simulated_after_mean": simulated_after,
                    "observed_delta": row.delta,
                    "simulated_delta": simulated_delta,
                    "observed_delta_ratio": row.delta_ratio,
                    "simulated_delta_ratio": simulated_delta_ratio,
                    "assumption": f"after metric reduced by {int(rate * 100)}% when action is effective",
                }
            )
    scenarios = pd.DataFrame(rows)
    if scenarios.empty:
        summary = pd.DataFrame()
    else:
        summary = (
            scenarios.groupby(["action", "action_group", "metric", "reduction_rate"], dropna=False)
            .agg(
                scenario_rows=("metric", "size"),
                before_mean=("before_mean", "mean"),
                observed_after_mean=("observed_after_mean", "mean"),
                simulated_after_mean=("simulated_after_mean", "mean"),
                observed_delta_mean=("observed_delta", "mean"),
                simulated_delta_mean=("simulated_delta", "mean"),
                observed_delta_ratio_mean=("observed_delta_ratio", "mean"),
                simulated_delta_ratio_mean=("simulated_delta_ratio", "mean"),
            )
            .reset_index()
        )
    return scenarios, summary


def save_tables(
    before_after: pd.DataFrame,
    replay_summary: pd.DataFrame,
    action_quality: pd.DataFrame,
    scenarios: pd.DataFrame,
    simulation_summary: pd.DataFrame,
) -> None:
    before_after.to_csv(REPLAY_DATA / "replay_before_after.csv", index=False, encoding="utf-8-sig")
    replay_summary.to_csv(REPLAY_DATA / "replay_effect_summary.csv", index=False, encoding="utf-8-sig")
    action_quality.to_csv(REPLAY_DATA / "replay_action_quality.csv", index=False, encoding="utf-8-sig")
    scenarios.to_csv(SIM_DATA / "counterfactual_scenarios.csv", index=False, encoding="utf-8-sig")
    simulation_summary.to_csv(SIM_DATA / "simulation_effect_summary.csv", index=False, encoding="utf-8-sig")


def plot_before_after(summary: pd.DataFrame, action_filter: list[str], metrics: list[str], path: Path, title: str) -> None:
    df = summary[(summary["action"].isin(action_filter)) & (summary["metric"].isin(metrics))].copy()
    if df.empty:
        return
    plot_df = df.melt(
        id_vars=["action", "metric"],
        value_vars=["before_mean", "after_mean"],
        var_name="period",
        value_name="value",
    )
    plt.figure(figsize=(9, 4.8))
    sns.barplot(data=plot_df, x="metric", y="value", hue="period")
    plt.title(title)
    plt.xlabel("")
    plt.ylabel("Mean value")
    plt.xticks(rotation=18, ha="right")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def make_replay_figures(replay_summary: pd.DataFrame) -> None:
    sns.set_theme(style="whitegrid")
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False
    plot_before_after(
        replay_summary,
        ["PRIORITIZE_DISCHARGE", "DISPATCH_AMR"],
        ["a3_to_amr_wait_p90_recent", "a3_to_c2_wait_p90_recent"],
        REPLAY_FIG / "a3_before_after_wait.png",
        "A3 Actions: Before vs After Wait",
    )
    plot_before_after(
        replay_summary,
        ["PRIORITIZE_DISCHARGE", "DISPATCH_AMR"],
        ["buffer_wip"],
        REPLAY_FIG / "buffer_wip_after_rule.png",
        "A3 Actions: Buffer WIP Before vs After",
    )
    plot_before_after(
        replay_summary,
        ["CONTROL_WIP", "HOLD_ENTRY"],
        ["a4_long_count", "a4_processing_max_sec"],
        REPLAY_FIG / "a4_before_after_long.png",
        "A4 Actions: Before vs After",
    )
    plot_before_after(
        replay_summary,
        ["SCHEDULE_RAIL"],
        ["rail_event_count", "active_rail_count"],
        REPLAY_FIG / "rail_before_after_congestion.png",
        "Rail Action: Before vs After",
    )


def make_simulation_figures(sim_summary: pd.DataFrame) -> None:
    if sim_summary.empty:
        return
    sns.set_theme(style="whitegrid")
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False

    wait = sim_summary[sim_summary["metric"].isin(["a3_to_amr_wait_p90_recent", "a3_to_c2_wait_p90_recent"])]
    if not wait.empty:
        plt.figure(figsize=(9, 4.8))
        sns.lineplot(data=wait, x="reduction_rate", y="simulated_after_mean", hue="metric", style="action", marker="o")
        plt.title("Counterfactual Scenario: A3 Wait Reduction")
        plt.xlabel("Assumed reduction rate")
        plt.ylabel("Simulated after mean")
        plt.tight_layout()
        plt.savefig(SIM_FIG / "scenario_wait_reduction.png", dpi=160)
        plt.close()

    wip = sim_summary[sim_summary["metric"] == "buffer_wip"]
    if not wip.empty:
        plt.figure(figsize=(8, 4.6))
        sns.lineplot(data=wip, x="reduction_rate", y="simulated_after_mean", hue="action", marker="o")
        plt.title("Counterfactual Scenario: Buffer WIP Reduction")
        plt.xlabel("Assumed reduction rate")
        plt.ylabel("Simulated after mean")
        plt.tight_layout()
        plt.savefig(SIM_FIG / "scenario_wip_reduction.png", dpi=160)
        plt.close()

    action_comp = (
        sim_summary.groupby(["action", "reduction_rate"], as_index=False)["simulated_delta_ratio_mean"]
        .mean()
        .sort_values(["action", "reduction_rate"])
    )
    plt.figure(figsize=(9, 4.8))
    sns.barplot(data=action_comp, x="action", y="simulated_delta_ratio_mean", hue="reduction_rate")
    plt.title("Counterfactual Scenario: Action Comparison")
    plt.xlabel("")
    plt.ylabel("Mean simulated delta ratio")
    plt.xticks(rotation=18, ha="right")
    plt.tight_layout()
    plt.savefig(SIM_FIG / "scenario_action_comparison.png", dpi=160)
    plt.close()


def write_reports(replay_summary: pd.DataFrame, action_quality: pd.DataFrame, sim_summary: pd.DataFrame) -> None:
    replay_md = replay_summary.to_markdown(index=False) if not replay_summary.empty else "No replay summary."
    quality_md = action_quality.to_markdown(index=False) if not action_quality.empty else "No action quality."
    sim_md = sim_summary.to_markdown(index=False) if not sim_summary.empty else "No simulation summary."

    replay_report = f"""
# Rule Replay Report

## 목적
6번 rule baseline이 기존 로그에서 trigger된 이후 병목 지표가 어떻게 변했는지 전후 60분 기준으로 관찰했다.

이 결과는 실제 개선 효과 확정이 아니다. action이 실제로 적용된 로그가 아니므로, trigger 이후 자연 변화와 rule 타이밍의 적절성을 보는 오프라인 replay 평가다.

## Replay Effect Summary
{replay_md}

## Action Quality / Window Status
{quality_md}

## 해석 기준
- `delta_mean < 0`: trigger 이후 평균 지표가 낮아진 관찰 결과
- `delta_mean > 0`: trigger 이후 평균 지표가 높아진 관찰 결과
- `improved_ratio`: 개별 trigger-window 중 after가 before보다 낮았던 비율
- `insufficient_window`: trigger 전후 60분 자료가 충분하지 않은 경우

## 한계
- AMR availability, C2 capacity, TRN_DEV_ID 물리 위치가 없다.
- replay는 실제 제어 적용 결과가 아니라 기존 로그의 전후 관찰이다.
- 개선 확정이 아니라 rule 개선과 다음 단계 시뮬레이션/agent 설계를 위한 참고 자료다.
"""
    (REPLAY / "rule_replay_report.md").write_text(replay_report.strip() + "\n", encoding="utf-8")

    sim_report = f"""
# Rule Counterfactual Simulation Report

## 목적
실제 제어 결과가 없으므로, rule action이 after window 지표를 10%, 20%, 30% 완화한다고 가정했을 때의 민감도를 계산했다.

이 결과는 실제 개선율이 아니다. 어떤 action/metric이 완화율 변화에 민감한지 보는 counterfactual 시나리오다.

## Simulation Effect Summary
{sim_md}

## 해석 기준
- `observed_after_mean`: 기존 로그에서 trigger 이후 관측된 평균
- `simulated_after_mean`: action이 해당 비율만큼 효과가 있다고 가정한 평균
- `simulated_delta_ratio_mean`: before 대비 시뮬레이션 after 변화율

## 한계
- 10/20/30% 완화율은 가정값이다.
- AMR, C2, rail 물리 상태를 직접 모델링하지 않는다.
- 실제 throughput 변화나 설비 제어 안정성은 별도 시뮬레이션/현장 검증이 필요하다.
"""
    (SIM / "rule_simulation_report.md").write_text(sim_report.strip() + "\n", encoding="utf-8")


def run() -> None:
    ensure_dirs()
    state, actions, _thresholds = load_inputs()
    before_after = evaluate_trigger_windows(state, actions)
    replay_summary, action_quality = summarize_replay(before_after)
    scenarios, sim_summary = build_counterfactual(before_after)
    save_tables(before_after, replay_summary, action_quality, scenarios, sim_summary)
    make_replay_figures(replay_summary)
    make_simulation_figures(sim_summary)
    write_reports(replay_summary, action_quality, sim_summary)
    print(f"saved replay package: {REPLAY}")
    print(f"saved simulation package: {SIM}")
    print(f"replay rows: {len(before_after)}")
    print(f"scenario rows: {len(scenarios)}")


if __name__ == "__main__":
    run()
