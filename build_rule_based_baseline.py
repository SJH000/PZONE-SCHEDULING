from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


SRC_DATA = Path("outputs/data")
PHASE_DATA = Path("outputs/2026_06_14/phase_1_to_5_analysis/data")
OUT = Path("outputs/2026_06_14/rule_baseline")
OUT_DATA = OUT / "data"
OUT_FIG = OUT / "figures"
REPORT = OUT / "rule_baseline_report.md"

BUCKET = "5min"
RECENT_WINDOW = "60min"
A3_BUFFER_WIP_THRESHOLD = 70
A3_AMR_WAIT_THRESHOLD_SEC = 1200
A3_C2_WAIT_THRESHOLD_SEC = 1800
DISPATCH_AMR_WAIT_THRESHOLD_SEC = 900
A4_LONG_THRESHOLD_SEC = 686.9


def ensure_dirs() -> None:
    for path in [OUT, OUT_DATA, OUT_FIG]:
        path.mkdir(parents=True, exist_ok=True)


def product_family(prd_cd: str) -> str:
    if str(prd_cd) in {"PRD1000", "PRD2000"}:
        return "HANDLE"
    if str(prd_cd) in {"PRD3001", "PRD3002"}:
        return "ROOM_MIRROR"
    return "OTHER"


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def p90(series: pd.Series) -> float:
    s = pd.to_numeric(series, errors="coerce").dropna()
    return float(s.quantile(0.9)) if not s.empty else math.nan


def fmt_num(value: float, digits: int = 1) -> str:
    if pd.isna(value):
        return "-"
    return f"{float(value):,.{digits}f}"


def fmt_pct(value: float) -> str:
    if pd.isna(value):
        return "-"
    return f"{float(value) * 100:.1f}%"


def load_inputs() -> dict[str, pd.DataFrame]:
    routes = read_csv(SRC_DATA / "product_routes.csv")
    waits = read_csv(SRC_DATA / "transition_waiting_events.csv")
    wip = read_csv(SRC_DATA / "wip_timeseries.csv")
    rail = read_csv(SRC_DATA / "rail_timeseries.csv")
    a3 = read_csv(PHASE_DATA / "a3_bottleneck_decomposition.csv")
    a4 = read_csv(PHASE_DATA / "a4_blocking_evidence_summary.csv")
    return {"routes": routes, "waits": waits, "wip": wip, "rail": rail, "a3": a3, "a4": a4}


def build_time_index(data: dict[str, pd.DataFrame]) -> pd.DatetimeIndex:
    times: list[pd.Timestamp] = []
    for col in ["start_time", "end_time"]:
        s = pd.to_datetime(data["routes"][col], errors="coerce")
        times.extend([s.min(), s.max()])
    for col in ["from_end_time", "to_start_time"]:
        s = pd.to_datetime(data["waits"][col], errors="coerce")
        times.extend([s.min(), s.max()])
    s = pd.to_datetime(data["wip"]["event_time"], errors="coerce")
    times.extend([s.min(), s.max()])
    s = pd.to_datetime(data["rail"]["bucket_5min"], errors="coerce")
    times.extend([s.min(), s.max()])
    clean = [t for t in times if pd.notna(t)]
    start = min(clean).floor(BUCKET)
    end = max(clean).ceil(BUCKET)
    return pd.date_range(start=start, end=end, freq=BUCKET)


def build_wip_state(wip: pd.DataFrame, buckets: pd.DatetimeIndex) -> pd.DataFrame:
    df = wip.copy()
    df["event_time"] = pd.to_datetime(df["event_time"], errors="coerce")
    df = df[df["event_time"].notna()].copy()
    df["bucket_5min"] = df["event_time"].dt.floor(BUCKET)
    pivot = pd.DataFrame({"bucket_5min": buckets})
    for area, out_col in [("BUFFER", "buffer_wip"), ("FINISHED_STORAGE", "finished_storage_wip")]:
        g = df[df["area"] == area].sort_values("event_time")
        if g.empty:
            pivot[out_col] = 0
            continue
        last = g.groupby("bucket_5min")["wip"].last().rename(out_col).reset_index()
        pivot = pivot.merge(last, on="bucket_5min", how="left")
        pivot[out_col] = pivot[out_col].ffill().fillna(0)
    return pivot


