#!/usr/bin/env python3
"""Run opensafely actions listed in `ehrql-actions` with parallelism."""

from __future__ import annotations

import argparse
import concurrent.futures
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from collections import defaultdict, deque
from threading import Lock


TOOLS_DIR = Path(__file__).resolve().parent
DEFAULT_ROOT = TOOLS_DIR.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "actions_file",
        nargs="?",
        type=Path,
        default=None,
        help="File containing '<dir> <action>' per line (default: <root>/ehrql-actions)",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="Root directory containing project folders (default: repository root)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=2,
        help="Maximum number of opensafely commands to run concurrently",
    )
    parser.add_argument(
        "--opensafely-bin",
        default="opensafely",
        help="Path to the opensafely executable (default: %(default)s)",
    )
    parser.add_argument(
        "--definition",
        action="store_true",
        help="Use os_definition.py to serialise definitions instead of running opensafely",
    )
    return parser.parse_args()


@dataclass
class Task:
    directory: str
    action: str


def load_tasks(actions_path: Path) -> dict[str, deque[Task]]:
    task_groups: dict[str, deque[Task]] = defaultdict(deque)
    try:
        lines = actions_path.read_text().splitlines()
    except FileNotFoundError:
        sys.stderr.write(f"Actions file not found: {actions_path}\n")
        raise SystemExit(1)

    for lineno, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            sys.stderr.write(
                f"Skipping malformed line {lineno} in {actions_path}: {raw_line!r}\n"
            )
            continue
        task = Task(directory=parts[0], action=parts[1])
        group = parts[0].split("/")[0]
        task_groups[group].append(task)
    return task_groups


def run_task(
    root: Path,
    bin_name: str,
    task: Task,
    use_definition: bool,
    definition_script: Path,
) -> tuple[bool, str]:
    cwd = root / task.directory
    if not cwd.is_dir():
        return False, f"directory missing ({cwd})"

    try:
        if use_definition:
            metadata_dir = cwd / "metadata"
            metadata_dir.mkdir(parents=True, exist_ok=True)
            output_path = metadata_dir / f"{task.action}.json"
            cmd = ["uv", "run", str(definition_script), task.action]
            print(cwd, " ".join(cmd), f"> {output_path}")
            with output_path.open("w") as out:
                result = subprocess.run(
                    cmd,
                    cwd=cwd,
                    stdout=out,
                    stderr=subprocess.PIPE,
                    text=True,
                )
        else:
            cmd = [bin_name, "run", task.action, "-m", "8G"]
            print(cwd, " ".join(cmd))
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
            )
    except FileNotFoundError:
        return False, f"{bin_name} not found"
    except Exception as exc:  # pragma: no cover - defensive guard
        return False, f"{type(exc).__name__}: {exc}"

    if result.returncode == 0:
        return True, ""

    message = result.stderr.strip() or f"exit code {result.returncode}"
    return False, message


def main() -> None:
    args = parse_args()
    root = args.root.resolve()
    actions_path = args.actions_file or (root / "ehrql-actions")
    if actions_path.is_absolute():
        actions_path = actions_path.resolve()
    else:
        actions_path = (root / actions_path).resolve()
    definition_script = (TOOLS_DIR / "os_definition.py").resolve()
    task_groups = load_tasks(actions_path)

    if not task_groups:
        sys.stderr.write("No actions to run.\n")
        return
    project_queue = deque(
        (project, deque(tasks)) for project, tasks in task_groups.items()
    )
    queue_lock = Lock()

    def worker_loop() -> None:
        while True:
            with queue_lock:
                if not project_queue:
                    return
                project, task_deque = project_queue.popleft()
            while task_deque:
                task = task_deque.popleft()
                success, detail = run_task(
                    root, args.opensafely_bin, task, args.definition, definition_script
                )
                status = "SUCCESS" if success else "FAILED"
                suffix = f" ({detail})" if detail else ""
                print(f"{task.directory} {task.action} {status}{suffix}", flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(worker_loop) for _ in range(args.workers)]
        for future in futures:
            future.result()


if __name__ == "__main__":
    main()
