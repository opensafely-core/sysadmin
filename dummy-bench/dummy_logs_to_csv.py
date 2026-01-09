#!/usr/bin/env python3
"""
Parse legacy/nextgen dummy data logs and emit two CSVs:
- dummy_matches_wide.csv (paired runs with batch data)
- dummy_matches_no_batches.csv (runs filtered out: no batches or exit codes 10/11/12)
"""

import csv
import json
import re
from collections import defaultdict
import subprocess
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
LOGS_ROOT = BASE_DIR / "logs"
QUERY_MODELS_ROOT = BASE_DIR / "query-models"
RESEARCH_ROOT = REPO_ROOT / "research"

NEXTGEN_BATCHES = [0, 1, 2, 3, 4]
NEXTGEN_OLD_BATCHES = [0, 1]
NEXTGEN_TOMW2_BATCHES = [0, 1]
NEXTGEN_TOMW3_BATCHES = [0, 1]
FILTER_EXIT_CODES = {10, 11, 12}
DUMMY_REGEX = re.compile(r"dummy.tables", re.IGNORECASE)
DATA_ROOTS = [
    ("legacy-dummy-data", "legacy"),
    ("nextgen-dummy-data", "nextgen"),
    ("nextgen-old", "nextgen_old"),
    ("nextgen-tomw2", "nextgen_tomw2"),
    ("tomw3", "nextgen_tomw3"),
]


def detect_run_type(log_name: str, analysis: str | None) -> str:
    text = f"{log_name} {analysis or ''}".lower()
    return "measure" if "measure" in text else "dataset"


def calc_dps(found: int | None, total_sec: float | None) -> float | None:
    if found is None or total_sec is None or total_sec <= 0:
        return None
    return found / total_sec


def pct_increase(new: int | None, base: int | None) -> float | None:
    if new is None or base is None or base == 0:
        return None
    return ((new - base) / base) * 100


def pct_reduction(old: float | None, new: float | None) -> float | None:
    if old is None or new is None or old <= 0:
        return None
    return ((old - new) / old) * 100


def symmetric_percent_diff(a: int | float | None, b: int | float | None) -> float | None:
    """Symmetric percent difference; returns None unless both values are positive."""
    if a is None or b is None or a <= 0 or b <= 0:
        return None
    return ((a - b) / ((a + b) / 2)) * 100


def get_population_node_count(project: str, log_name: str) -> int | None:
    stem = Path(log_name).stem
    path = QUERY_MODELS_ROOT / project / "metadata" / f"{stem}.json"
    if not path.exists():
        return None

    text = path.read_text()
    if "Running:" in text:
        text = text.split("Running:")[0].strip()
    try:
        data = json.loads(text)
    except Exception:
        return None
    val = data.get("value", {})
    tuple_list = val.get("tuple") if isinstance(val, dict) else None
    if not tuple_list:
        return None
    root_ref = tuple_list[0].get("ref")
    if not root_ref or root_ref not in data:
        return None
    root = data[root_ref]
    if "Dataset" in root:
        pref = root["Dataset"]["population"]["ref"]
    elif "MeasureCollection" in root:
        mref = root["MeasureCollection"]["items"][0]["ref"]
        pref = data[mref]["Measure"]["population"]["ref"]
    else:
        return None

    def count_nodes(ref: str) -> int:
        stack = [ref]
        seen: set[str] = set()
        while stack:
            r = stack.pop()
            if r in seen or r not in data:
                continue
            seen.add(r)
            node = data[r]
            val = next(iter(node.values()))

            def walk(v):
                if isinstance(v, dict):
                    if "ref" in v:
                        stack.append(v["ref"])
                    else:
                        for vv in v.values():
                            walk(vv)
                elif isinstance(v, list):
                    for vv in v:
                        walk(vv)

            walk(val)
        return len(seen)

    return count_nodes(pref)

def uses_table_from_file(project: str, log_name: str) -> bool:
    """Check definition JSON for InlinePatientTable marker."""
    stem = Path(log_name).stem
    json_path = QUERY_MODELS_ROOT / project / "metadata" / f"{stem}.json"
    if not json_path.exists():
        return False
    try:
        content = json_path.read_text(encoding="utf-8", errors="ignore")
        return "InlinePatientTable" in content
    except Exception:
        return False