def build_a3_wait_state(waits: pd.DataFrame, buckets: pd.DatetimeIndex) -> pd.DataFrame:
    df = waits.copy()
    df["to_start_time"] = pd.to_datetime(df["to_start_time"], errors="coerce")
    df["waiting_sec"] = pd.to_numeric(df["waiting_sec"], errors="coerce")
    df = df[(df["from_process"] == "A3") & (df["to_start_time"].notna()) & (df["waiting_sec"].notna())]
    df = df[df["negative_wait_flag"].astype(str).str.lower() != "true"].copy()
    df["transition"] = df["from_process"] + "->" + df["to_process"]
    rows = []
    for bucket in buckets:
        start = bucket - pd.Timedelta(RECENT_WINDOW)
        window = df[(df["to_start_time"] > start) & (df["to_start_time"] <= bucket)]
        amr = window[window["transition"] == "A3->AMR_LD250"]
        c2 = window[window["transition"] == "A3->C2_FINISHED_STORAGE"]
        rows.append(
            {
                "bucket_5min": bucket,
                "a3_to_amr_wait_p90_recent": p90(amr["waiting_sec"]),
                "a3_to_c2_wait_p90_recent": p90(c2["waiting_sec"]),
                "a3_to_amr_wait_event_count_recent": len(amr),
                "a3_to_c2_wait_event_count_recent": len(c2),
            }
        )
    out = pd.DataFrame(rows)
    out[["a3_to_amr_wait_p90_recent", "a3_to_c2_wait_p90_recent"]] = out[
        ["a3_to_amr_wait_p90_recent", "a3_to_c2_wait_p90_recent"]
    ].fillna(0)
    return out


def build_route_state(routes: pd.DataFrame, buckets: pd.DatetimeIndex) -> pd.DataFrame:
    df = routes.copy()
    df["start_time"] = pd.to_datetime(df["start_time"], errors="coerce")
    df["end_time"] = pd.to_datetime(df["end_time"], errors="coerce")
    df["processing_sec"] = pd.to_numeric(df["processing_sec"], errors="coerce")
    a3_done = df[(df["logical_process"] == "A3") & (df["end_time"].notna())].copy()
    a3_done["bucket_5min"] = a3_done["end_time"].dt.floor(BUCKET)
    a3_count = a3_done.groupby("bucket_5min").size().rename("a3_completed_count").reset_index()

    a4 = df[(df["logical_process"] == "A4") & (df["start_time"].notna()) & (df["end_time"].notna())].copy()
    rows = []
    for bucket in buckets:
        bucket_end = bucket + pd.Timedelta(BUCKET)
        active = a4[(a4["start_time"] < bucket_end) & (a4["end_time"] >= bucket)]
        long_active = active[active["processing_sec"] >= A4_LONG_THRESHOLD_SEC]
        rows.append(
            {
                "bucket_5min": bucket,
                "a4_active_count": int(len(active)),
                "a4_long_count": int(len(long_active)),
                "a4_processing_max_sec": float(active["processing_sec"].max()) if not active.empty else 0.0,
            }
        )
    out = pd.DataFrame({"bucket_5min": buckets}).merge(a3_count, on="bucket_5min", how="left")
    out["a3_completed_count"] = out["a3_completed_count"].fillna(0).astype(int)
    out = out.merge(pd.DataFrame(rows), on="bucket_5min", how="left")
    return out


