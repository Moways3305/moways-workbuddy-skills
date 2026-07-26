#!/usr/bin/env python3
"""Validate skill directories in this repo.

Rules:
- Every directory under skills/ must contain SKILL.md with frontmatter
  `name` matching the directory name, unless whitelisted as a shared bundle.
- Shared bundles (no SKILL.md by design) are listed in SHARED_BUNDLES.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SHARED_BUNDLES = {"bovey-ai-tool-factory"}
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
NAME_RE = re.compile(r"^name:\s*(\S+)\s*$", re.MULTILINE)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    skills_dir = repo_root / "skills"
    errors: list[str] = []
    for child in sorted(skills_dir.iterdir()):
        if not child.is_dir():
            continue
        skill_md = child / "SKILL.md"
        if child.name in SHARED_BUNDLES:
            if skill_md.exists():
                errors.append(f"{child.name}: shared bundle must not contain SKILL.md")
            continue
        if not skill_md.is_file():
            errors.append(f"{child.name}: SKILL.md missing")
            continue
        text = skill_md.read_text(encoding="utf-8")
        match = FRONTMATTER_RE.match(text)
        if not match:
            errors.append(f"{child.name}: frontmatter missing")
            continue
        name_match = NAME_RE.search(match.group(1))
        if not name_match or name_match.group(1) != child.name:
            errors.append(f"{child.name}: frontmatter name mismatch")
    if errors:
        print("FAIL")
        for e in errors:
            print(" -", e)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
