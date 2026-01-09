#!/usr/bin/env python3
"""
Clone additional branches listed in research/non-main.csv into research/{repo}-{branch}.

The CSV headers are expected to include: Branch, Repo
"""

import csv
import subprocess
import sys
from pathlib import Path


def sanitize_branch(branch: str) -> str:
    return branch.replace("/", "-")


def clone_entry(branch: str, repo_url: str, dest_dir: Path) -> None:
    if dest_dir.exists():
        print(f"skip (exists): {dest_dir}")
        return
    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["git", "clone", "-b", branch, "--single-branch", repo_url, str(dest_dir)]
    print("cloning:", " ".join(cmd))
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        print(f"failed to clone {repo_url} ({branch}): {exc}")


def main() -> None:
    csv_path = Path("research/non-main.csv")
    if not csv_path.exists():
        sys.exit(f"Missing {csv_path}")

    with csv_path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            branch = row.get("Branch")
            repo = row.get("Repo")
            if not branch or not repo:
                continue
            repo_name = Path(repo).stem
            dest_name = f"{repo_name}-{sanitize_branch(branch)}"
            dest_dir = Path("research") / dest_name
            clone_entry(branch, repo, dest_dir)


if __name__ == "__main__":
    main()
