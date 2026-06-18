from __future__ import annotations

import argparse
import csv
import math
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from pypdf import PdfReader


TARGET_TABLES: dict[str, list[str]] = {
    "prc_hist_tb": [
        "PRD_SRL_NO",
        "PRD_PLN_NO",
        "CMP_CD",
        "PRD_CD",
        "CMP_LINE_ID",
        "CMP_EQ_ID",
        "PRD_TYP_NO",
        "PRD_LOT",
        "RECE_CD",
        "PRD_WRK_CD",
        "PRD_CYC_TM",
        "MN_CYC_TM",
        "RBT_CYC_TM",
        "REG_DT",
    ],
    "prc_trns_tb": [
        "PRD_SRL_NO",
        "PRD_PLN_NO",
        "CMP_CD",
        "PRD_CD",
        "CMP_LINE_ID",
        "CMP_EQ_ID",
        "PRD_TYP_NO",
        "PRD_LOT",
        "RECE_CD",
        "TRN_CD",
        "TRN_DEV_ID",
        "MBL_NMBR",
        "PRD_WRK_CD",
        "TRN_QNT",
        "REG_DT",
    ],
    "prc_oee_tb": ["IND_CD", "CMP_CD", "CMP_LINE_ID", "CMP_EQ_ID", "PRC_STATUS", "PRC_TM", "REG_DT"],
    "strg_buf_in": [
        "PRD_SRL_NO",
        "PRD_PLN_NO",
        "CMP_CD",
        "PRD_CD",
        "CMP_LINE_ID",
        "CMP_EQ_ID",
        "PRD_TYP_NO",
        "PRD_LOT",
        "RECE_CD",
        "STRG_CD",
        "SLOT_NM",
        "REG_DT",
    ],
    "strg_buf_out": [
        "PRD_SRL_NO",
        "PRD_PLN_NO",
        "CMP_CD",
        "PRD_CD",
        "CMP_LINE_ID",
        "CMP_EQ_ID",
        "PRD_TYP_NO",
        "PRD_LOT",
        "RECE_CD",
        "STRG_CD",
        "SLOT_NM",
        "REG_DT",
    ],
    "strg_fns_in": [
        "PRD_SRL_NO",
        "PRD_PLN_NO",
        "CMP_CD",
        "PRD_CD",
        "CMP_LINE_ID",
        "CMP_EQ_ID",
        "PRD_TYP_NO",
        "PRD_LOT",
        "RECE_CD",
        "STRG_CD",
        "SLOT_NM",
        "REG_DT",
    ],
    "strg_fns_out": [
        "PRD_SRL_NO",
        "PRD_PLN_NO",
        "CMP_CD",
        "PRD_CD",
        "CMP_LINE_ID",
        "CMP_EQ_ID",
        "PRD_LOT",
        "STRG_CD",
        "SLOT_NM",
        "REG_DT",
    ],
    "std_eqpmn_tb": ["CMP_EQ_ID", "CMP_CD", "CMP_LINE_ID", "ORD_EQ", "EQ_IMG", "PRC_CMNT", "REG_DT"],
    "std_strg_cd": ["STRG_CD", "STRG_CMNT", "REG_DT"],
    "std_prdct_tb": ["PRD_CD", "CMP_CD", "CMP_LINE_ID", "PRD_NM", "PRD_STAT", "UNIT", "STD", "PRD_IMG", "REG_DT"],
}

DEFAULT_PRODUCTS = {"PRD1000", "PRD2000", "PRD3001", "PRD3002"}
DEFAULT_CMP_CD = "4188300219"
DEFAULT_LINE_ID = "LN01"

EQUIPMENT_GROUPS = {
    "EQ01": "C1_RAW_STORAGE",
    "EQ02": "AMR_LD90",
    "EQ03": "A1",
    "EQ04": "A2",
    "EQ05": "A3",
    "EQ06": "A4",
    "EQ07": "A5",
    "EQ08": "A6_TESLA",
    "EQ09": "A6_KONA",
    "EQ10": "A7",
    "EQ11": "A8",
    "EQ12": "A9_2",
    "EQ13": "A9_1",
    "EQ14": "AMR_LD250",
    "EQ15": "C2_FINISHED_STORAGE",
}

SEMANTIC_LAYER = {
    "A3": {
        "manual_pages": "14-20",
        "meaning": "완제품/NG 분류, 협동로봇 이송, 2단 적재 대기, IN/OUT 컨베이어, 스토퍼 기반 1개씩 배출 구조",
        "scheduling_hint": "A3 이후 대기는 반출 우선순위, AMR/모바일 컨베이어 배정, 완제품 대기 적재부 여유와 직접 연결된다.",
        "physical_hint": "2단 적재와 1개씩 배출 구조 때문에 출구 용량과 로봇 작업공간이 제한될 수 있다.",
    },
    "A4": {
        "manual_pages": "23-31",
        "meaning": "사상 제거, 레이저 마킹, 산업용 로봇, 협동로봇, 툴체인저, 틸팅 유닛, 3개 파렛트 버퍼가 결합된 복합 공정",
        "scheduling_hint": "제품 종류 혼합, 툴체인지, 버퍼 점유를 고려한 WIP cap과 투입 제어가 일부 효과를 낼 수 있다.",
        "physical_hint": "다중 로봇과 틸팅/레이저/사상 작업이 한 CELL에 결합되어 처리시간 자체가 구조적으로 길 수 있다.",
    },
    "A5": {
        "manual_pages": "32-39",
        "meaning": "핸들 브로칭 가공과 룸미러 가조립, 산업용 로봇, 2SET 버퍼 테이블, 제품별 이송 유닛",
        "scheduling_hint": "제품군별 route 차이와 버퍼 점유를 분리해서 해석해야 한다.",
        "physical_hint": "핸들과 룸미러 작업 내용이 달라 동일 설비 평균만 보면 제품 믹스 영향이 섞일 수 있다.",
    },
    "A6_A7": {
        "manual_pages": "40-53",
        "meaning": "드릴/TAP, 리벳/인서트 압입, 서보 프레스, 협동로봇, 버퍼 테이블이 포함된 가공/압입 구간",
        "scheduling_hint": "제품 종류별 EQ08/EQ09 분기와 A7 압입 순서를 따로 봐야 한다.",
        "physical_hint": "가공/압입은 실제 작업량과 설비 동작 시간이 병목의 주원인일 수 있다.",
    },
    "A9": {
        "manual_pages": "54-61",
        "meaning": "코어 검사, 비전 검사, 직교 이송, 툴체인저, 조립검사, 볼트 공급/체결, 팔레트 대기/버퍼 공간이 결합된 후단 검사/조립 공정",
        "scheduling_hint": "A9 자체보다 A8/A9 공급 균형과 A3 반출 가능 여부를 함께 봐야 한다.",
        "physical_hint": "검사/조립/체결이 묶인 후단 공정이라 작업공간과 버퍼 공간이 제한될 수 있다.",
    },
    "C2_FINISHED_STORAGE": {
        "manual_pages": "77-82",
        "meaning": "완제품 창고(A11), 완제품 버퍼, 제품별 그립툴, 산업용 로봇 분류 적재, 룸미러/핸들 적재 공간",
        "scheduling_hint": "완제품 입고 지연은 제품별 적재 위치, 로봇 분류 작업, 후단 버퍼 여유와 연결된다.",
        "physical_hint": "완제품 버퍼와 적재 공간이 부족하면 A3 이후 반출이 구조적으로 막힌다.",
    },
    "MOBILE_CONVEYOR": {
        "manual_pages": "88-89",
        "meaning": "2개 팔레트 이송 가능, 중간 스토퍼, 얼라인 모터, 감지센서를 가진 제한 용량 이송 자원",
        "scheduling_hint": "팔레트 2개 용량과 목적지 배정을 고려한 dispatching이 핵심이다.",
        "physical_hint": "동시 적재 수량이 제한되어 출구 대기 WIP가 빠르게 커질 수 있다.",
    },
    "MOBILE_MANIPULATOR": {
        "manual_pages": "90-93",
        "meaning": "제품별 그립툴과 완제품 버퍼를 가진 후단 반출/적재 자원",
        "scheduling_hint": "제품 타입별 그립 전환과 완제품 버퍼 상태를 함께 고려해야 한다.",
        "physical_hint": "그립툴/버퍼/제품별 적재 위치가 반출 처리량의 물리 한계가 될 수 있다.",
    },
}


