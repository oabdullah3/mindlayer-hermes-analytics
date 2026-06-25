#!/usr/bin/env python3
"""
Snapshot Backward Compatibility Test

Runs both the old root collector (via subprocess) and the new userend collector
against the same HERMES_HOME, normalizes `generated_at` timestamps, and
deep-compares the resulting JSON trees. Exits 0 on match, 1 on divergence.

Usage:
    python3 userend/test_snapshot_compat.py
"""

import json
import os
import subprocess
import sys
import tempfile


def run_collector(script_path: str, hermes_home: str, output_path: str) -> int:
    """Run a collector script and return the exit code."""
    result = subprocess.run(
        ["python3", script_path, "--hermes-home", hermes_home, "--output", output_path],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        print(f"Collector {script_path} failed with exit code {result.returncode}")
        print("STDERR:", result.stderr[:500])
    return result.returncode


def load_json(path: str) -> dict:
    """Load a JSON file."""
    if not os.path.isfile(path):
        print(f"ERROR: Output file not found: {path}")
        sys.exit(1)
    with open(path, "r") as f:
        return json.load(f)


def normalize_generated_at(snapshot: dict) -> dict:
    """Set generated_at to a constant value so it doesn't cause false diffs."""
    snapshot["generated_at"] = "__NORMALIZED__"
    return snapshot


def deep_compare(a, b, path: str = "") -> list[str]:
    """
    Recursively compare two JSON-compatible structures.
    Returns a list of difference descriptions (empty list = identical).
    """
    diffs = []

    if type(a) != type(b):
        diffs.append(f"{path}: type mismatch ({type(a).__name__} vs {type(b).__name__})")
        return diffs

    if isinstance(a, dict):
        a_keys = set(a.keys())
        b_keys = set(b.keys())
        for key in a_keys - b_keys:
            diffs.append(f"{path}.{key}: missing in new snapshot")
        for key in b_keys - a_keys:
            diffs.append(f"{path}.{key}: extra in new snapshot")
        for key in sorted(a_keys & b_keys):
            current_path = f"{path}.{key}" if path else key
            diffs.extend(deep_compare(a[key], b[key], current_path))

    elif isinstance(a, list):
        if len(a) != len(b):
            diffs.append(f"{path}: list length mismatch ({len(a)} vs {len(b)})")
        else:
            for i in range(len(a)):
                current_path = f"{path}[{i}]"
                diffs.extend(deep_compare(a[i], b[i], current_path))

    elif a != b:
        diffs.append(f"{path}: value mismatch ({repr(a)} vs {repr(b)})")

    return diffs


def main() -> None:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hermes_home = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))

    print(f"Repo root: {repo_root}")
    print(f"HERMES_HOME: {hermes_home}")

    # Create temp output files
    fd_old, old_output = tempfile.mkstemp(suffix=".json", prefix="snapshot_old_")
    fd_new, new_output = tempfile.mkstemp(suffix=".json", prefix="snapshot_new_")
    os.close(fd_old)
    os.close(fd_new)

    try:
        old_script = os.path.join(repo_root, "collector.py")
        print(f"Old collector: {old_script}")

        new_script = os.path.join(repo_root, "userend", "collector.py")
        print(f"New collector: {new_script}")

        # Run old collector
        print("\n--- Running old (root) collector ---")
        rc = run_collector(old_script, hermes_home, old_output)
        if rc != 0:
            print("FAIL: Old collector failed")
            sys.exit(1)

        # Run new collector
        print("\n--- Running new (userend) collector ---")
        rc = run_collector(new_script, hermes_home, new_output)
        if rc != 0:
            print("FAIL: New collector failed")
            sys.exit(1)

        # Load and normalize
        old_snapshot = load_json(old_output)
        new_snapshot = load_json(new_output)

        old_snapshot = normalize_generated_at(old_snapshot)
        new_snapshot = normalize_generated_at(new_snapshot)

        # Deep compare
        diffs = deep_compare(old_snapshot, new_snapshot)

        if diffs:
            print(f"\nFAIL: {len(diffs)} difference(s) found:")
            for diff in diffs[:20]:  # cap at 20 to avoid overwhelming output
                print(f"  {diff}")
            if len(diffs) > 20:
                print(f"  ... and {len(diffs) - 20} more")
            sys.exit(1)
        else:
            print("\nPASS: Snapshots are identical")
            sys.exit(0)

    finally:
        # Clean up temp files
        for path in [old_output, new_output]:
            try:
                os.unlink(path)
            except OSError:
                pass


if __name__ == "__main__":
    main()
