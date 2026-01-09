#!/usr/bin/env python3
import marimo
from pathlib import Path

app = marimo.App(width="wide")


@app.cell
def __():
    import csv
    import pandas as pd
    import altair as alt
    import marimo as mo
    from pathlib import Path
    base_dir = Path(__file__).resolve().parent

    # Load data
    wide_df = pd.read_csv(
        base_dir / "dummy_matches_wide.csv",
        dtype={
            "project": "string",
            "log_name": "string",
            "analysis_file": "string",
            "analysis_link": "string",
            "run_type": "string",
            "users": "string",
        },
    )
    # Column descriptions for tooltips/help
    def load_column_descriptions():
        desc = {}
        try:
            with open(base_dir / "dummy_matches_columns.csv", newline="") as f:
                reader = csv.reader(f)
                next(reader, None)
                for name, text in reader:
                    desc[name] = text
        except Exception:
            pass
        return desc

    column_descriptions = load_column_descriptions()
    # Nextgen found metric: batch0 only
    wide_df["nextgen_found"] = wide_df["nextgen_batch0_found"]

    return (
        mo,
        pd,
        alt,
        wide_df,
        column_descriptions,
    )


@app.cell
def __(
    mo,
    alt,
    wide_df,
    column_descriptions,
):
    # Controls (UI elements only)
    method_filter = mo.ui.multiselect(
        label="Methods", options=["legacy", "nextgen"], value=["legacy", "nextgen"]
    )
    run_type_filter = mo.ui.multiselect(
        label="Run type", options=sorted(wide_df["run_type"].dropna().unique().tolist())
    )
    sort_options = [c for c in wide_df.columns if c.endswith("_found") or c.endswith("_dps")]
    if "found_diff_pct" in wide_df.columns:
        sort_options.append("found_diff_pct")
    if "tomw3_improvements_batch0" in wide_df.columns:
        sort_options.append("tomw3_improvements_batch0")
    if "tomw3_improvements_batch1" in wide_df.columns:
        sort_options.append("tomw3_improvements_batch1")
    sort_col = mo.ui.dropdown(
        label="Sort column",
        options=sort_options,
        value=sort_options[0] if sort_options else "project",
    )
    sort_ascending = mo.ui.switch(value=True, label="Sort ascending")
    page_size = mo.ui.number(value=20, start=5, stop=200, step=5, label="Rows per page")
    column_help_options = [c for c in wide_df.columns if c in column_descriptions]
    column_help = mo.ui.dropdown(
        label="Column help",
        options=column_help_options,
        value=column_help_options[0] if column_help_options else None,
        allow_select_none=True,
    )
    return (
        column_help,
        method_filter,
        page_size,
        run_type_filter,
        sort_ascending,
        sort_col,
    )