def ensure_dirs(root: Path) -> dict[str, Path]:
    dirs = {
        "data": root / "data",
        "out_data": root / "outputs" / "data",
        "report": root / "outputs" / "report",
        "figures": root / "outputs" / "report" / "figures",
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def convert_token(raw: str, quoted: bool):
    if quoted:
        return raw
    value = raw.strip()
    if value.upper() == "NULL" or value == "":
        return None
    try:
        if re.match(r"^-?\d+$", value):
            return int(value)
        if re.match(r"^-?\d+\.\d+$", value):
            return float(value)
    except ValueError:
        pass
    return value


def parse_insert_values(payload: str) -> Iterator[list]:
    row = []
    current = []
    in_string = False
    escaping = False
    quoted = False
    in_row = False

    for ch in payload:
        if in_string:
            if escaping:
                current.append(ch)
                escaping = False
            elif ch == "\\":
                escaping = True
            elif ch == "'":
                in_string = False
                quoted = True
            else:
                current.append(ch)
            continue

        if ch == "'":
            in_string = True
        elif ch == "(":
            in_row = True
            row = []
            current = []
            quoted = False
        elif ch == "," and in_row:
            row.append(convert_token("".join(current), quoted))
            current = []
            quoted = False
        elif ch == ")" and in_row:
            row.append(convert_token("".join(current), quoted))
            yield row
            row = []
            current = []
            quoted = False
            in_row = False
        elif in_row:
            current.append(ch)


def create_sqlite(sqlite_path: Path) -> sqlite3.Connection:
    if sqlite_path.exists():
        sqlite_path.unlink()
    conn = sqlite3.connect(sqlite_path)
    conn.execute("PRAGMA journal_mode=OFF")
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA temp_store=MEMORY")
    for table, columns in TARGET_TABLES.items():
        col_defs = ", ".join(f'"{col}" TEXT' for col in columns)
        conn.execute(f'DROP TABLE IF EXISTS "{table}"')
        conn.execute(f'CREATE TABLE "{table}" ({col_defs})')
    conn.commit()
    return conn


def should_keep_row(table: str, columns: list[str], row: list) -> bool:
    data = dict(zip(columns, row))
    if data.get("CMP_CD") not in (None, DEFAULT_CMP_CD):
        return False
    if data.get("CMP_LINE_ID") not in (None, DEFAULT_LINE_ID):
        return False
    if table.startswith("prc_") or table.startswith("strg_"):
        if data.get("PRD_TYP_NO") not in (None, "PRDC"):
            return False
        if data.get("PRD_CD") not in (None, *DEFAULT_PRODUCTS):
            return False
    return True


def extract_dump_to_sqlite(sql_path: Path, sqlite_path: Path) -> pd.DataFrame:
    conn = create_sqlite(sqlite_path)
    insert_prefix = "INSERT INTO `"
    counts = Counter()
    kept = Counter()
    batch: dict[str, list[tuple]] = defaultdict(list)
    batch_size = 5000

    with sql_path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.startswith(insert_prefix):
                continue
            end = line.find("`", len(insert_prefix))
            if end < 0:
                continue
            table = line[len(insert_prefix) : end]
            if table not in TARGET_TABLES:
                continue
            marker = " VALUES "
            marker_at = line.find(marker)
            if marker_at < 0:
                continue
            payload = line[marker_at + len(marker) :].rstrip().rstrip(";")
            columns = TARGET_TABLES[table]
            placeholders = ",".join("?" for _ in columns)
            insert_sql = f'INSERT INTO "{table}" VALUES ({placeholders})'
            for row in parse_insert_values(payload):
                counts[table] += 1
                if len(row) != len(columns):
                    continue
                if not should_keep_row(table, columns, row):
                    continue
                batch[table].append(tuple(row))
                kept[table] += 1
                if len(batch[table]) >= batch_size:
                    conn.executemany(insert_sql, batch[table])
                    batch[table].clear()
            if line_no % 100000 == 0:
                conn.commit()

    for table, rows in batch.items():
        if rows:
            placeholders = ",".join("?" for _ in TARGET_TABLES[table])
            conn.executemany(f'INSERT INTO "{table}" VALUES ({placeholders})', rows)
    conn.commit()

    summary = []
    for table in TARGET_TABLES:
        db_rows = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        summary.append({"table": table, "dump_rows_seen": counts[table], "rows_loaded": db_rows})
    conn.close()
    return pd.DataFrame(summary)


def read_table(conn: sqlite3.Connection, table: str) -> pd.DataFrame:
    return pd.read_sql_query(f'SELECT * FROM "{table}"', conn)


def load_tables(sqlite_path: Path) -> dict[str, pd.DataFrame]:
    conn = sqlite3.connect(sqlite_path)
    try:
        return {table: read_table(conn, table) for table in TARGET_TABLES}
    finally:
        conn.close()


def enrich_equipment(df: pd.DataFrame, eq_map: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "CMP_EQ_ID" not in df.columns:
        return df
    result = df.merge(eq_map[["CMP_EQ_ID", "PRC_CMNT", "logical_process"]], on="CMP_EQ_ID", how="left")
    return result


def build_equipment_map(std_eq: pd.DataFrame) -> pd.DataFrame:
    eq_map = std_eq.copy()
    eq_map["logical_process"] = eq_map["CMP_EQ_ID"].map(EQUIPMENT_GROUPS).fillna(eq_map["CMP_EQ_ID"])
    return eq_map


def build_processing_events(prc_hist: pd.DataFrame, eq_map: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if prc_hist.empty:
        return pd.DataFrame(), pd.DataFrame()
    df = prc_hist.copy()
    df["REG_DT"] = pd.to_datetime(df["REG_DT"], errors="coerce")
    df["PRD_CYC_TM"] = pd.to_numeric(df["PRD_CYC_TM"], errors="coerce")
    keys = ["PRD_SRL_NO", "PRD_PLN_NO", "PRD_CD", "CMP_EQ_ID", "RECE_CD"]
    df = df.sort_values(keys + ["REG_DT", "PRD_WRK_CD"])
    starts = defaultdict(list)
    events = []
    anomalies = []

    for row in df.itertuples(index=False):
        rec = row._asdict()
        key = tuple(rec[k] for k in keys)
        code = rec["PRD_WRK_CD"]
        if code == "STR":
            starts[key].append(rec)
        elif code == "END":
            if starts[key]:
                start = starts[key].pop(0)
                start_time = start["REG_DT"]
                end_time = rec["REG_DT"]
                duration = (end_time - start_time).total_seconds() if pd.notna(start_time) and pd.notna(end_time) else math.nan
                events.append(
                    {
                        "PRD_SRL_NO": rec["PRD_SRL_NO"],
                        "PRD_PLN_NO": rec["PRD_PLN_NO"],
                        "PRD_CD": rec["PRD_CD"],
                        "PRD_LOT": rec["PRD_LOT"],
                        "RECE_CD": rec["RECE_CD"],
                        "CMP_EQ_ID": rec["CMP_EQ_ID"],
                        "start_time": start_time,
                        "end_time": end_time,
                        "processing_sec": duration,
                        "reported_cycle_sec": pd.to_numeric(rec["PRD_CYC_TM"], errors="coerce"),
                        "manual_sec": pd.to_numeric(rec["MN_CYC_TM"], errors="coerce"),
                        "robot_cycle_raw": rec["RBT_CYC_TM"],
                    }
                )
            else:
                anomalies.append(
                    {
                        "type": "END_WITHOUT_STR",
                        "PRD_SRL_NO": rec["PRD_SRL_NO"],
                        "CMP_EQ_ID": rec["CMP_EQ_ID"],
                        "REG_DT": rec["REG_DT"],
                    }
                )

    for key, remaining in starts.items():
        for rec in remaining:
            anomalies.append(
                {
                    "type": "STR_WITHOUT_END",
                    "PRD_SRL_NO": rec["PRD_SRL_NO"],
                    "CMP_EQ_ID": rec["CMP_EQ_ID"],
                    "REG_DT": rec["REG_DT"],
                }
            )

    events_df = pd.DataFrame(events)
    if not events_df.empty:
        events_df = enrich_equipment(events_df, eq_map)
        events_df["negative_duration_flag"] = events_df["processing_sec"] < 0
    return events_df, pd.DataFrame(anomalies)


def add_outlier_flags(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return events
    df = events.copy()
    df["iqr_upper_sec"] = math.nan
    df["outlier_flag"] = False
    for eq, idx in df.groupby("CMP_EQ_ID").groups.items():
        series = df.loc[idx, "processing_sec"].dropna()
        if series.empty:
            continue
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        upper = q3 + 1.5 * (q3 - q1)
        df.loc[idx, "iqr_upper_sec"] = upper
        df.loc[idx, "outlier_flag"] = (df.loc[idx, "processing_sec"] > upper) | (df.loc[idx, "processing_sec"] > 600)
    return df


def summarize_processing(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame()
    clean = events[(events["processing_sec"].notna()) & (~events["negative_duration_flag"])]
    rows = []
    for (eq, logical, name), g in clean.groupby(["CMP_EQ_ID", "logical_process", "PRC_CMNT"], dropna=False):
        raw = g["processing_sec"]
        clean_g = g[~g["outlier_flag"]]["processing_sec"]
        rows.append(
            {
                "CMP_EQ_ID": eq,
                "logical_process": logical,
                "equipment_name": name,
                "count_raw": len(raw),
                "count_clean": len(clean_g),
                "mean_sec_raw": raw.mean(),
                "median_sec_raw": raw.median(),
                "p90_sec_raw": raw.quantile(0.9),
                "max_sec_raw": raw.max(),
                "mean_sec_clean": clean_g.mean() if not clean_g.empty else math.nan,
                "median_sec_clean": clean_g.median() if not clean_g.empty else math.nan,
                "p90_sec_clean": clean_g.quantile(0.9) if not clean_g.empty else math.nan,
                "max_sec_clean": clean_g.max() if not clean_g.empty else math.nan,
                "outlier_count": int(g["outlier_flag"].sum()),
            }
        )
    return pd.DataFrame(rows).sort_values("p90_sec_clean", ascending=False, na_position="last")


def build_routes_and_waits(events: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if events.empty:
        return pd.DataFrame(), pd.DataFrame()
    df = events.sort_values(["PRD_SRL_NO", "start_time", "end_time"]).copy()
    routes = df.copy()
    waits = []
    for serial, g in df.groupby("PRD_SRL_NO"):
        g = g.sort_values("start_time").reset_index(drop=True)
        for i in range(len(g) - 1):
            cur = g.iloc[i]
            nxt = g.iloc[i + 1]
            wait = (nxt["start_time"] - cur["end_time"]).total_seconds()
            waits.append(
                {
                    "PRD_SRL_NO": serial,
                    "PRD_CD": cur["PRD_CD"],
                    "from_eq": cur["CMP_EQ_ID"],
                    "from_process": cur["logical_process"],
                    "from_name": cur["PRC_CMNT"],
                    "to_eq": nxt["CMP_EQ_ID"],
                    "to_process": nxt["logical_process"],
                    "to_name": nxt["PRC_CMNT"],
                    "from_end_time": cur["end_time"],
                    "to_start_time": nxt["start_time"],
                    "waiting_sec": wait,
                    "negative_wait_flag": wait < 0,
                }
            )
    return routes, pd.DataFrame(waits)


OPTIONAL_ROUTE_STEPS = {"AMR_LD90", "AMR_LD250", "C2_FINISHED_STORAGE"}


def normalized_route(processes: Iterable[str]) -> tuple[str, ...]:
    return tuple(p for p in processes if p not in OPTIONAL_ROUTE_STEPS)


def is_prefix_route(candidate: tuple[str, ...], normal: tuple[str, ...]) -> bool:
    return len(candidate) <= len(normal) and candidate == normal[: len(candidate)]


def derive_normal_route_filter(routes: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, set[str]]:
    if routes.empty:
        return pd.DataFrame(), pd.DataFrame(), set()
    route_rows = []
    for (prd_cd, serial), g in routes.sort_values(["PRD_SRL_NO", "start_time"]).groupby(["PRD_CD", "PRD_SRL_NO"]):
        route = tuple(g["logical_process"].tolist())
        norm = normalized_route(route)
        route_rows.append(
            {
                "PRD_CD": prd_cd,
                "PRD_SRL_NO": serial,
                "route": " > ".join(route),
                "normalized_route": " > ".join(norm),
                "normalized_route_tuple": norm,
                "step_count": len(route),
                "normalized_step_count": len(norm),
            }
        )
    serial_routes = pd.DataFrame(route_rows)
    normal_rows = []
    normal_by_product: dict[str, tuple[str, ...]] = {}
    for prd_cd, g in serial_routes.groupby("PRD_CD"):
        counts = g["normalized_route_tuple"].value_counts()
        # Prefer the most frequent substantial route; this avoids choosing short
        # incomplete prefixes when a product has many partially logged serials.
        candidates = []
        for route_tuple, count in counts.items():
            if len(route_tuple) >= 4:
                candidates.append((route_tuple, int(count), len(route_tuple)))
        if not candidates:
            candidates = [(route_tuple, int(count), len(route_tuple)) for route_tuple, count in counts.items()]
        candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
        normal_route, support_count, route_len = candidates[0]
        normal_by_product[prd_cd] = normal_route
        total = int(len(g))
        normal_rows.append(
            {
                "PRD_CD": prd_cd,
                "normal_route": " > ".join(normal_route),
                "support_count_exact": support_count,
                "serial_count_total": total,
                "support_ratio_exact": support_count / total if total else 0,
            }
        )
    route_summary = pd.DataFrame(normal_rows)

    keep_flags = []
    reasons = []
    for row in serial_routes.to_dict("records"):
        normal = normal_by_product.get(row["PRD_CD"], ())
        candidate = row["normalized_route_tuple"]
        keep = is_prefix_route(candidate, normal)
        keep_flags.append(keep)
        if keep:
            reasons.append("normal_route_or_prefix")
        else:
            reasons.append("deviates_from_product_normal_route")
    serial_routes["normal_route_flag"] = keep_flags
    serial_routes["filter_reason"] = reasons
    normal_serials = set(serial_routes.loc[serial_routes["normal_route_flag"], "PRD_SRL_NO"])

    normal_counts = serial_routes.groupby("PRD_CD")["normal_route_flag"].agg(normal_serial_count="sum", serial_count_total="count").reset_index()
    normal_counts["normal_serial_ratio"] = normal_counts["normal_serial_count"] / normal_counts["serial_count_total"]
    route_summary = route_summary.merge(normal_counts, on=["PRD_CD", "serial_count_total"], how="left")
    route_summary["analysis_policy"] = "Keep serials whose normalized route is the product normal route or a prefix of it; strip AMR_LD90/AMR_LD250/C2 for route validation only."

    excluded = serial_routes.loc[~serial_routes["normal_route_flag"]].copy()
    excluded = excluded.drop(columns=["normalized_route_tuple"])
    return route_summary, excluded, normal_serials


def summarize_waits(waits: pd.DataFrame) -> pd.DataFrame:
    if waits.empty:
        return pd.DataFrame()
    waits = waits.copy()
    waits["outlier_flag"] = False
    base = waits[(waits["waiting_sec"].notna()) & (~waits["negative_wait_flag"])]
    for transition, idx in base.groupby(["from_process", "to_process"]).groups.items():
        series = waits.loc[idx, "waiting_sec"].dropna()
        if series.empty:
            continue
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        upper = q3 + 1.5 * (q3 - q1)
        waits.loc[idx, "outlier_flag"] = (waits.loc[idx, "waiting_sec"] > upper) | (waits.loc[idx, "waiting_sec"] > 3600)
    clean = waits[(waits["waiting_sec"].notna()) & (~waits["negative_wait_flag"])]
    rows = []
    for keys, g in clean.groupby(["from_eq", "from_process", "to_eq", "to_process"], dropna=False):
        clean_g = g[~g["outlier_flag"]]
        rows.append(
            {
                "from_eq": keys[0],
                "from_process": keys[1],
                "to_eq": keys[2],
                "to_process": keys[3],
                "transition": f"{keys[1]}->{keys[3]}",
                "count": len(g),
                "mean_wait_sec": g["waiting_sec"].mean(),
                "median_wait_sec": g["waiting_sec"].median(),
                "p90_wait_sec": g["waiting_sec"].quantile(0.9),
                "max_wait_sec": g["waiting_sec"].max(),
                "count_clean": len(clean_g),
                "mean_wait_sec_clean": clean_g["waiting_sec"].mean() if not clean_g.empty else math.nan,
                "median_wait_sec_clean": clean_g["waiting_sec"].median() if not clean_g.empty else math.nan,
                "p90_wait_sec_clean": clean_g["waiting_sec"].quantile(0.9) if not clean_g.empty else math.nan,
                "max_wait_sec_clean": clean_g["waiting_sec"].max() if not clean_g.empty else math.nan,
                "outlier_count": int(g["outlier_flag"].sum()),
            }
        )
    return pd.DataFrame(rows).sort_values("p90_wait_sec_clean", ascending=False, na_position="last")


def build_storage_wip(tables: dict[str, pd.DataFrame], normal_serials: set[str] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    event_rows = []
    specs = [
        ("strg_buf_in", "BUFFER", 1),
        ("strg_buf_out", "BUFFER", -1),
        ("strg_fns_in", "FINISHED_STORAGE", 1),
        ("strg_fns_out", "FINISHED_STORAGE", -1),
    ]
    for table, area, delta in specs:
        df = tables[table]
        if df.empty:
            continue
        tmp = df.copy()
        if normal_serials is not None and "PRD_SRL_NO" in tmp.columns:
            tmp = tmp[tmp["PRD_SRL_NO"].isin(normal_serials)]
        tmp["REG_DT"] = pd.to_datetime(tmp["REG_DT"], errors="coerce")
        for row in tmp.itertuples(index=False):
            rec = row._asdict()
            event_rows.append(
                {
                    "event_time": rec["REG_DT"],
                    "area": area,
                    "source_table": table,
                    "PRD_SRL_NO": rec["PRD_SRL_NO"],
                    "PRD_CD": rec["PRD_CD"],
                    "CMP_EQ_ID": rec["CMP_EQ_ID"],
                    "STRG_CD": rec["STRG_CD"],
                    "SLOT_NM": rec["SLOT_NM"],
                    "delta": delta,
                }
            )
    events = pd.DataFrame(event_rows)
    if events.empty:
        return events, pd.DataFrame()
    events = events.sort_values(["area", "event_time", "delta"]).copy()
    events["wip"] = events.groupby("area")["delta"].cumsum()
    summary = (
        events.groupby("area")["wip"]
        .agg(count="count", mean_wip="mean", median_wip="median", max_wip="max")
        .reset_index()
    )
    summary["p90_wip"] = events.groupby("area")["wip"].quantile(0.9).values
    return events, summary


def summarize_occupancy(prc_trns: pd.DataFrame, eq_map: pd.DataFrame, normal_serials: set[str] | None = None) -> pd.DataFrame:
    if prc_trns.empty:
        return pd.DataFrame()
    df = prc_trns.copy()
    if normal_serials is not None and "PRD_SRL_NO" in df.columns:
        df = df[df["PRD_SRL_NO"].isin(normal_serials)]
    df["REG_DT"] = pd.to_datetime(df["REG_DT"], errors="coerce")
    df["TRN_QNT"] = pd.to_numeric(df["TRN_QNT"], errors="coerce")
    df["TRN_DEV_ID"] = pd.to_numeric(df["TRN_DEV_ID"], errors="coerce")
    df = enrich_equipment(df, eq_map)
    # Pair STR to next ARV for the same product/transport/device/mobile-equipment tuple.
    keys = ["PRD_SRL_NO", "TRN_CD", "TRN_DEV_ID", "MBL_NMBR"]
    starts = defaultdict(list)
    rows = []
    for rec in df.sort_values(keys + ["REG_DT"]).to_dict("records"):
        key = tuple(rec.get(k) for k in keys)
        if rec.get("PRD_WRK_CD") == "STR":
            starts[key].append(rec)
        elif rec.get("PRD_WRK_CD") == "ARV" and starts[key]:
            start = starts[key].pop(0)
            duration = (rec["REG_DT"] - start["REG_DT"]).total_seconds()
            rows.append(
                {
                    "PRD_SRL_NO": rec["PRD_SRL_NO"],
                    "PRD_CD": rec["PRD_CD"],
                    "TRN_CD": rec["TRN_CD"],
                    "TRN_DEV_ID": rec["TRN_DEV_ID"],
                    "MBL_NMBR": rec["MBL_NMBR"],
                    "CMP_EQ_ID": rec["CMP_EQ_ID"],
                    "logical_process": rec["logical_process"],
                    "start_time": start["REG_DT"],
                    "end_time": rec["REG_DT"],
                    "occupancy_sec": duration,
                    "TRN_QNT_start": start["TRN_QNT"],
                    "TRN_QNT_end": rec["TRN_QNT"],
                }
            )
    paired = pd.DataFrame(rows)
    if paired.empty:
        # Fallback: summarize observed transport queue quantity by destination/process.
        return (
            df.groupby(["TRN_CD", "TRN_DEV_ID", "MBL_NMBR", "CMP_EQ_ID", "logical_process"], dropna=False)["TRN_QNT"]
            .agg(count="count", mean_trn_qnt="mean", p90_trn_qnt=lambda s: s.quantile(0.9), max_trn_qnt="max")
            .reset_index()
        )
    paired["outlier_flag"] = False
    for keys, idx in paired.groupby(["TRN_CD", "TRN_DEV_ID", "MBL_NMBR", "CMP_EQ_ID"]).groups.items():
        series = paired.loc[idx, "occupancy_sec"].dropna()
        if series.empty:
            continue
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        upper = q3 + 1.5 * (q3 - q1)
        paired.loc[idx, "outlier_flag"] = (paired.loc[idx, "occupancy_sec"] > upper) | (paired.loc[idx, "occupancy_sec"] > 3600)
    summary = (
        paired.groupby(["TRN_CD", "TRN_DEV_ID", "MBL_NMBR", "CMP_EQ_ID", "logical_process"], dropna=False)["occupancy_sec"]
        .agg(count="count", mean_occupancy_sec="mean", median_occupancy_sec="median", max_occupancy_sec="max")
        .reset_index()
    )
    summary["p90_occupancy_sec"] = (
        paired.groupby(["TRN_CD", "TRN_DEV_ID", "MBL_NMBR", "CMP_EQ_ID", "logical_process"], dropna=False)["occupancy_sec"]
        .quantile(0.9)
        .values
    )
    clean = paired[~paired["outlier_flag"]]
    clean_summary = (
        clean.groupby(["TRN_CD", "TRN_DEV_ID", "MBL_NMBR", "CMP_EQ_ID", "logical_process"], dropna=False)["occupancy_sec"]
        .agg(
            count_clean="count",
            mean_occupancy_sec_clean="mean",
            median_occupancy_sec_clean="median",
            max_occupancy_sec_clean="max",
        )
        .reset_index()
    )
    clean_summary["p90_occupancy_sec_clean"] = (
        clean.groupby(["TRN_CD", "TRN_DEV_ID", "MBL_NMBR", "CMP_EQ_ID", "logical_process"], dropna=False)["occupancy_sec"]
        .quantile(0.9)
        .values
    )
    outliers = (
        paired.groupby(["TRN_CD", "TRN_DEV_ID", "MBL_NMBR", "CMP_EQ_ID", "logical_process"], dropna=False)["outlier_flag"]
        .sum()
        .reset_index(name="outlier_count")
    )
    summary = summary.merge(clean_summary, on=["TRN_CD", "TRN_DEV_ID", "MBL_NMBR", "CMP_EQ_ID", "logical_process"], how="left")
    summary = summary.merge(outliers, on=["TRN_CD", "TRN_DEV_ID", "MBL_NMBR", "CMP_EQ_ID", "logical_process"], how="left")
    return summary.sort_values("p90_occupancy_sec_clean", ascending=False, na_position="last")


def summarize_oee(prc_oee: pd.DataFrame, eq_map: pd.DataFrame) -> pd.DataFrame:
    if prc_oee.empty:
        return pd.DataFrame()
    df = prc_oee.copy()
    df["PRC_TM"] = pd.to_numeric(df["PRC_TM"], errors="coerce").fillna(0)
    df = enrich_equipment(df, eq_map)
    pivot = (
        df.pivot_table(index=["CMP_EQ_ID", "logical_process", "PRC_CMNT"], columns="PRC_STATUS", values="PRC_TM", aggfunc="sum", fill_value=0)
        .reset_index()
    )
    for col in ["RUN", "IDLE", "ALARM"]:
        if col not in pivot.columns:
            pivot[col] = 0
    pivot["total_status_sec"] = pivot[["RUN", "IDLE", "ALARM"]].sum(axis=1)
    for col in ["RUN", "IDLE", "ALARM"]:
        pivot[f"{col.lower()}_ratio"] = pivot[col] / pivot["total_status_sec"].replace(0, pd.NA)
    return pivot


def product_family(prd_cd: str) -> str:
    if prd_cd in {"PRD1000", "PRD2000"}:
        return "HANDLE"
    if prd_cd in {"PRD3001", "PRD3002"}:
        return "ROOM_MIRROR"
    return "OTHER"


def build_rail_events(prc_trns: pd.DataFrame, eq_map: pd.DataFrame, normal_serials: set[str]) -> pd.DataFrame:
    if prc_trns.empty:
        return pd.DataFrame()
    df = prc_trns.copy()
    df = df[(df["TRN_CD"] == "TR01") & (df["PRD_SRL_NO"].isin(normal_serials))]
    if df.empty:
        return pd.DataFrame()
    df["REG_DT"] = pd.to_datetime(df["REG_DT"], errors="coerce")
    df["TRN_DEV_ID"] = pd.to_numeric(df["TRN_DEV_ID"], errors="coerce")
    df["TRN_QNT"] = pd.to_numeric(df["TRN_QNT"], errors="coerce").fillna(0)
    df = df[df["TRN_DEV_ID"].between(1, 4)]
    df = enrich_equipment(df, eq_map)
    df["product_family"] = df["PRD_CD"].map(product_family)
    df["bucket_5min"] = df["REG_DT"].dt.floor("5min")
    return df


def build_shared_rail_analysis(
    prc_trns: pd.DataFrame,
    eq_map: pd.DataFrame,
    events: pd.DataFrame,
    waits: pd.DataFrame,
    normal_serials: set[str],
) -> dict[str, pd.DataFrame]:
    rail_events = build_rail_events(prc_trns, eq_map, normal_serials)
    if rail_events.empty:
        return {
            "rail_timeseries": pd.DataFrame(),
            "a4_blocking_windows": pd.DataFrame(),
            "cross_product_delay_matrix": pd.DataFrame(),
            "a4_downstream_lag": pd.DataFrame(),
        }

    rail_timeseries = (
        rail_events.groupby("bucket_5min")
        .agg(
            rail_event_count=("PRD_SRL_NO", "count"),
            rail_product_count=("PRD_SRL_NO", "nunique"),
            rail_qnt_sum=("TRN_QNT", "sum"),
            rail_qnt_mean=("TRN_QNT", "mean"),
            active_rail_count=("TRN_DEV_ID", "nunique"),
            a4_rail_event_count=("logical_process", lambda s: int((s == "A4").sum())),
            a4_rail_qnt_sum=("TRN_QNT", lambda s: float(s[rail_events.loc[s.index, "logical_process"] == "A4"].sum())),
        )
        .reset_index()
    )
    family_counts = (
        rail_events.pivot_table(index="bucket_5min", columns="product_family", values="PRD_SRL_NO", aggfunc="count", fill_value=0)
        .reset_index()
    )
    rail_timeseries = rail_timeseries.merge(family_counts, on="bucket_5min", how="left")
    for col in ["HANDLE", "ROOM_MIRROR"]:
        if col not in rail_timeseries.columns:
            rail_timeseries[col] = 0

    a4 = events[events["logical_process"] == "A4"].copy()
    if not a4.empty:
        threshold = a4["processing_sec"].quantile(0.75)
        a4["a4_long_flag"] = a4["processing_sec"] >= threshold
        a4_long = a4[a4["a4_long_flag"]].copy()
    else:
        threshold = math.nan
        a4_long = pd.DataFrame()

    waits = waits.copy()
    if not waits.empty:
        waits["from_end_time"] = pd.to_datetime(waits["from_end_time"], errors="coerce")
        waits["to_start_time"] = pd.to_datetime(waits["to_start_time"], errors="coerce")
        waits["product_family"] = waits["PRD_CD"].map(product_family)
        waits["waiting_clean_flag"] = (~waits["negative_wait_flag"]) & waits["waiting_sec"].notna() & (waits["waiting_sec"] <= 3600)
    a4_rows = []
    lag_rows = []
    overlap_rows = []
    lag_minutes = [5, 10, 30]
    for row in a4_long.to_dict("records"):
        start = row["start_time"]
        end = row["end_time"]
        if pd.isna(start) or pd.isna(end):
            continue
        overlap = rail_events[(rail_events["REG_DT"] >= start) & (rail_events["REG_DT"] <= end)]
        other_family = "ROOM_MIRROR" if product_family(row["PRD_CD"]) == "HANDLE" else "HANDLE"
        other_overlap = overlap[overlap["product_family"] == other_family]
        same_overlap = overlap[overlap["product_family"] == product_family(row["PRD_CD"])]
        wait_overlap = pd.DataFrame()
        if not waits.empty:
            wait_overlap = waits[
                waits["waiting_clean_flag"]
                & (waits["from_end_time"] <= end)
                & (waits["to_start_time"] >= start)
            ]
        a4_rows.append(
            {
                "PRD_SRL_NO": row["PRD_SRL_NO"],
                "PRD_CD": row["PRD_CD"],
                "product_family": product_family(row["PRD_CD"]),
                "a4_start_time": start,
                "a4_end_time": end,
                "a4_processing_sec": row["processing_sec"],
                "a4_long_threshold_sec": threshold,
                "rail_event_count_overlap": len(overlap),
                "rail_product_count_overlap": overlap["PRD_SRL_NO"].nunique(),
                "active_rail_count_overlap": overlap["TRN_DEV_ID"].nunique(),
                "same_family_rail_events": len(same_overlap),
                "other_family_rail_events": len(other_overlap),
                "other_family_product_count": other_overlap["PRD_SRL_NO"].nunique(),
                "overlap_wait_event_count": len(wait_overlap),
                "overlap_wait_p90_sec": wait_overlap["waiting_sec"].quantile(0.9) if not wait_overlap.empty else 0,
            }
        )
        for fam, g in overlap.groupby("product_family"):
            overlap_rows.append(
                {
                    "a4_product_family": product_family(row["PRD_CD"]),
                    "overlap_product_family": fam,
                    "rail_event_count": len(g),
                    "product_count": g["PRD_SRL_NO"].nunique(),
                    "rail_qnt_sum": g["TRN_QNT"].sum(),
                }
            )
        for mins in lag_minutes:
            lag_end = end + pd.Timedelta(minutes=mins)
            after_rail = rail_events[(rail_events["REG_DT"] > end) & (rail_events["REG_DT"] <= lag_end)]
            after_waits = waits[
                waits["waiting_clean_flag"]
                & (waits["from_end_time"] > end)
                & (waits["from_end_time"] <= lag_end)
            ] if not waits.empty else pd.DataFrame()
            lag_rows.append(
                {
                    "PRD_SRL_NO": row["PRD_SRL_NO"],
                    "PRD_CD": row["PRD_CD"],
                    "a4_processing_sec": row["processing_sec"],
                    "lag_minutes": mins,
                    "rail_event_count_after": len(after_rail),
                    "rail_product_count_after": after_rail["PRD_SRL_NO"].nunique(),
                    "active_rail_count_after": after_rail["TRN_DEV_ID"].nunique(),
                    "waiting_event_count_after": len(after_waits),
                    "waiting_p90_sec_after": after_waits["waiting_sec"].quantile(0.9) if not after_waits.empty else 0,
                    "room_mirror_rail_events_after": int((after_rail["product_family"] == "ROOM_MIRROR").sum()) if not after_rail.empty else 0,
                    "handle_rail_events_after": int((after_rail["product_family"] == "HANDLE").sum()) if not after_rail.empty else 0,
                }
            )

    a4_blocking_windows = pd.DataFrame(a4_rows).sort_values("a4_processing_sec", ascending=False) if a4_rows else pd.DataFrame()
    a4_downstream_lag = pd.DataFrame(lag_rows)
    if overlap_rows:
        cross_product_delay_matrix = (
            pd.DataFrame(overlap_rows)
            .groupby(["a4_product_family", "overlap_product_family"], as_index=False)
            .agg(
                rail_event_count=("rail_event_count", "sum"),
                product_count=("product_count", "sum"),
                rail_qnt_sum=("rail_qnt_sum", "sum"),
            )
        )
    else:
        cross_product_delay_matrix = pd.DataFrame()

    return {
        "rail_timeseries": rail_timeseries.sort_values("bucket_5min"),
        "a4_blocking_windows": a4_blocking_windows,
        "cross_product_delay_matrix": cross_product_delay_matrix,
        "a4_downstream_lag": a4_downstream_lag,
    }


def zscore(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce").fillna(0)
    if s.std(ddof=0) == 0:
        return pd.Series(0, index=s.index)
    return (s - s.mean()) / s.std(ddof=0)


def semantic_for_process(process: str) -> dict[str, str]:
    if process in ("A9_1", "A9_2"):
        return SEMANTIC_LAYER["A9"]
    if process in ("C2_FINISHED_STORAGE",):
        return SEMANTIC_LAYER["C2_FINISHED_STORAGE"]
    if process in SEMANTIC_LAYER:
        return SEMANTIC_LAYER[process]
    if process in ("A6_TESLA", "A6_KONA", "A7"):
        return SEMANTIC_LAYER["A6_A7"]
    return {"meaning": "", "scheduling_hint": "", "physical_hint": "", "manual_pages": ""}


def build_bottleneck_ranking(
    proc_summary: pd.DataFrame,
    wait_summary: pd.DataFrame,
    wip_summary: pd.DataFrame,
    occ_summary: pd.DataFrame,
    oee_summary: pd.DataFrame,
) -> pd.DataFrame:
    processes = set()
    for df, col in [
        (proc_summary, "logical_process"),
        (wait_summary, "to_process"),
        (wait_summary, "from_process"),
        (wip_summary, "area"),
        (occ_summary, "logical_process"),
        (oee_summary, "logical_process"),
    ]:
        if not df.empty and col in df.columns:
            processes.update(str(x) for x in df[col].dropna().unique())

    rows = []
    for process in sorted(processes):
        proc_p90 = 0.0
        if not proc_summary.empty:
            vals = proc_summary.loc[proc_summary["logical_process"] == process, "p90_sec_clean"]
            proc_p90 = float(vals.max()) if not vals.empty and pd.notna(vals.max()) else 0.0
        wait_p90 = 0.0
        if not wait_summary.empty:
            wait_col = "p90_wait_sec_clean" if "p90_wait_sec_clean" in wait_summary.columns else "p90_wait_sec"
            vals = wait_summary.loc[(wait_summary["to_process"] == process) | (wait_summary["from_process"] == process), wait_col]
            wait_p90 = float(vals.max()) if not vals.empty and pd.notna(vals.max()) else 0.0
        wip_p90 = 0.0
        if not wip_summary.empty:
            aliases = {
                "A3": ["BUFFER"],
                "C2_FINISHED_STORAGE": ["FINISHED_STORAGE"],
            }.get(process, [process])
            vals = wip_summary.loc[wip_summary["area"].isin(aliases), "p90_wip"]
            wip_p90 = float(vals.max()) if not vals.empty and pd.notna(vals.max()) else 0.0
        occ_p90 = 0.0
        if not occ_summary.empty and ("p90_occupancy_sec_clean" in occ_summary.columns or "p90_occupancy_sec" in occ_summary.columns):
            occ_col = "p90_occupancy_sec_clean" if "p90_occupancy_sec_clean" in occ_summary.columns else "p90_occupancy_sec"
            vals = occ_summary.loc[occ_summary["logical_process"] == process, occ_col]
            occ_p90 = float(vals.max()) if not vals.empty and pd.notna(vals.max()) else 0.0
        idle_ratio = 0.0
        alarm_ratio = 0.0
        if not oee_summary.empty:
            vals = oee_summary.loc[oee_summary["logical_process"] == process]
            if not vals.empty:
                idle_ratio = float(vals["idle_ratio"].max()) if "idle_ratio" in vals else 0.0
                alarm_ratio = float(vals["alarm_ratio"].max()) if "alarm_ratio" in vals else 0.0
        sem = semantic_for_process(process)
        rows.append(
            {
                "process": process,
                "processing_p90_sec": proc_p90,
                "waiting_p90_sec": wait_p90,
                "wip_p90": wip_p90,
                "occupancy_p90_sec": occ_p90,
                "idle_ratio": idle_ratio,
                "alarm_ratio": alarm_ratio,
                "manual_pages": sem.get("manual_pages", ""),
                "semantic_meaning": sem.get("meaning", ""),
                "semantic_scheduling_hint": sem.get("scheduling_hint", ""),
                "semantic_physical_hint": sem.get("physical_hint", ""),
            }
        )
    ranking = pd.DataFrame(rows)
    if ranking.empty:
        return ranking
    ranking["bottleneck_score"] = (
        zscore(ranking["processing_p90_sec"])
        + zscore(ranking["waiting_p90_sec"])
        + zscore(ranking["wip_p90"])
        + zscore(ranking["occupancy_p90_sec"])
        + zscore(ranking["alarm_ratio"])
    )
    ranking = ranking.sort_values("bottleneck_score", ascending=False).reset_index(drop=True)
    ranking.insert(0, "rank", range(1, len(ranking) + 1))
    return ranking


def classify_schedulability(ranking: pd.DataFrame) -> pd.DataFrame:
    if ranking.empty:
        return ranking
    rows = []
    for row in ranking.to_dict("records"):
        process = row["process"]
        processing = row["processing_p90_sec"]
        waiting = row["waiting_p90_sec"]
        wip = row["wip_p90"]
        occupancy = row["occupancy_p90_sec"]
        if process in {"A3", "AMR_LD250", "C2_FINISHED_STORAGE", "FINISHED_STORAGE", "BUFFER"} and waiting >= processing:
            sched = "Scheduling Feasible"
            action = "PRIORITIZE_DISCHARGE" if process in {"A3", "C2_FINISHED_STORAGE", "FINISHED_STORAGE", "BUFFER"} else "DISPATCH_AMR"
            reason = "후단 반출/저장 흐름의 대기 비중이 커서 AMR/모바일 이송 및 배출 우선순위 조정 여지가 큼"
        elif process in {"A4", "A9_1", "A9_2", "A5", "A6_TESLA", "A6_KONA", "A7"} and processing > max(waiting, occupancy):
            sched = "Physically Constrained" if process == "A4" else "Partially Feasible"
            action = "CONTROL_WIP" if sched == "Partially Feasible" else "REQUIRE_PHYSICAL_CHANGE"
            reason = "공정 자체 처리시간 비중이 커서 순서 조정보다는 설비 작업량/공간/버퍼 구조 영향이 큼"
        elif waiting > 0 or wip > 0 or occupancy > 0:
            sched = "Partially Feasible"
            action = "CONTROL_WIP"
            reason = "대기/WIP/점유 지표가 있어 투입 제한과 우선순위 조정으로 일부 완화 가능"
        else:
            sched = "Insufficient Evidence"
            action = "REQUIRE_MORE_DATA"
            reason = "핵심 지표가 충분하지 않아 판단 근거가 약함"
        rows.append(
            {
                "rank": row["rank"],
                "process": process,
                "bottleneck_score": row["bottleneck_score"],
                "schedulability": sched,
                "recommended_action": action,
                "judgement_reason": reason,
                "physical_recommendation": row["semantic_physical_hint"],
                "scheduling_recommendation": row["semantic_scheduling_hint"],
                "semantic_meaning": row["semantic_meaning"],
            }
        )
    return pd.DataFrame(rows)


def write_semantics_report(path: Path) -> None:
    lines = ["# P-ZONE 공정 의미 해석", ""]
    for key, data in SEMANTIC_LAYER.items():
        lines.extend(
            [
                f"## {key}",
                f"- 매뉴얼 페이지: {data['manual_pages']}",
                f"- 구조 의미: {data['meaning']}",
                f"- 스케줄링 해석: {data['scheduling_hint']}",
                f"- 물리 제약 해석: {data['physical_hint']}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def extract_manual_excerpt(pdf_path: Path) -> pd.DataFrame:
    if not pdf_path.exists():
        return pd.DataFrame()
    page_ranges = {
        "A3": range(14, 21),
        "A4": range(23, 32),
        "A9": range(54, 62),
        "C2/A11": range(77, 83),
        "MOBILE_CONVEYOR": range(88, 90),
        "MOBILE_MANIPULATOR": range(90, 94),
    }
    reader = PdfReader(str(pdf_path))
    rows = []
    for section, pages in page_ranges.items():
        parts = []
        for p in pages:
            if p - 1 < len(reader.pages):
                text = (reader.pages[p - 1].extract_text() or "").replace("\n", " ")
                parts.append(re.sub(r"\s+", " ", text).strip())
        rows.append({"section": section, "pages": f"{min(pages)}-{max(pages)}", "manual_text_excerpt": " ".join(parts)[:2500]})
    return pd.DataFrame(rows)


def write_main_report(
    path: Path,
    load_summary: pd.DataFrame,
    normal_route_summary: pd.DataFrame,
    excluded_route_summary: pd.DataFrame,
    pair_anomalies: pd.DataFrame,
    proc_summary: pd.DataFrame,
    wait_summary: pd.DataFrame,
    wip_summary: pd.DataFrame,
    occ_summary: pd.DataFrame,
    ranking: pd.DataFrame,
    classification: pd.DataFrame,
    shared_rail: dict[str, pd.DataFrame],
) -> None:
    def md_table(df: pd.DataFrame, n: int = 10) -> str:
        if df.empty:
            return "_No data._"
        return df.head(n).to_markdown(index=False)

    lines = [
        "# P-ZONE 병목 분석 리포트",
        "",
        "## 데이터 적재 요약",
        md_table(load_summary, 20),
        "",
        "## STR/END 페어링 품질",
        f"- 페어링 anomaly 건수: {len(pair_anomalies):,}",
        "",
        "## 정상 route 필터",
        md_table(normal_route_summary, 10),
        "",
        f"- 정상 route에서 제외된 serial 수: {excluded_route_summary['PRD_SRL_NO'].nunique() if not excluded_route_summary.empty else 0:,}",
        "",
        "### 제외 route 예시",
        md_table(excluded_route_summary[["PRD_CD", "PRD_SRL_NO", "normalized_route", "filter_reason"]], 12)
        if not excluded_route_summary.empty
        else "_No excluded route._",
        "",
        "## 설비별 처리시간 상위",
        md_table(proc_summary[["logical_process", "equipment_name", "count_clean", "p90_sec_clean", "max_sec_clean", "outlier_count"]], 12)
        if not proc_summary.empty
        else "_No data._",
        "",
        "## 공정 간 대기시간 상위",
        md_table(wait_summary[["transition", "count", "count_clean", "p90_wait_sec_clean", "max_wait_sec_clean", "outlier_count"]], 12)
        if not wait_summary.empty
        else "_No data._",
        "",
        "## WIP 요약",
        md_table(wip_summary, 10),
        "",
        "## 이송/점유 요약",
        md_table(
            occ_summary[
                [
                    "TRN_CD",
                    "TRN_DEV_ID",
                    "MBL_NMBR",
                    "CMP_EQ_ID",
                    "logical_process",
                    "count",
                    "count_clean",
                    "p90_occupancy_sec_clean",
                    "max_occupancy_sec_clean",
                    "outlier_count",
                ]
            ],
            12,
        )
        if not occ_summary.empty and "p90_occupancy_sec_clean" in occ_summary.columns
        else md_table(occ_summary, 12),
        "",
        "## 병목 순위",
        md_table(
            ranking[
                [
                    "rank",
                    "process",
                    "bottleneck_score",
                    "processing_p90_sec",
                    "waiting_p90_sec",
                    "wip_p90",
                    "occupancy_p90_sec",
                    "semantic_meaning",
                ]
            ],
            15,
        )
        if not ranking.empty
        else "_No data._",
        "",
        "## 스케줄링 가능성 분류",
        md_table(
            classification[
                [
                    "rank",
                    "process",
                    "schedulability",
                    "recommended_action",
                    "judgement_reason",
                    "physical_recommendation",
                ]
            ],
            15,
        )
        if not classification.empty
        else "_No data._",
        "",
        "## 공유 레일 Blocking 분석",
        "이 섹션은 A4 장시간 처리 구간과 TR01 공유 레일 이벤트가 시간적으로 겹치는지 확인한다.",
        "",
        "### A4 장시간 처리 window 상위",
        md_table(
            shared_rail.get("a4_blocking_windows", pd.DataFrame())[
                [
                    "PRD_SRL_NO",
                    "PRD_CD",
                    "a4_processing_sec",
                    "rail_event_count_overlap",
                    "rail_product_count_overlap",
                    "active_rail_count_overlap",
                    "other_family_rail_events",
                    "other_family_product_count",
                    "overlap_wait_event_count",
                    "overlap_wait_p90_sec",
                ]
            ],
            12,
        )
        if not shared_rail.get("a4_blocking_windows", pd.DataFrame()).empty
        else "_No data._",
        "",
        "### 제품군 간 레일 overlap",
        md_table(shared_rail.get("cross_product_delay_matrix", pd.DataFrame()), 10),
        "",
        "### A4 종료 후 downstream lag 요약",
        md_table(
            shared_rail.get("a4_downstream_lag", pd.DataFrame())
            .groupby("lag_minutes", as_index=False)
            .agg(
                a4_window_count=("PRD_SRL_NO", "count"),
                mean_rail_events_after=("rail_event_count_after", "mean"),
                mean_products_after=("rail_product_count_after", "mean"),
                mean_wait_events_after=("waiting_event_count_after", "mean"),
                p90_wait_after=("waiting_p90_sec_after", lambda s: s.quantile(0.9)),
                mean_room_mirror_events_after=("room_mirror_rail_events_after", "mean"),
                mean_handle_events_after=("handle_rail_events_after", "mean"),
            )
            if not shared_rail.get("a4_downstream_lag", pd.DataFrame()).empty
            else pd.DataFrame(),
            10,
        ),
        "",
        "### 공유 레일 해석",
        "- `TR01`, `TRN_DEV_ID=1~4`를 공유 레일/이송 자원으로 보았다.",
        "- A4 장시간 처리 window 중 다른 제품군 레일 이벤트가 동시에 많으면 A4 주변 blocking 가능성이 높다.",
        "- 단, 로그만으로 특정 제품이 A4 때문에 직접 막혔다고 단정하지 않고 시간 겹침과 시차 패턴으로 정황을 평가한다.",
        "",
        "## 해석 원칙",
        "- 수치 지표는 병목 후보를 찾는 근거로 사용한다.",
        "- 제품별 정상 route를 통계적으로 먼저 산출하고, 해당 정상 route 또는 정상 prefix에 속하는 serial만 병목 분석에 사용한다.",
        "- 매뉴얼 의미 해석은 해당 병목이 스케줄링 문제인지, 구조적/물리적 제약인지 판단하는 보조 근거로 사용한다.",
        "- A4는 복합 CELL 구조이므로 처리시간 병목이 나오면 우선 물리 제약 가능성을 높게 본다.",
        "- A3/C2/모바일 이송은 후단 반출 흐름이므로 대기시간과 WIP가 높으면 스케줄링 가능성을 우선 검토한다.",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_figures(fig_dir: Path, proc_summary: pd.DataFrame, wait_summary: pd.DataFrame, ranking: pd.DataFrame) -> None:
    sns.set_theme(style="whitegrid")
    if not proc_summary.empty:
        top = proc_summary.head(12).copy()
        plt.figure(figsize=(12, 7))
        sns.barplot(data=top, y="logical_process", x="p90_sec_clean", hue="logical_process", dodge=False, legend=False)
        plt.xlabel("p90 processing seconds, clean")
        plt.ylabel("Process")
        plt.tight_layout()
        plt.savefig(fig_dir / "processing_p90_top.png", dpi=160)
        plt.close()
    if not wait_summary.empty:
        top = wait_summary.head(12).copy()
        plt.figure(figsize=(12, 7))
        sns.barplot(data=top, y="transition", x="p90_wait_sec", hue="transition", dodge=False, legend=False)
        plt.xlabel("p90 waiting seconds")
        plt.ylabel("Transition")
        plt.tight_layout()
        plt.savefig(fig_dir / "waiting_p90_top.png", dpi=160)
        plt.close()
    if not ranking.empty:
        top = ranking.head(12).copy()
        plt.figure(figsize=(12, 7))
        sns.barplot(data=top, y="process", x="bottleneck_score", hue="process", dodge=False, legend=False)
        plt.xlabel("Bottleneck score")
        plt.ylabel("Process")
        plt.tight_layout()
        plt.savefig(fig_dir / "bottleneck_ranking.png", dpi=160)
        plt.close()


def write_shared_rail_figures(fig_dir: Path, shared_rail: dict[str, pd.DataFrame]) -> None:
    sns.set_theme(style="whitegrid")
    rail_ts = shared_rail.get("rail_timeseries", pd.DataFrame())
    if not rail_ts.empty:
        ts = rail_ts.copy()
        ts["bucket_5min"] = pd.to_datetime(ts["bucket_5min"], errors="coerce")
        # Keep the plot readable by showing daily p90 rather than every 5-min point.
        ts["date"] = ts["bucket_5min"].dt.date
        daily = (
            ts.groupby("date", as_index=False)
            .agg(
                rail_qnt_sum_p90=("rail_qnt_sum", lambda s: s.quantile(0.9)),
                active_rail_count_p90=("active_rail_count", lambda s: s.quantile(0.9)),
                a4_rail_events_sum=("a4_rail_event_count", "sum"),
            )
        )
        plt.figure(figsize=(12, 7))
        sns.lineplot(data=daily, x="date", y="rail_qnt_sum_p90", marker="o", label="rail_qnt_sum p90")
        sns.lineplot(data=daily, x="date", y="active_rail_count_p90", marker="o", label="active rail count p90")
        plt.xticks(rotation=45, ha="right")
        plt.xlabel("Date")
        plt.ylabel("Daily value")
        plt.tight_layout()
        plt.savefig(fig_dir / "rail_occupancy_timeseries.png", dpi=160)
        plt.close()

    windows = shared_rail.get("a4_blocking_windows", pd.DataFrame())
    if not windows.empty:
        top = windows.head(25).copy()
        plt.figure(figsize=(12, 7))
        sns.scatterplot(
            data=top,
            x="a4_processing_sec",
            y="rail_event_count_overlap",
            size="other_family_rail_events",
            hue="PRD_CD",
            sizes=(40, 300),
        )
        plt.xlabel("A4 processing seconds")
        plt.ylabel("Rail events overlapping A4 window")
        plt.tight_layout()
        plt.savefig(fig_dir / "a4_processing_vs_rail_occupancy.png", dpi=160)
        plt.close()

        overlap = windows[["PRD_CD", "same_family_rail_events", "other_family_rail_events"]].copy()
        overlap = overlap.head(25).melt(id_vars=["PRD_CD"], var_name="overlap_type", value_name="rail_events")
        plt.figure(figsize=(12, 7))
        sns.barplot(data=overlap, x="PRD_CD", y="rail_events", hue="overlap_type", estimator="mean", errorbar=None)
        plt.xlabel("A4 product")
        plt.ylabel("Mean overlapping rail events")
        plt.tight_layout()
        plt.savefig(fig_dir / "a4_blocking_overlap_by_product_family.png", dpi=160)
        plt.close()

    lag = shared_rail.get("a4_downstream_lag", pd.DataFrame())
    if not lag.empty:
        lag_summary = (
            lag.groupby("lag_minutes", as_index=False)
            .agg(
                rail_event_count_after=("rail_event_count_after", "mean"),
                waiting_event_count_after=("waiting_event_count_after", "mean"),
                waiting_p90_sec_after=("waiting_p90_sec_after", "mean"),
            )
        )
        plt.figure(figsize=(10, 6))
        sns.lineplot(data=lag_summary, x="lag_minutes", y="rail_event_count_after", marker="o", label="rail events")
        sns.lineplot(data=lag_summary, x="lag_minutes", y="waiting_event_count_after", marker="o", label="waiting events")
        plt.xlabel("Minutes after A4 end")
        plt.ylabel("Mean event count")
        plt.tight_layout()
        plt.savefig(fig_dir / "a4_downstream_lag_effect.png", dpi=160)
        plt.close()


def export_outputs(dirs: dict[str, Path], tables: dict[str, pd.DataFrame], outputs: dict[str, pd.DataFrame]) -> None:
    for name, df in outputs.items():
        df.to_csv(dirs["out_data"] / f"{name}.csv", index=False, encoding="utf-8-sig")
    with pd.ExcelWriter(dirs["report"] / "PZONE_analysis_summary.xlsx", engine="openpyxl") as writer:
        for name, df in outputs.items():
            sheet = name[:31]
            df.to_excel(writer, sheet_name=sheet, index=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="P-ZONE bottleneck analysis without MariaDB import.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--sql", type=Path, default=Path("jnb_db_dump_2026-05-07.sql"))
    parser.add_argument("--manual", type=Path, default=Path("전북대학교_매뉴얼_통합본_260323.pdf"))
    parser.add_argument("--force-extract", action="store_true", help="Rebuild SQLite from the SQL dump.")
    args = parser.parse_args()

    root = args.root.resolve()
    dirs = ensure_dirs(root)
    sql_path = (root / args.sql).resolve()
    manual_path = (root / args.manual).resolve()
    sqlite_path = dirs["data"] / "pzone_analysis.sqlite"
    load_summary_path = dirs["out_data"] / "sql_extract_summary.csv"

    if args.force_extract or not sqlite_path.exists():
        print(f"[extract] {sql_path} -> {sqlite_path}")
        load_summary = extract_dump_to_sqlite(sql_path, sqlite_path)
        load_summary.to_csv(load_summary_path, index=False, encoding="utf-8-sig")
    else:
        load_summary = pd.read_csv(load_summary_path) if load_summary_path.exists() else pd.DataFrame()

    print("[analyze] loading SQLite tables")
    tables = load_tables(sqlite_path)
    eq_map = build_equipment_map(tables["std_eqpmn_tb"])
    events_all, pair_anomalies = build_processing_events(tables["prc_hist_tb"], eq_map)
    events_all = add_outlier_flags(events_all)
    all_routes, _ = build_routes_and_waits(events_all)
    normal_route_summary, excluded_route_summary, normal_serials = derive_normal_route_filter(all_routes)
    print(f"[analyze] normal route serials: {len(normal_serials)} / {all_routes['PRD_SRL_NO'].nunique() if not all_routes.empty else 0}")
    events = events_all[events_all["PRD_SRL_NO"].isin(normal_serials)].copy() if normal_serials else events_all.iloc[0:0].copy()
    proc_summary = summarize_processing(events)
    routes, waits = build_routes_and_waits(events)
    wait_summary = summarize_waits(waits)
    wip_timeseries, wip_summary = build_storage_wip(tables, normal_serials)
    occ_summary = summarize_occupancy(tables["prc_trns_tb"], eq_map, normal_serials)
    oee_summary = summarize_oee(tables["prc_oee_tb"], eq_map)
    shared_rail = build_shared_rail_analysis(tables["prc_trns_tb"], eq_map, events, waits, normal_serials)
    ranking = build_bottleneck_ranking(proc_summary, wait_summary, wip_summary, occ_summary, oee_summary)
    classification = classify_schedulability(ranking)
    manual_excerpt = extract_manual_excerpt(manual_path)

    outputs = {
        "sql_extract_summary": load_summary,
        "normal_route_summary": normal_route_summary,
        "excluded_route_summary": excluded_route_summary,
        "all_product_routes_before_filter": all_routes,
        "product_routes": routes,
        "equipment_processing_events": events,
        "equipment_processing_time_summary": proc_summary,
        "transition_waiting_time": wait_summary,
        "transition_waiting_events": waits,
        "wip_timeseries": wip_timeseries,
        "wip_summary": wip_summary,
        "occupancy_summary": occ_summary,
        "oee_summary": oee_summary,
        "bottleneck_ranking": ranking,
        "schedulability_classification": classification,
        "pairing_anomalies": pair_anomalies,
        "manual_semantic_excerpts": manual_excerpt,
        "rail_timeseries": shared_rail["rail_timeseries"],
        "a4_blocking_windows": shared_rail["a4_blocking_windows"],
        "cross_product_delay_matrix": shared_rail["cross_product_delay_matrix"],
        "a4_downstream_lag": shared_rail["a4_downstream_lag"],
    }
    export_outputs(dirs, tables, outputs)
    write_semantics_report(dirs["report"] / "PZONE_process_semantics.md")
    write_main_report(
        dirs["report"] / "PZONE_bottleneck_analysis_report.md",
        load_summary,
        normal_route_summary,
        excluded_route_summary,
        pair_anomalies,
        proc_summary,
        wait_summary,
        wip_summary,
        occ_summary,
        ranking,
        classification,
        shared_rail,
    )
    write_figures(dirs["figures"], proc_summary, wait_summary, ranking)
    write_shared_rail_figures(dirs["figures"], shared_rail)
    print("[done] outputs written under outputs/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