def git_primary_author(project: str) -> str:
    repo_path = RESEARCH_ROOT / project
    if not repo_path.exists():
        return ""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "log", "--format=%an"],
            check=True,
            capture_output=True,
            text=True,
        )
        authors = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        authors = [a for a in authors if not a.lower().startswith("dependabot")]
        if not authors:
            return ""
        # count frequency, preserve most recent order by scanning from top
        freq = defaultdict(int)
        order = {}
        for a in authors:
            freq[a] += 1
            if a not in order:
                order[a] = len(order)
        uniq = list(order.keys())
        uniq.sort(key=lambda a: (-freq[a], order[a]))
        return uniq[0] if uniq else ""
    except Exception:
        return ""


def git_head_sha(project: str) -> str | None:
    if not hasattr(git_head_sha, "_cache"):
        git_head_sha._cache = {}  # type: ignore[attr-defined]
    cache = git_head_sha._cache  # type: ignore[attr-defined]
    if project in cache:
        return cache[project]
    repo_path = RESEARCH_ROOT / project
    if not repo_path.exists():
        cache[project] = None
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        cache[project] = result.stdout.strip()
        return cache[project]
    except Exception:
        cache[project] = None
        return None


_dummy_cache: dict[tuple[str, str], bool] = {}
_project_runs: dict[str, dict[str, str]] = {}


def action_uses_dummy_tables(project: str, log_name: str) -> bool:
    key = (project, log_name)
    if key in _dummy_cache:
        return _dummy_cache[key]
    action = Path(log_name).stem
    proj_path = Path("research") / project / "project.yaml"
    if not proj_path.exists():
        _dummy_cache[key] = False
        return False
    if project not in _project_runs:
        try:
            data = yaml.safe_load(proj_path.read_text()) or {}
            acts = data.get("actions") or {}
            run_map = {}
            for name, cfg in acts.items():
                cfg = cfg or {}
                run = cfg.get("run")
                if run:
                    run_map[name] = " ".join(run) if isinstance(run, list) else str(run)
            _project_runs[project] = run_map
        except Exception:
            _project_runs[project] = {}
    run_map = _project_runs.get(project, {})
    run_str = run_map.get(action)
    if not run_str:
        for name, rstr in run_map.items():
            if action in rstr:
                run_str = rstr
                break
    result = "--dummy-tables" in run_str if run_str else False
    _dummy_cache[key] = result
    return result


def round_numeric_values(row: dict) -> dict:
    """Round float values to 2 decimal places."""
    for k, v in list(row.items()):
        if isinstance(v, float):
            row[k] = round(v, 2)
    return row


def parse_log(path: Path) -> dict:
    path = path.resolve()
    rel = path.relative_to(LOGS_ROOT)
    root_name = rel.parts[0]
    method_map = {name: m for name, m in DATA_ROOTS}
    method = method_map.get(root_name, "nextgen")
    project = rel.parts[1]
    analysis = target = overall = exit_code = None
    batches: dict[int, dict] = {}
    has_dummy_tables = False

    def bset(b: int, key: str, val: float) -> None:
        batches.setdefault(b, {})[key] = val

    for line in path.read_text().splitlines():
        if DUMMY_REGEX.search(line):
            has_dummy_tables = True
        if analysis is None and (
            m := re.search(r"Compiling (?:dataset|measure)s? definition(?:s)? from (.+)", line)
        ):
            analysis = m.group(1).strip()
        if target is None and (m := re.search(r"Attempting to generate (\d+) matching patients", line)):
            target = int(m.group(1))
        if overall is None and (m := re.search(r"Dummy data generation took: ([0-9.]+)", line)):
            overall = float(m.group(1))
        if exit_code is None and (m := re.search(r"exit_code: (\d+)", line)):
            exit_code = int(m.group(1))

        if method == "legacy":
            if m := re.search(r"Raw dummy batch: ([0-9.]+)", line):
                bset(0, "raw_sec", float(m.group(1)))
            if m := re.search(r"database\.populate: ([0-9.]+)", line):
                bset(0, "populate_sec", float(m.group(1)))
            if m := re.search(r"engine\.get_results: ([0-9.]+)", line):
                bset(0, "engine_sec", float(m.group(1)))
            if m := re.search(r"accumulate patients from batch: ([0-9.]+)", line):
                bset(0, "accumulate_sec", float(m.group(1)))
            if m := re.search(r"Generated (\d+) patients, found (\d+) matching", line):
                bset(0, "found", int(m.group(2)))
        else:
            if m := re.search(r"batch (\d+): Raw dummy batch: ([0-9.]+)", line):
                bset(int(m.group(1)), "raw_sec", float(m.group(2)))
            if m := re.search(r"batch (\d+): database\.populate: ([0-9.]+)", line):
                bset(int(m.group(1)), "populate_sec", float(m.group(2)))
            if m := re.search(r"batch (\d+): engine\.get_results: ([0-9.]+)", line):
                bset(int(m.group(1)), "engine_sec", float(m.group(2)))
            if m := re.search(r"batch (\d+): accumulate patients from batch: ([0-9.]+)", line):
                bset(int(m.group(1)), "accumulate_sec", float(m.group(2)))
            if m := re.search(r"batch (\d+): found this batch: (\d+)", line):
                bset(int(m.group(1)), "found", int(m.group(2)))

    has_batches = bool(batches)
    if has_batches:
        for b, metrics in batches.items():
            total = sum(metrics.get(k, 0.0) for k in ("raw_sec", "populate_sec", "engine_sec", "accumulate_sec"))
            metrics["total_sec"] = total if method in ("nextgen", "nextgen_old", "nextgen_tomw2", "nextgen_tomw3") else overall

    run_type = detect_run_type(path.name, analysis)

    return {
        "project": project,
        "log_name": path.name,
        "analysis": analysis,
        "method": method,
        "run_type": run_type,
        "batches": batches,
        "target": target,
        "overall_sec": overall,
        "exit_code": exit_code,
        "source_log": str(path),
        "has_batches": has_batches,
        "has_dummy_tables": has_dummy_tables,
    }