@app.cell
def __(
    mo,
    alt,
    wide_df,
    column_descriptions,
    column_help,
    method_filter,
    page_size,
    run_type_filter,
    sort_ascending,
    sort_col,
):
    # Apply filters to the main table
    df = wide_df.copy()
    run_types_selected = run_type_filter.value or []
    if run_types_selected:
        df = df[df["run_type"].isin(run_types_selected)]
    df = df.sort_values(sort_col.value, ascending=sort_ascending.value)

    # Geometric mean of improvements
    gm_col = "tomw_improvements_batch0"
    gm_text = "Geometric mean improvement (batch0): n/a"
    gm2_text = "Geometric mean tomw2 found improvement (batch1): n/a"
    gm3_text = "Geometric mean tomw3 improvement (batch0): n/a"
    gm4_text = "Geometric mean tomw3 found improvement (batch1): n/a"
    if gm_col in df.columns and "nextgen_batch0_total_sec" in df.columns and "nextgen_old_batch0_total_sec" in df.columns:
        # Filter by runtime >= 1s for both
        mask = (
            df[gm_col].notna()
            & df["nextgen_batch0_total_sec"].notna()
            & df["nextgen_batch0_total_sec"].ge(1)
            & df["nextgen_old_batch0_total_sec"].notna()
            & df["nextgen_old_batch0_total_sec"].ge(1)
        )
        vals = df.loc[mask, gm_col]
        vals = vals[vals > -100]  # guard against extreme negatives
        vals = vals + 100  # convert reduction % into ratio base (100% -> 200, 0% ->100)
        if len(vals) > 0:
            import numpy as np

            gm = float(np.exp(np.log(vals).mean()) - 100)
            gm_text = f"Geometric mean improvement (batch0): {gm:.2f}%"
    if "tomw2_found_improvement" in df.columns and "nextgen_batch1_found" in df.columns and "nextgen_tomw2_batch1_found" in df.columns:
        vals2 = df["tomw2_found_improvement"].dropna()
        vals2 = vals2[vals2 > -100]
        vals2 = vals2 + 100
        if len(vals2) > 0:
            import numpy as np

            gm2 = float(np.exp(np.log(vals2).mean()) - 100)
            gm2_text = f"Geometric mean tomw2 found improvement (batch1): {gm2:.2f}%"
    if "tomw3_improvements_batch0" in df.columns and "nextgen_batch0_total_sec" in df.columns and "nextgen_tomw3_batch0_total_sec" in df.columns:
        vals3 = df["tomw3_improvements_batch0"].dropna()
        vals3 = vals3[vals3 > -100]
        vals3 = vals3 + 100
        if len(vals3) > 0:
            import numpy as np

            gm3 = float(np.exp(np.log(vals3).mean()) - 100)
            gm3_text = f"Geometric mean tomw3 improvement (batch0): {gm3:.2f}%"
    if "tomw3_improvements_batch1" in df.columns and "nextgen_batch1_found" in df.columns and "nextgen_tomw3_batch1_found" in df.columns:
        vals4 = df["tomw3_improvements_batch1"].dropna()
        vals4 = vals4[vals4 > -100]
        vals4 = vals4 + 100
        if len(vals4) > 0:
            import numpy as np

            gm4 = float(np.exp(np.log(vals4).mean()) - 100)
            gm4_text = f"Geometric mean tomw3 found improvement (batch1): {gm4:.2f}%"

    # Prepare chart data from found columns (batch 0 only), split by run_type
    def make_found_hist(subdf: pd.DataFrame, title: str):
        records = []
        found_cols = [c for c in subdf.columns if c.endswith("_found") and ("batch0" in c)]
        for col in found_cols:
            method = "legacy" if col.startswith("legacy_") else "nextgen"
            if method not in method_filter.value:
                continue
            batch = col.replace("_found", "").replace("legacy_batch", "").replace("nextgen_batch", "")
            for val in subdf[col].dropna():
                records.append({"method": method, "batch": batch, "found": val})
        if not records:
            return alt.Chart(pd.DataFrame({"found": [], "method": []})).mark_bar()
        chart_df = pd.DataFrame(records)
        return (
            alt.Chart(chart_df)
            .mark_bar()
            .transform_bin("found_bin", field="found", bin=alt.Bin(step=50))
            .encode(
                x=alt.X(
                    "found_bin:O",
                    title="Patients found (binned, width 50)",
                    axis=alt.Axis(labelExpr="datum.label", labelFlush=True, labelOverlap=True, labelAngle=0, tickCount=4),
                ),
                y=alt.Y("count()", title="Count"),
                color="method:N",
                xOffset="method",
            )
            .properties(title=title)
        )

    def make_dps_hist(subdf: pd.DataFrame, title: str):
        records = []
        dps_cols = [c for c in subdf.columns if c.endswith("_dps") and ("batch0" in c)]
        for col in dps_cols:
            method = "legacy" if col.startswith("legacy_") else "nextgen"
            if method not in method_filter.value:
                continue
            batch = col.replace("_dps", "").replace("legacy_batch", "").replace("nextgen_batch", "")
            for val in subdf[col].dropna():
                records.append({"method": method, "batch": batch, "dps": val})
        if not records:
            return alt.Chart(pd.DataFrame({"dps": [], "method": []})).mark_bar()
        chart_df = pd.DataFrame(records)
        chart_df = chart_df[chart_df["dps"] >= 0]
        return (
            alt.Chart(chart_df)
            .mark_bar()
            .transform_bin("dps_bin", field="dps", bin=alt.Bin(step=100))
            .encode(
                x=alt.X(
                    "dps_bin:O",
                    title="Dummy patients per second (batch 0)",
                    axis=alt.Axis(labelExpr="datum.label", labelFlush=True, labelOverlap=True, labelAngle=0, tickCount=4),
                ),
                y=alt.Y("count()", title="Count"),
                color="method:N",
                xOffset="method",
            )
            .properties(title=title)
        )

    # Split data by run_type for charts
    charts = []
    for rtype in ["dataset", "measure"]:
        subdf = df[df["run_type"] == rtype] if "run_type" in df.columns else df
        found_chart = make_found_hist(subdf, f"Found distribution (batch 0) - {rtype}")
        dps_chart = make_dps_hist(subdf, f"DPS distribution (batch 0) - {rtype}")
        charts.append((rtype, found_chart, dps_chart))

    # Nextgen found by project (mean across runs), sorted ascending
    if "nextgen" in method_filter.value:
        nextgen_project = (
            df[df["nextgen_found"].notna()]
            .groupby("project", as_index=False)["nextgen_found"]
            .mean()
            .sort_values("nextgen_found", ascending=True)
        )
    else:
        nextgen_project = pd.DataFrame(columns=["project", "nextgen_found"])
    if nextgen_project.empty:
        nextgen_found_chart = alt.Chart(pd.DataFrame({"project": [], "nextgen_found": []})).mark_bar()
    else:
        sort_projects = nextgen_project["project"].tolist()
        nextgen_found_chart = (
            alt.Chart(nextgen_project)
            .mark_bar()
            .encode(
                y=alt.Y("project:N", sort=sort_projects, title="Project"),
                x=alt.X("nextgen_found:Q", title="Avg nextgen patients found (batch 0)"),
                tooltip=["project", alt.Tooltip("nextgen_found:Q", format=".1f", title="Avg found")],
            )
            .properties(title="Nextgen found by project (batch 0, ascending)")
        )

    # Legacy found by project (batch0 mean), sorted ascending
    if "legacy" in method_filter.value:
        legacy_project = (
            df[df["legacy_batch0_found"].notna()]
            .groupby("project", as_index=False)["legacy_batch0_found"]
            .mean()
            .sort_values("legacy_batch0_found", ascending=True)
        )
    else:
        legacy_project = pd.DataFrame(columns=["project", "legacy_batch0_found"])
    if legacy_project.empty:
        legacy_found_chart = alt.Chart(pd.DataFrame({"project": [], "legacy_batch0_found": []})).mark_bar()
    else:
        sort_projects_legacy = legacy_project["project"].tolist()
        legacy_found_chart = (
            alt.Chart(legacy_project)
            .mark_bar()
            .encode(
                y=alt.Y("project:N", sort=sort_projects_legacy, title="Project"),
                x=alt.X("legacy_batch0_found:Q", title="Avg legacy patients found (batch 0)"),
                tooltip=["project", alt.Tooltip("legacy_batch0_found:Q", format=".1f", title="Avg found")],
            )
            .properties(title="Legacy found by project (batch 0, ascending)")
        )

    # Scatter: nodes vs found
    scatter = alt.Chart(df.dropna(subset=["population_nodes", "nextgen_batch0_found"])).mark_circle(size=60).encode(
        x=alt.X("nextgen_batch0_found:Q", title="Nextgen batch0 found"),
        y=alt.Y("population_nodes:Q", title="Population nodes"),
        color="run_type:N",
        tooltip=["project", "log_name", "population_nodes", "nextgen_batch0_found", "run_type"],
    ).properties(title="Population complexity vs batch0 yield")

    # Drop method-specific columns not selected
    legacy_cols = [c for c in df.columns if c.startswith("legacy_")]
    nextgen_cols = [c for c in df.columns if c.startswith("nextgen_")]
    drop_cols = []
    if "legacy" not in method_filter.value:
        drop_cols.extend(legacy_cols)
    if "nextgen" not in method_filter.value:
        drop_cols.extend(nextgen_cols)
    # Hide analysis_file in table
    drop_cols.append("analysis_file")
    # Drop nextgen batches 2,3,4 columns
    for c in list(df.columns):
        if c.startswith("nextgen_batch"):
            import re
            m = re.match(r"nextgen_batch(\d+)_", c)
            if m and int(m.group(1)) > 1:
                drop_cols.append(c)
        # Drop per-step timings; keep totals and derived
        if any(
            c.endswith(suffix)
            for suffix in ("raw_sec", "populate_sec", "engine_sec", "accumulate_sec")
        ):
            drop_cols.append(c)
    if drop_cols:
        df = df.drop(columns=[c for c in drop_cols if c in df.columns])

    hidden_cols = [
        "id",
        "legacy_exit_code",
        "nextgen_exit_code",
        "nextgen_old_exit_code",
        "nextgen_tomw2_exit_code",
        "nextgen_tomw3_exit_code",
        "legacy_overall_sec",
        "nextgen_overall_sec",
        "nextgen_old_overall_sec",
        "nextgen_tomw2_overall_sec",
        "nextgen_tomw3_overall_sec",
    ]
    drop_hidden = [c for c in hidden_cols if c in df.columns]
    if drop_hidden:
        df = df.drop(columns=drop_hidden)

    # Drop the first integer column (e.g., target) from display
    int_cols = [c for c in df.columns if pd.api.types.is_integer_dtype(df[c])]
    if int_cols:
        df = df.drop(columns=[int_cols[0]])

    # Drop the index so it does not render as an int64 column
    df = df.reset_index(drop=True)

    # Percent formatting for improvements
    percent_cols = [
        c
        for c in df.columns
        if c
        in (
            "nextgen_batch_improvement",
            "found_diff_pct",
            "tomw_improvements_batch0",
            "tomw_improvements_batch1",
            "tomw2_found_improvement",
            "tomw3_improvements_batch0",
            "tomw3_improvements_batch1",
        )
    ]
    format_mapping = {c: "{:.2f}%" for c in percent_cols}

    # Column tooltips/help
    column_tooltips = {c: column_descriptions.get(c, "") for c in df.columns if c in column_descriptions}
    table_kwargs = {
        "pagination": True,
        "page_size": int(page_size.value),
        "selection": None,
        "format_mapping": format_mapping if format_mapping else None,
    }
    try:
        main_table = mo.ui.table(df, column_tooltips=column_tooltips, **table_kwargs)
    except TypeError:
        # Fallback for marimo versions without column_tooltips support
        main_table = mo.ui.table(df, **table_kwargs)
    table_box = main_table

    help_text = (
        f"**{column_help.value}**: {column_descriptions.get(column_help.value, '')}"
        if column_help.value
        else "Select a column to see its description."
    )
    rows = []
    for col in df.columns:
        desc = column_descriptions.get(col)
        if not desc:
            continue
        rows.append(f"<div class='col-row'><strong>{col}</strong>: {desc}</div>")
    legend_html = mo.Html(
        """
<style>
.col-legend {display:flex;flex-direction:column;gap:0.25rem;max-height:40vh;overflow:auto;padding:0.4rem 0.6rem;border:1px solid #e0e0e0;border-radius:0.4rem;background:#f9f9f9;}
.col-row strong {font-weight:600;}
</style>
<div class="col-legend">
""" + "\n".join(rows) + "\n</div>"
    )

    # Filtered table: small populations with low yield
    filtered = df[
        (df.get("population_nodes").notna())
        & (df["population_nodes"] < 70)
        & (df.get("nextgen_batch0_found").notna())
        & (df["nextgen_batch0_found"] < 250)
    ]
    filtered_table = mo.ui.table(
        filtered.reset_index(drop=True),
        pagination=True,
        page_size=int(page_size.value),
        selection=None,
        format_mapping=format_mapping if format_mapping else None,
    )

    display = mo.vstack(
        [
            mo.md("## Dummy log comparison explorer"),
            mo.md(f"**{gm_text}**  \n**{gm2_text}**"),
            mo.md("### Batch 0 DPS distribution"),
            mo.ui.altair_chart(charts[0][2]),
            mo.ui.altair_chart(charts[0][1]),
            mo.md("### Batch 0 DPS distribution (measures)"),
            mo.ui.altair_chart(charts[1][2]),
            mo.ui.altair_chart(charts[1][1]),
            mo.md("### Nextgen found by project"),
            mo.ui.altair_chart(nextgen_found_chart),
            mo.md("### Legacy found by project"),
            mo.ui.altair_chart(legacy_found_chart),
            mo.md("### Population complexity vs batch0 yield"),
            mo.ui.altair_chart(scatter),
            mo.md("### Paired runs (legacy + nextgen)"),
            mo.hstack(
                [method_filter, run_type_filter, sort_col, sort_ascending, page_size],
                gap="0.5rem",
            ),
            mo.md(f"**{gm_text}**  \n**{gm2_text}**  \n**{gm3_text}**  \n**{gm4_text}**"),
            table_box,
            mo.vstack(
                [
                    mo.md("#### Column descriptions"),
                    column_help,
                    mo.md(help_text),
                    legend_html,
                ],
                align="start",
            ),
            mo.md("### Small population & low yield (population_nodes < 70, nextgen_batch0_found < 250)"),
            filtered_table,
        ],
        gap="1rem",
    )

    display


if __name__ == "__main__":
    app.run()
