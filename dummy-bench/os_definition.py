#!/usr/bin/env -S uvx python
"""
Run an opensafely action to serialize an EHRQL definition, inferring inputs from project.yaml.

Usage: os_definition <action-name>
Run from a project directory containing project.yaml.
"""

import shlex
import subprocess
import sys
from pathlib import Path

import yaml


def load_project():
    proj_file = Path("project.yaml")
    if not proj_file.exists():
        sys.exit("project.yaml not found; run from a project directory")
    try:
        return yaml.safe_load(proj_file.read_text())
    except Exception as exc:
        sys.exit(f"Failed to read project.yaml: {exc}")


def parse_run(run_value: str):
    """Parse the run command to extract type, analysis path, and args after '--'."""
    if isinstance(run_value, list):
        run_str = " ".join(str(x) for x in run_value)
    else:
        run_str = str(run_value)
    tokens = shlex.split(run_str)

    # Split on sentinel '--'
    extra_args = []
    if "--" in tokens:
        split_idx = tokens.index("--")
        extra_args = tokens[split_idx + 1 :]
        tokens = tokens[:split_idx]

    # Determine type
    run_type = None
    for tok in tokens:
        if "generate-measure" in tok:
            run_type = "measures"
            break
        if "generate-dataset" in tok:
            run_type = "dataset"
            break

    # Find analysis path (first .py token after the type token if possible)
    analysis_path = None
    for tok in tokens:
        if tok.endswith(".py"):
            analysis_path = tok
            break

    return run_type, analysis_path, extra_args


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: os_definition <action-name>")
    action_name = sys.argv[1]

    project = load_project()
    actions = project.get("actions", {})
    if action_name not in actions:
        sys.exit(f"Action '{action_name}' not found in project.yaml")

    run_value = actions[action_name].get("run")
    if not run_value:
        sys.exit(f"Action '{action_name}' has no 'run' entry")

    run_type, analysis_path, extra_args = parse_run(run_value)
    if not analysis_path:
        sys.exit("Could not determine analysis file (.py) from action run command")
    if not run_type:
        sys.exit("Could not determine run type (generate-dataset or generate-measures)")

    cmd = [
        "opensafely",
        "exec",
        "--env",
        "PYTHONPATH=/app:/workspace",
        "ehrql:v1",
        "serialize-definition",
        "-t",
        run_type,
        analysis_path,
    ]
    if extra_args:
        cmd.append("--")
        cmd.extend(extra_args)

    print("Running:", " ".join(shlex.quote(c) for c in cmd))
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
