#!/usr/bin/env python3
"""Simple helper to move the [Unreleased] changelog section into a versioned
section, commit the change, and tag the commit.

Usage:
    python scripts/bump_release.py --version 1.0.2

Options:
    --version / -v   Semantic version to release (required, without leading 'v')
    --notes-file     Path to the RELEASE_NOTES.md (default: RELEASE_NOTES.md)
    --no-git         Skip git commit & tag (just updates the notes)

The script expects a changelog following *Keep‑a‑Changelog* style with a top
`## [Unreleased]` header.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import pathlib as _pl
import re
import subprocess
import sys
from textwrap import dedent

DEFAULT_CHANGELOG = dedent("""
# Release Notes – How Is Lily Doing

## [Unreleased]
### Added
### Changed
### Fixed
### Removed
""")

git_available = True
try:
    subprocess.run(["git", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
except Exception:
    git_available = False


def ensure_changelog(path: _pl.Path) -> None:
    """Create skeleton changelog if it does not exist."""
    if not path.exists():
        path.write_text(DEFAULT_CHANGELOG, encoding="utf-8")
        print(f"Created new changelog skeleton at {path}.")


def bump_version(path: _pl.Path, version: str) -> None:
    text = path.read_text(encoding="utf-8")

    if f"[v{version}]" in text:
        print(f"Version v{version} already present in changelog – aborting.")
        sys.exit(1)

    # Match everything between the Unreleased header and the next header ("## ")
    unreleased_pattern = re.compile(r"## \[Unreleased\](.*?)(?=\n## )", re.S)
    match = unreleased_pattern.search(text)
    if not match:
        print("Could not locate an '[Unreleased]' section in the changelog.")
        sys.exit(1)

    unreleased_body = match.group(1).rstrip()
    today = _dt.datetime.utcnow().strftime("%Y-%m-%d")
    release_header = f"## [v{version}] – {today}"

    # Build replacement
    new_unreleased_header = "## [Unreleased]\n\n"
    replacement = f"{new_unreleased_header}{release_header}{unreleased_body}\n\n## "
    new_text = unreleased_pattern.sub(replacement, text).rstrip("\n## ")
    path.write_text(new_text, encoding="utf-8")
    print(f"Changelog updated for v{version}.")


def git_commit_and_tag(changelog: _pl.Path, version: str):
    if not git_available:
        print("Git not available – skipping commit & tag.")
        return

    tag_name = f"v{version}"
    # Stage file
    subprocess.run(["git", "add", str(changelog)], check=True)
    subprocess.run(["git", "commit", "-m", f"docs: release notes for {tag_name}"], check=True)
    # Create annotated tag
    subprocess.run(["git", "tag", "-a", tag_name, "-m", f"Release {tag_name}"], check=True)
    print(f"Git commit + tag {tag_name} created. Don't forget to push: git push && git push --tags")


def main():
    parser = argparse.ArgumentParser(description="Bump RELEASE_NOTES.md and create a git tag")
    parser.add_argument("--version", "-v", required=True, help="Version number, e.g. 1.0.2")
    parser.add_argument("--notes-file", default="RELEASE_NOTES.md", help="Path to changelog file")
    parser.add_argument("--no-git", action="store_true", help="Skip git commit & tag")
    args = parser.parse_args()

    changelog_path = _pl.Path(args.notes_file).resolve()
    ensure_changelog(changelog_path)
    bump_version(changelog_path, args.version)

    if not args.no_git:
        git_commit_and_tag(changelog_path, args.version)


if __name__ == "__main__":
    main() 