def build_rail_state(rail: pd.DataFrame, buckets: pd.DatetimeIndex) -> tuple[pd.DataFrame, float]:
    df = rail.copy()
    df["bucket_5min"] = pd.to_datetime(df["bucket_5min"], errors="coerce")
    numeric_cols = ["rail_event_count", "active_rail_count", "HANDLE", "ROOM_MIRROR"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    out = pd.DataFrame({"bucket_5min": buckets}).merge(
        df[["bucket_5min", "rail_event_count", "active_rail_count", "HANDLE", "ROOM_MIRROR"]],
        on="bucket_5min",
        how="left",
    )
    out[["rail_event_count", "active_rail_count", "HANDLE", "ROOM_MIRROR"]] = out[
        ["rail_event_count", "active_rail_count", "HANDLE", "ROOM_MIRROR"]
    ].fillna(0)
    out = out.rename(columns={"HANDLE": "handle_rail_events", "ROOM_MIRROR": "room_mirror_rail_events"})
    out["dominant_product_family"] = out.apply(
        lambda r: "HANDLE"
        if r["handle_rail_events"] > r["room_mirror_rail_events"]
        else "ROOM_MIRROR"
        if r["room_mirror_rail_events"] > r["handle_rail_events"]
        else "MIXED_OR_NONE",
        axis=1,
    )
    observed = pd.to_numeric(df["rail_event_count"], errors="coerce").dropna()
    observed = observed[observed > 0]
    rail_p90 = float(observed.quantile(0.9)) if not observed.empty else float(out["rail_event_count"].quantile(0.9))
    return out, rail_p90


def build_state(data: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, dict[str, float]]:
    buckets = build_time_index(data)
    state = pd.DataFrame({"bucket_5min": buckets})
    for part in [
        build_wip_state(data["wip"], buckets),
        build_a3_wait_state(data["waits"], buckets),
        build_route_state(data["routes"], buckets),
    ]:
        state = state.merge(part, on="bucket_5min", how="left")
    rail_state, rail_p90 = build_rail_state(data["rail"], buckets)
    state = state.merge(rail_state, on="bucket_5min", how="left")
    fill_zero = [
        "buffer_wip",
        "finished_storage_wip",
        "a3_completed_count",
        "a3_to_amr_wait_p90_recent",
        "a3_to_c2_wait_p90_recent",
        "a4_active_count",
        "a4_long_count",
        "a4_processing_max_sec",
        "rail_event_count",
        "active_rail_count",
        "handle_rail_events",
        "room_mirror_rail_events",
    ]
    state[fill_zero] = state[fill_zero].fillna(0)
    state["dominant_product_family"] = state["dominant_product_family"].fillna("MIXED_OR_NONE")
    thresholds = {
        "buffer_wip": A3_BUFFER_WIP_THRESHOLD,
        "a3_to_amr_wait_p90_recent": A3_AMR_WAIT_THRESHOLD_SEC,
        "a3_to_c2_wait_p90_recent": A3_C2_WAIT_THRESHOLD_SEC,
        "dispatch_amr_wait_p90_recent": DISPATCH_AMR_WAIT_THRESHOLD_SEC,
        "a4_long_threshold_sec": A4_LONG_THRESHOLD_SEC,
        "rail_event_count_p90": rail_p90,
        "active_rail_count": 4,
    }
    return state.sort_values("bucket_5min").reset_index(drop=True), thresholds


def action_row(
    row: pd.Series,
    action: str,
    target_process: str,
    target_resource: str,
    trigger_rule: str,
    trigger_metric: str,
    trigger_value: float,
    threshold: float,
    confidence: str,
    reason: str,
    limitation: str,
) -> dict[str, object]:
    return {
        "bucket_5min": row["bucket_5min"],
        "action": action,
        "target_process": target_process,
        "target_resource": target_resource,
        "trigger_rule": trigger_rule,
        "trigger_metric": trigger_metric,
        "trigger_value": trigger_value,
        "threshold": threshold,
        "product_family_context": row["dominant_product_family"],
        "confidence": confidence,
        "reason": reason,
        "limitation": limitation,
    }


def build_actions(state: pd.DataFrame, thresholds: dict[str, float]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, row in state.iterrows():
        discharge_triggers = [
            ("buffer_wip", row["buffer_wip"], thresholds["buffer_wip"]),
            ("a3_to_amr_wait_p90_recent", row["a3_to_amr_wait_p90_recent"], thresholds["a3_to_amr_wait_p90_recent"]),
            ("a3_to_c2_wait_p90_recent", row["a3_to_c2_wait_p90_recent"], thresholds["a3_to_c2_wait_p90_recent"]),
        ]
        discharge_hits = [(m, v, t) for m, v, t in discharge_triggers if v >= t]
        if discharge_hits:
            metric, value, threshold = max(discharge_hits, key=lambda x: (x[1] / x[2]) if x[2] else 0)
            rows.append(
                action_row(
                    row,
                    "PRIORITIZE_DISCHARGE",
                    "A3",
                    "BUFFER/AMR_LD250/C2",
                    "A3_DISCHARGE_PRESSURE",
                    metric,
                    value,
                    threshold,
                    "High",
                    "A3 후단 대기 또는 BUFFER WIP가 높아 반출 우선순위를 높이는 후보 상황",
                    "AMR dispatch 로그와 C2 capacity가 없어 실제 원인은 확정하지 않음",
                )
            )

        if row["a3_completed_count"] > 0 and row["a3_to_amr_wait_p90_recent"] >= thresholds["dispatch_amr_wait_p90_recent"]:
            rows.append(
                action_row(
                    row,
                    "DISPATCH_AMR",
                    "A3",
                    "AMR_LD250",
                    "A3_AMR_WAIT",
                    "a3_to_amr_wait_p90_recent",
                    row["a3_to_amr_wait_p90_recent"],
                    thresholds["dispatch_amr_wait_p90_recent"],
                    "Medium",
                    "A3 완료품과 A3->AMR 대기가 함께 관측되어 AMR 배정 후보 상황",
                    "AMR availability가 없어 실제 배정 가능 여부는 판단하지 않음",
                )
            )

        control_wip = row["a4_long_count"] > 0 or row["a4_processing_max_sec"] >= thresholds["a4_long_threshold_sec"]
        schedule_rail = row["rail_event_count"] >= thresholds["rail_event_count_p90"] or row["active_rail_count"] >= thresholds["active_rail_count"]

        if control_wip and schedule_rail:
            rows.append(
                action_row(
                    row,
                    "HOLD_ENTRY",
                    "A4",
                    "A4 entry",
                    "A4_LONG_AND_RAIL_CONGESTION",
                    "a4_long_count+rail_event_count",
                    max(row["a4_long_count"], row["rail_event_count"]),
                    thresholds["rail_event_count_p90"],
                    "Medium",
                    "A4 long window와 rail congestion이 같은 bucket에서 발생해 A4 진입 hold 후보 상황",
                    "TRN_DEV_ID 물리 위치가 없어 실제 blocking 구간은 확정하지 않음",
                )
            )

        if control_wip:
            rows.append(
                action_row(
                    row,
                    "CONTROL_WIP",
                    "A4",
                    "A4 WIP",
                    "A4_LONG_WINDOW",
                    "a4_long_count",
                    row["a4_long_count"],
                    1,
                    "Medium",
                    "A4 long window가 관측되어 A4 주변 WIP cap 후보 상황",
                    "A4 processing을 줄이는 제어가 아니라 진입량 완화 후보임",
                )
            )

        if schedule_rail:
            metric = "rail_event_count" if row["rail_event_count"] >= thresholds["rail_event_count_p90"] else "active_rail_count"
            threshold = thresholds["rail_event_count_p90"] if metric == "rail_event_count" else thresholds["active_rail_count"]
            rows.append(
                action_row(
                    row,
                    "SCHEDULE_RAIL",
                    "TR01",
                    "TRN_DEV_ID=1~4",
                    "RAIL_CONGESTION",
                    metric,
                    row[metric],
                    threshold,
                    "Low",
                    "rail event 밀집 또는 active rail count가 높아 rail scheduling 후보 상황",
                    "TRN_DEV_ID=1~4의 물리 위치가 없어 구체 구간 제어는 확정하지 않음",
                )
            )

    if not rows:
        return pd.DataFrame(
            columns=[
                "bucket_5min",
                "action",
                "target_process",
                "target_resource",
                "trigger_rule",
                "trigger_metric",
                "trigger_value",
                "threshold",
                "product_family_context",
                "confidence",
                "reason",
                "limitation",
            ]
        )
    actions = pd.DataFrame(rows)
    priority = {
        "PRIORITIZE_DISCHARGE": 1,
        "DISPATCH_AMR": 2,
        "HOLD_ENTRY": 3,
        "CONTROL_WIP": 4,
        "SCHEDULE_RAIL": 5,
    }
    actions["action_priority"] = actions["action"].map(priority)
    return actions.sort_values(["bucket_5min", "action_priority"]).reset_index(drop=True)


def build_timeline(state: pd.DataFrame, actions: pd.DataFrame) -> pd.DataFrame:
    timeline = state[["bucket_5min"]].copy()
    for action in ["PRIORITIZE_DISCHARGE", "DISPATCH_AMR", "HOLD_ENTRY", "CONTROL_WIP", "SCHEDULE_RAIL"]:
        buckets = set(actions.loc[actions["action"] == action, "bucket_5min"]) if not actions.empty else set()
        timeline[action] = timeline["bucket_5min"].isin(buckets).astype(int)
    timeline["action_count"] = timeline.drop(columns=["bucket_5min"]).sum(axis=1)
    timeline["no_action"] = (timeline["action_count"] == 0).astype(int)
    return timeline


def overlap_metric(name: str, trigger: pd.Series, target: pd.Series) -> dict[str, object]:
    trigger = trigger.astype(bool)
    target = target.astype(bool)
    overlap = trigger & target
    trigger_count = int(trigger.sum())
    target_count = int(target.sum())
    overlap_count = int(overlap.sum())
    return {
        "proxy": name,
        "target_bucket_count": target_count,
        "trigger_bucket_count": trigger_count,
        "overlap_bucket_count": overlap_count,
        "coverage": overlap_count / target_count if target_count else math.nan,
        "precision": overlap_count / trigger_count if trigger_count else math.nan,
    }


def build_proxy_validation(state: pd.DataFrame, timeline: pd.DataFrame, thresholds: dict[str, float]) -> pd.DataFrame:
    merged = state.merge(timeline, on="bucket_5min", how="left")
    a3_target = (merged["a3_to_amr_wait_p90_recent"] >= thresholds["a3_to_amr_wait_p90_recent"]) | (
        merged["a3_to_c2_wait_p90_recent"] >= thresholds["a3_to_c2_wait_p90_recent"]
    )
    a4_target = merged["a4_long_count"] > 0
    rail_target = (merged["rail_event_count"] >= thresholds["rail_event_count_p90"]) | (
        merged["active_rail_count"] >= thresholds["active_rail_count"]
    )
    rows = [
        overlap_metric("A3 rule vs high A3 downstream wait", merged["PRIORITIZE_DISCHARGE"] == 1, a3_target),
        overlap_metric("A4 rule vs A4 long window", merged["CONTROL_WIP"] == 1, a4_target),
        overlap_metric("Rail rule vs rail congestion", merged["SCHEDULE_RAIL"] == 1, rail_target),
        overlap_metric("Hold entry vs A4+rail combined congestion", merged["HOLD_ENTRY"] == 1, a4_target & rail_target),
    ]
    return pd.DataFrame(rows)


def build_counts(actions: pd.DataFrame, timeline: pd.DataFrame, state: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if actions.empty:
        counts = pd.DataFrame(columns=["action", "trigger_count", "bucket_count", "confidence_modes"])
    else:
        counts = (
            actions.groupby("action")
            .agg(
                trigger_count=("action", "size"),
                bucket_count=("bucket_5min", "nunique"),
                confidence_modes=("confidence", lambda s: ",".join(sorted(s.dropna().unique()))),
            )
            .reset_index()
            .sort_values("trigger_count", ascending=False)
        )
    no_action = int(timeline["no_action"].sum())
    counts = pd.concat(
        [
            counts,
            pd.DataFrame(
                [{"action": "NO_ACTION", "trigger_count": no_action, "bucket_count": no_action, "confidence_modes": ""}]
            ),
        ],
        ignore_index=True,
    )

    if actions.empty:
        family = pd.DataFrame(columns=["action", "product_family_context", "trigger_count"])
    else:
        family = (
            actions.groupby(["action", "product_family_context"])
            .size()
            .rename("trigger_count")
            .reset_index()
            .sort_values(["action", "trigger_count"], ascending=[True, False])
        )
    return counts, family


def write_thresholds(thresholds: dict[str, float]) -> pd.DataFrame:
    rows = [
        ["buffer_wip", thresholds["buffer_wip"], "PRIORITIZE_DISCHARGE", "BUFFER WIP p90 73.1 근처에서 시작"],
        ["a3_to_amr_wait_p90_recent", thresholds["a3_to_amr_wait_p90_recent"], "PRIORITIZE_DISCHARGE", "A3->AMR high wait 감지"],
        ["a3_to_c2_wait_p90_recent", thresholds["a3_to_c2_wait_p90_recent"], "PRIORITIZE_DISCHARGE", "A3->C2 high wait 감지"],
        ["dispatch_amr_wait_p90_recent", thresholds["dispatch_amr_wait_p90_recent"], "DISPATCH_AMR", "AMR dispatch 후보 감지"],
        ["a4_long_threshold_sec", thresholds["a4_long_threshold_sec"], "CONTROL_WIP/HOLD_ENTRY", "기존 A4 long threshold"],
        ["rail_event_count_p90", thresholds["rail_event_count_p90"], "SCHEDULE_RAIL", "현재 데이터 rail event p90"],
        ["active_rail_count", thresholds["active_rail_count"], "SCHEDULE_RAIL", "TRN_DEV_ID=1~4 모두 active인 구간"],
    ]
    return pd.DataFrame(rows, columns=["metric", "threshold", "used_by", "reason"])


def save_outputs(
    state: pd.DataFrame,
    actions: pd.DataFrame,
    timeline: pd.DataFrame,
    counts: pd.DataFrame,
    family: pd.DataFrame,
    proxy: pd.DataFrame,
    thresholds_df: pd.DataFrame,
) -> None:
    state.to_csv(OUT_DATA / "state_5min.csv", index=False, encoding="utf-8-sig")
    actions.to_csv(OUT_DATA / "actions.csv", index=False, encoding="utf-8-sig")
    timeline.to_csv(OUT_DATA / "rule_trigger_timeline.csv", index=False, encoding="utf-8-sig")
    counts.to_csv(OUT_DATA / "rule_trigger_counts.csv", index=False, encoding="utf-8-sig")
    family.to_csv(OUT_DATA / "rule_family_bias.csv", index=False, encoding="utf-8-sig")
    proxy.to_csv(OUT_DATA / "rule_effect_proxy.csv", index=False, encoding="utf-8-sig")
    thresholds_df.to_csv(OUT_DATA / "rule_thresholds.csv", index=False, encoding="utf-8-sig")


def make_figures(state: pd.DataFrame, actions: pd.DataFrame, timeline: pd.DataFrame, counts: pd.DataFrame, thresholds: dict[str, float]) -> None:
    sns.set_theme(style="whitegrid")
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False

    plot_counts = counts[counts["action"] != "NO_ACTION"].copy()
    plt.figure(figsize=(8, 4.5))
    if not plot_counts.empty:
        sns.barplot(data=plot_counts, y="action", x="trigger_count", hue="action", dodge=False, legend=False)
    plt.title("Rule Trigger Counts")
    plt.xlabel("Trigger count")
    plt.ylabel("")
    plt.tight_layout()
    plt.savefig(OUT_FIG / "rule_trigger_counts.png", dpi=160)
    plt.close()

    daily = timeline.copy()
    daily["bucket_5min"] = pd.to_datetime(daily["bucket_5min"])
    daily["date"] = daily["bucket_5min"].dt.date
    action_cols = ["PRIORITIZE_DISCHARGE", "DISPATCH_AMR", "HOLD_ENTRY", "CONTROL_WIP", "SCHEDULE_RAIL"]
    daily_counts = daily.groupby("date")[action_cols].sum().reset_index()
    plt.figure(figsize=(10, 4.8))
    for col in action_cols:
        plt.plot(pd.to_datetime(daily_counts["date"]), daily_counts[col], label=col, linewidth=1.5)
    plt.title("Daily Rule Trigger Timeline")
    plt.xlabel("Date")
    plt.ylabel("Daily trigger buckets")
    plt.legend(loc="upper right", fontsize=8)
    plt.tight_layout()
    plt.savefig(OUT_FIG / "rule_trigger_timeline.png", dpi=160)
    plt.close()

    merged = state.merge(timeline, on="bucket_5min", how="left")
    merged["bucket_5min"] = pd.to_datetime(merged["bucket_5min"])

    plt.figure(figsize=(10, 4.8))
    plt.plot(merged["bucket_5min"], merged["a3_to_amr_wait_p90_recent"], label="A3->AMR recent p90", linewidth=1)
    plt.plot(merged["bucket_5min"], merged["a3_to_c2_wait_p90_recent"], label="A3->C2 recent p90", linewidth=1)
    trigger = merged[merged["PRIORITIZE_DISCHARGE"] == 1]
    plt.scatter(trigger["bucket_5min"], trigger["a3_to_amr_wait_p90_recent"], s=8, color="red", label="PRIORITIZE_DISCHARGE")
    plt.axhline(thresholds["a3_to_amr_wait_p90_recent"], color="red", linestyle="--", linewidth=0.8)
    plt.axhline(thresholds["a3_to_c2_wait_p90_recent"], color="orange", linestyle="--", linewidth=0.8)
    plt.title("A3 Rule vs Downstream Wait")
    plt.xlabel("Time")
    plt.ylabel("Seconds")
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(OUT_FIG / "a3_rule_vs_wait.png", dpi=160)
    plt.close()

    plt.figure(figsize=(10, 4.8))
    plt.plot(merged["bucket_5min"], merged["a4_long_count"], label="A4 long active count", linewidth=1)
    trigger = merged[merged["CONTROL_WIP"] == 1]
    plt.scatter(trigger["bucket_5min"], trigger["a4_long_count"], s=8, color="purple", label="CONTROL_WIP")
    plt.title("A4 Rule vs Long Window")
    plt.xlabel("Time")
    plt.ylabel("Count")
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(OUT_FIG / "a4_rule_vs_long_window.png", dpi=160)
    plt.close()

    plt.figure(figsize=(10, 4.8))
    plt.plot(merged["bucket_5min"], merged["rail_event_count"], label="rail_event_count", linewidth=1)
    trigger = merged[merged["SCHEDULE_RAIL"] == 1]
    plt.scatter(trigger["bucket_5min"], trigger["rail_event_count"], s=8, color="green", label="SCHEDULE_RAIL")
    plt.axhline(thresholds["rail_event_count_p90"], color="green", linestyle="--", linewidth=0.8, label="rail p90")
    plt.title("Rail Rule vs Congestion")
    plt.xlabel("Time")
    plt.ylabel("Rail event count")
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(OUT_FIG / "rail_rule_vs_congestion.png", dpi=160)
    plt.close()


def write_report(
    state: pd.DataFrame,
    actions: pd.DataFrame,
    counts: pd.DataFrame,
    family: pd.DataFrame,
    proxy: pd.DataFrame,
    thresholds_df: pd.DataFrame,
) -> None:
    action_counts = counts[counts["action"] != "NO_ACTION"][["action", "trigger_count", "bucket_count", "confidence_modes"]]
    top_counts_md = action_counts.to_markdown(index=False) if not action_counts.empty else "No action triggers."
    proxy_md = proxy.to_markdown(index=False)
    thresholds_md = thresholds_df.to_markdown(index=False)
    family_md = family.head(20).to_markdown(index=False) if not family.empty else "No action family context."

    report = f"""
# Rule-based Scheduling Baseline Report

## 목적
현장 추가정보 없이 6번 단계를 진행하기 위해, 기존 로그만으로 rule-based scheduling baseline 후보를 만들고 오프라인 proxy 검증을 수행했다.

이 결과는 실제 설비 제어 효과 확정이 아니다. AMR availability, C2 capacity, `TRN_DEV_ID=1~4` 물리 위치가 없으므로 action은 운영 규칙 후보이며, 각 action에 confidence와 limitation을 함께 기록했다.

## 생성 범위
- State bucket: {len(state):,}개
- Action row: {len(actions):,}개
- 분석 bucket 크기: `{BUCKET}`
- recent window: `{RECENT_WINDOW}`
- 출력 경로: `outputs/2026_06_14/rule_baseline/`

## Rule Trigger Counts
{top_counts_md}

## Proxy 검증
{proxy_md}

해석 기준:
- coverage: 실제 병목 proxy bucket 중 rule이 감지한 비율
- precision: rule trigger bucket 중 병목 proxy와 겹친 비율
- 이 값은 개선율이 아니라 감지 성능이다.

## Thresholds
{thresholds_md}

## Product Family Context
{family_md}

## 한계
- `DISPATCH_AMR`는 AMR availability가 없기 때문에 실제 배정 가능 여부를 판단하지 않는다.
- `SCHEDULE_RAIL`은 `TRN_DEV_ID=1~4` 물리 위치가 없어 구체 레일 구간 제어로 해석하지 않는다.
- `PRIORITIZE_DISCHARGE`는 A3 후단 대기와 BUFFER WIP를 감지하지만, AMR 문제인지 C2 포화인지는 확정하지 않는다.
- `HOLD_ENTRY`는 A4 long window와 rail congestion이 같은 bucket에 있는 경우의 후보 action이며, 실제 설비 blocking 확정이 아니다.

## 다음 단계
1. 이 baseline action log를 사용해 LLM decision agent의 입력 state와 출력 action schema를 정의한다.
2. 현장 정보가 확보되면 `TRN_DEV_ID` 물리 위치, AMR dispatch 상태, C2 capacity를 state에 추가한다.
3. 그 후 rule trigger가 실제 대기시간/WIP를 줄이는지 로그 리플레이 또는 시뮬레이션으로 평가한다.
"""
    REPORT.write_text(report.strip() + "\n", encoding="utf-8")


def run() -> None:
    ensure_dirs()
    data = load_inputs()
    state, thresholds = build_state(data)
    actions = build_actions(state, thresholds)
    timeline = build_timeline(state, actions)
    proxy = build_proxy_validation(state, timeline, thresholds)
    counts, family = build_counts(actions, timeline, state)
    thresholds_df = write_thresholds(thresholds)
    save_outputs(state, actions, timeline, counts, family, proxy, thresholds_df)
    make_figures(state, actions, timeline, counts, thresholds)
    write_report(state, actions, counts, family, proxy, thresholds_df)
    print(f"saved rule baseline package: {OUT}")
    print(f"state rows: {len(state)}")
    print(f"action rows: {len(actions)}")


if __name__ == "__main__":
    run()