def main() -> None:
    records = []
    for root, _method in DATA_ROOTS:
        for p in (LOGS_ROOT / root).glob("*/metadata/*.log"):
            records.append(parse_log(p))

    by_key: dict[tuple[str, str], dict[str, dict]] = defaultdict(dict)
    for rec in records:
        by_key[(rec["project"], rec["log_name"])][rec["method"]] = rec

    paired_rows: list[dict] = []
    filtered_no_batches: list[dict] = []
    filtered_exit: list[dict] = []

    for (project, log_name), pair in by_key.items():
        for rec in pair.values():
            if rec["exit_code"] in FILTER_EXIT_CODES:
                filtered_exit.append(
                    round_numeric_values(
                        {
                            "project": rec["project"],
                            "log_name": rec["log_name"],
                            "method": rec["method"],
                            "analysis_file": rec["analysis"],
                            "run_type": rec["run_type"],
                            "target": rec["target"],
                            "overall_sec": rec["overall_sec"],
                            "exit_code": rec["exit_code"],
                            "source_log": rec["source_log"],
                            "reason": f"exit_code_{rec['exit_code']}",
                        }
                    )
                )
        if any(rec["exit_code"] in FILTER_EXIT_CODES for rec in pair.values()):
            continue

        for rec in pair.values():
            if not rec["has_batches"]:
                reason = "dummy tables" if rec["has_dummy_tables"] else "no dummy batch data"
                filtered_no_batches.append(
                    round_numeric_values(
                        {
                            "project": rec["project"],
                            "log_name": rec["log_name"],
                            "method": rec["method"],
                            "analysis_file": rec["analysis"],
                            "run_type": rec["run_type"],
                            "target": rec["target"],
                            "overall_sec": rec["overall_sec"],
                            "exit_code": rec["exit_code"],
                            "source_log": rec["source_log"],
                            "reason": reason,
                        }
                    )
                )

        if "legacy" not in pair or ("nextgen" not in pair and "nextgen_old" not in pair and "nextgen_tomw2" not in pair):
            continue
        legacy = pair.get("legacy")
        nxt = pair.get("nextgen")
        nxt_old = pair.get("nextgen_old")
        nxt_t2 = pair.get("nextgen_tomw2")
        nxt_t3 = pair.get("nextgen_tomw3")
        # require legacy plus at least one new gen with batches
        if not legacy or not legacy["has_batches"]:
            continue
        if not (
            (nxt and nxt["has_batches"])
            or (nxt_old and nxt_old["has_batches"])
            or (nxt_t2 and nxt_t2["has_batches"])
            or (nxt_t3 and nxt_t3["has_batches"])
        ):
            continue

        # pick primary new-gen for shared fields
        preferred = nxt or nxt_t3 or nxt_t2 or nxt_old

        sha = git_head_sha(project)
        row = {
            "project": project,
            "log_name": log_name,
            "analysis_file": preferred["analysis"] or legacy["analysis"],
            "analysis_link": (
                f"https://github.com/opensafely/{project}/blob/{sha}/{preferred['analysis'] or legacy['analysis']}"
                if ((preferred["analysis"] or legacy["analysis"]) and sha)
                else ""
            ),
            "run_type": preferred["run_type"] or legacy["run_type"],
            "target": preferred["target"] or legacy["target"],
            "users": git_primary_author(project),
            "uses_table_from_file": uses_table_from_file(project, log_name),
            "population_nodes": get_population_node_count(project, log_name),
            "uses_dummy_tables_flag": action_uses_dummy_tables(project, log_name),
            "nextgen_tomw2_exit_code": nxt_t2["exit_code"] if nxt_t2 else None,
            "nextgen_tomw2_overall_sec": nxt_t2["overall_sec"] if nxt_t2 else None,
            "nextgen_tomw3_exit_code": nxt_t3["exit_code"] if nxt_t3 else None,
            "nextgen_tomw3_overall_sec": nxt_t3["overall_sec"] if nxt_t3 else None,
            "legacy_exit_code": legacy["exit_code"],
            "legacy_overall_sec": legacy["overall_sec"],
            "nextgen_exit_code": nxt["exit_code"] if nxt else None,
            "nextgen_overall_sec": nxt["overall_sec"] if nxt else None,
            "nextgen_old_exit_code": nxt_old["exit_code"] if nxt_old else None,
            "nextgen_old_overall_sec": nxt_old["overall_sec"] if nxt_old else None,
            "legacy_batch0_found": legacy["batches"].get(0, {}).get("found"),
            "legacy_batch0_raw_sec": legacy["batches"].get(0, {}).get("raw_sec"),
            "legacy_batch0_populate_sec": legacy["batches"].get(0, {}).get("populate_sec"),
            "legacy_batch0_engine_sec": legacy["batches"].get(0, {}).get("engine_sec"),
            "legacy_batch0_accumulate_sec": legacy["batches"].get(0, {}).get("accumulate_sec"),
            "legacy_batch0_total_sec": legacy["batches"].get(0, {}).get("total_sec"),
            "legacy_batch0_dps": calc_dps(
                legacy["batches"].get(0, {}).get("found"),
                legacy["batches"].get(0, {}).get("total_sec"),
            ),
            "nextgen_batch_improvement": pct_increase(
                nxt["batches"].get(1, {}).get("found") if nxt else None,
                nxt["batches"].get(0, {}).get("found") if nxt else None,
            ),
            "found_diff_pct": symmetric_percent_diff(
                nxt["batches"].get(0, {}).get("found") if nxt else None,
                legacy["batches"].get(0, {}).get("found"),
            ),
            "tomw_improvements_batch0": pct_reduction(
                nxt_old["batches"].get(0, {}).get("total_sec") if nxt_old else None,
                nxt["batches"].get(0, {}).get("total_sec") if nxt else None,
            ),
            "tomw_improvements_batch1": pct_reduction(
                nxt_old["batches"].get(1, {}).get("total_sec") if nxt_old else None,
                nxt["batches"].get(1, {}).get("total_sec") if nxt else None,
            ),
            "tomw2_found_improvement": pct_increase(
                nxt_t2["batches"].get(1, {}).get("found") if nxt_t2 else None,
                nxt["batches"].get(1, {}).get("found") if nxt else None,
            ),
            "tomw3_improvements_batch0": pct_reduction(
                nxt["batches"].get(0, {}).get("total_sec") if nxt else None,
                nxt_t3["batches"].get(0, {}).get("total_sec") if nxt_t3 else None,
            ),
            "tomw3_improvements_batch1": pct_increase(
                nxt_t3["batches"].get(1, {}).get("found") if nxt_t3 else None,
                nxt["batches"].get(1, {}).get("found") if nxt else None,
            ),
        }
        for b in NEXTGEN_BATCHES[:2]:
            m = nxt["batches"].get(b, {}) if nxt else {}
            row.update(
                {
                    f"nextgen_batch{b}_found": m.get("found"),
                    f"nextgen_batch{b}_raw_sec": m.get("raw_sec"),
                    f"nextgen_batch{b}_populate_sec": m.get("populate_sec"),
                    f"nextgen_batch{b}_engine_sec": m.get("engine_sec"),
                    f"nextgen_batch{b}_accumulate_sec": m.get("accumulate_sec"),
                    f"nextgen_batch{b}_total_sec": m.get("total_sec"),
                    f"nextgen_batch{b}_dps": calc_dps(m.get("found"), m.get("total_sec")),
                }
            )
        for b in NEXTGEN_TOMW2_BATCHES:
            m = nxt_t2["batches"].get(b, {}) if nxt_t2 else {}
            row.update(
                {
                    f"nextgen_tomw2_batch{b}_found": m.get("found"),
                    f"nextgen_tomw2_batch{b}_raw_sec": m.get("raw_sec"),
                    f"nextgen_tomw2_batch{b}_populate_sec": m.get("populate_sec"),
                    f"nextgen_tomw2_batch{b}_engine_sec": m.get("engine_sec"),
                    f"nextgen_tomw2_batch{b}_accumulate_sec": m.get("accumulate_sec"),
                    f"nextgen_tomw2_batch{b}_total_sec": m.get("total_sec"),
                    f"nextgen_tomw2_batch{b}_dps": calc_dps(m.get("found"), m.get("total_sec")),
                }
            )
        for b in NEXTGEN_TOMW3_BATCHES:
            m = nxt_t3["batches"].get(b, {}) if nxt_t3 else {}
            row.update(
                {
                    f"nextgen_tomw3_batch{b}_found": m.get("found"),
                    f"nextgen_tomw3_batch{b}_raw_sec": m.get("raw_sec"),
                    f"nextgen_tomw3_batch{b}_populate_sec": m.get("populate_sec"),
                    f"nextgen_tomw3_batch{b}_engine_sec": m.get("engine_sec"),
                    f"nextgen_tomw3_batch{b}_accumulate_sec": m.get("accumulate_sec"),
                    f"nextgen_tomw3_batch{b}_total_sec": m.get("total_sec"),
                    f"nextgen_tomw3_batch{b}_dps": calc_dps(m.get("found"), m.get("total_sec")),
                }
            )
        for b in NEXTGEN_OLD_BATCHES:
            m = nxt_old["batches"].get(b, {}) if nxt_old else {}
            row.update(
                {
                    f"nextgen_old_batch{b}_found": m.get("found"),
                    f"nextgen_old_batch{b}_raw_sec": m.get("raw_sec"),
                    f"nextgen_old_batch{b}_populate_sec": m.get("populate_sec"),
                    f"nextgen_old_batch{b}_engine_sec": m.get("engine_sec"),
                    f"nextgen_old_batch{b}_accumulate_sec": m.get("accumulate_sec"),
                    f"nextgen_old_batch{b}_total_sec": m.get("total_sec"),
                    f"nextgen_old_batch{b}_dps": calc_dps(m.get("found"), m.get("total_sec")),
                }
        )
        paired_rows.append(row)

    paired_rows = [round_numeric_values(r) for r in paired_rows]

    if not paired_rows:
        raise SystemExit("No paired rows found; check log paths and data roots.")

    output_wide = BASE_DIR / "dummy_matches_wide.csv"
    with output_wide.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(paired_rows[0].keys()))
        writer.writeheader()
        writer.writerows(paired_rows)

    filtered_fields = [
        "project",
        "log_name",
        "method",
        "analysis_file",
        "run_type",
        "target",
        "overall_sec",
        "exit_code",
        "source_log",
        "uses_dummy_tables_flag",
        "reason",
    ]
    filtered_combined = filtered_no_batches + filtered_exit
    filtered_combined = [round_numeric_values(r) for r in filtered_combined]
    if filtered_combined:
        output_filtered = BASE_DIR / "dummy_matches_no_batches.csv"
        with output_filtered.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=filtered_fields)
            writer.writeheader()
            writer.writerows(filtered_combined)

    print(f"Wrote {len(paired_rows)} paired rows to {output_wide}")
    print(
        f"Logged {len(filtered_no_batches)} runs without batches and "
        f"{len(filtered_exit)} exit_code in {FILTER_EXIT_CODES} to {output_filtered}"
    )


if __name__ == "__main__":
    main()
