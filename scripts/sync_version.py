#!/usr/bin/env python3
"""Synchronize version metadata across bibliography-skills repos.

Single source of truth:
  package.json in the bibliography-skills repo

This script updates:
  - manifest.json
  - package.json
  - packages/bibliography-skills/manifest.json
  - marketplace.json
  - .claude/marketplace.json
  - ../Bibliography-skills-marketplace/.claude-plugin/marketplace.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def require_version(version: str) -> str:
    version = version.strip()
    if not VERSION_RE.match(version):
        raise ValueError(f"Unsupported version format: {version!r}. Expected x.y.z")
    return version


def sync_repo_versions(repo_root: Path, version: str) -> list[Path]:
    changed: list[Path] = []

    targets = [
        repo_root / "package.json",
        repo_root / "manifest.json",
        repo_root / "packages" / "bibliography-skills" / "manifest.json",
        repo_root / "marketplace.json",
        repo_root / ".claude" / "marketplace.json",
    ]

    for path in targets:
        if not path.exists():
            continue
        data = load_json(path)
        old = data.get("version")
        if old != version:
            data["version"] = version
            write_json(path, data)
            changed.append(path)

    marketplace_repo = repo_root.parent / "Bibliography-skills-marketplace" / ".claude-plugin" / "marketplace.json"
    if marketplace_repo.exists():
        data = load_json(marketplace_repo)
        old_meta = data.get("metadata", {}).get("version")
        old_plugin = None
        plugins = data.get("plugins", [])
        if plugins:
            old_plugin = plugins[0].get("version")

        data.setdefault("metadata", {})["version"] = version
        for plugin in plugins:
            if plugin.get("name") == "bibliography-skills":
                plugin["version"] = version

        if old_meta != version or old_plugin != version:
            write_json(marketplace_repo, data)
            changed.append(marketplace_repo)

    return changed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync bibliography-skills version metadata from package.json or an explicit version."
    )
    parser.add_argument(
        "version",
        nargs="?",
        help="Target semantic version. Defaults to package.json version.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    package_json = repo_root / "package.json"
    if not package_json.exists():
        print(f"Error: package.json not found at {package_json}", file=sys.stderr)
        return 1

    package_data = load_json(package_json)
    source_version = args.version or package_data.get("version", "")

    try:
        version = require_version(source_version)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    changed = sync_repo_versions(repo_root, version)

    print(f"Synced version: {version}")
    if changed:
        for path in changed:
            print(path)
    else:
        print("No files changed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
