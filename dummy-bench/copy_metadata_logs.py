#!/usr/bin/env python3
"""Copy */metadata/*.log files into ../default preserving structure."""

from __future__ import annotations

import shutil
from pathlib import Path

import argparse


TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
DEFAULT_SRC_ROOT = REPO_ROOT / "research"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Copy metadata logs to a new root")
    parser.add_argument(
        "--source-root",
        type=Path,
        default=DEFAULT_SRC_ROOT,
        help="Directory to scan for metadata logs (default: research/)",
    )
    parser.add_argument(
        "dest_root",
        type=Path,
        help="Destination directory where logs will be copied",
    )
    parser.add_argument(
        "--actions-file",
        type=Path,
        help="Optional actions file (<dir> <action> per line). If set, only copy logs for these entries and do not error if dest exists.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dest_root = args.dest_root.resolve()
    src_root = args.source_root.resolve()
    allow_existing = args.actions_file is not None
    if dest_root.exists() and not allow_existing:
        raise SystemExit(f"Destination already exists: {dest_root}")
    if not src_root.exists():
        raise SystemExit(f"Source root not found: {src_root}")

    selected_paths = None
    if args.actions_file:
        selected_paths = set()
        lines = args.actions_file.read_text().splitlines()
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) != 2:
                continue
            directory, action = parts
            selected_paths.add((directory, action))

    log_files = []
    for src in src_root.glob("**/metadata/*.log"):
        if selected_paths:
            rel = src.relative_to(src_root)
            project = rel.parts[0]
            action = src.stem
            if (project, action) not in selected_paths:
                continue
        log_files.append(src)

    log_files = sorted(log_files)
    if not log_files:
        print("No metadata logs found.")
        return

    dest_root.mkdir(parents=True, exist_ok=True)

    for src in log_files:
        rel = src.relative_to(src_root)
        dest = dest_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    print(f"Copied {len(log_files)} log files into {dest_root}")


if __name__ == "__main__":
    main()
