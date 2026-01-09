#!/usr/bin/env python3
"""Scan project.yaml files for actions that run using ehrql:v1."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover - dependency missing guard
    sys.stderr.write(
        "PyYAML is required to run this script. Install it with `pip install pyyaml`.\n"
    )
    raise SystemExit(1) from exc

TOOLS_DIR = Path(__file__).resolve().parent
DEFAULT_ROOT = TOOLS_DIR.parent / "research"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="Root directory to scan for project.yaml files (default: repository root)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file location (default: <root>/ehrql-actions)",
    )
    return parser.parse_args()


def find_project_files(root: Path) -> list[Path]:
    """Return all project.yaml files directly under the root directory."""

    return sorted(root.glob("*/project.yaml"))


def actions_using_ehrql(project_file: Path) -> list[str]:
    """Return action names whose run command starts with `ehrql:v1`."""

    try:
        data = yaml.safe_load(project_file.read_text()) or {}
    except yaml.YAMLError:
        return []

    actions = data.get("actions", {})
    if not isinstance(actions, dict):
        return []

    matching: list[str] = []
    for action_name, action_config in actions.items():
        if not isinstance(action_config, dict):
            continue
        run_value = action_config.get("run")
        if isinstance(run_value, str) and run_value.lstrip().startswith("ehrql:v1"):
            matching.append(action_name)
    return matching


def main() -> None:
    args = parse_args()
    root = args.root.resolve()
    output_lines: list[str] = []
    for project_file in find_project_files(root):
        action_names = actions_using_ehrql(project_file)
        for action_name in action_names:
            relative_dir = project_file.parent.relative_to(root)
            line = f"{relative_dir} {action_name}"
            print(line)
            output_lines.append(line)

    output_path = (args.output or (root / "ehrql-actions")).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(output_lines) + ("\n" if output_lines else ""))


if __name__ == "__main__":
    main()
