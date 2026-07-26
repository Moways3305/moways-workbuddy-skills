#!/usr/bin/env python3
"""Bind release evidence to the current plugin version and source digest."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from build_package import (
    parse_evidence_report,
    source_sha256,
    validate_release_evidence,
)


def evidence_relative(root: Path, value: str) -> str:
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    resolved_root = root.resolve(strict=True)
    resolved = path.resolve(strict=True)
    if resolved_root not in resolved.parents or not resolved.is_file():
        raise ValueError(f"evidence file must be inside plugin root: {value}")
    if path.is_symlink():
        raise ValueError(f"evidence file cannot be a symbolic link: {value}")
    return resolved.relative_to(resolved_root).as_posix()


def create_status(args: argparse.Namespace) -> Path:
    if not args.approve:
        raise ValueError("explicit --approve is required after reviewing all reports")
    root = Path(args.plugin_root).resolve(strict=True)
    manifest = json.loads(
        (root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    channel = args.channel
    behavior = "live_passed" if args.behavior == "live" else "dry_run_passed"
    security = (
        "professional_passed"
        if args.security == "professional"
        else "static_passed"
    )
    if channel == "public-release":
        if behavior != "live_passed" or args.host_runtime != "verified":
            raise ValueError("public release requires live behavior and verified host")
        if security != "professional_passed":
            raise ValueError("public release requires professional security review")

    evidence_paths = {
        "static_validation": evidence_relative(root, args.static_report),
        "behavior_evaluation": evidence_relative(root, args.behavior_report),
        "independent_judge": evidence_relative(root, args.judge_report),
        "security_review": evidence_relative(root, args.security_report),
    }
    if len(set(evidence_paths.values())) != len(evidence_paths):
        raise ValueError("the four evidence reports must be distinct files")
    for label, relative in evidence_paths.items():
        parse_evidence_report(root / relative, label, manifest["version"])
    digest = source_sha256(root)
    status = {
        "product_version": manifest["version"],
        "source_sha256": digest,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "static_validation": "passed",
        "behavior_evaluation": behavior,
        "independent_judge": "passed",
        "security_review": security,
        "host_runtime": args.host_runtime,
        "approved_for_packaging": True,
        "release_channel": (
            "internal_candidate"
            if channel == "internal-candidate"
            else "public_release"
        ),
        "evidence_paths": evidence_paths,
    }
    target = root / "release-status.json"
    if target.exists() and not args.replace:
        raise FileExistsError(f"release status already exists: {target}")
    previous = target.read_bytes() if target.exists() else None
    temporary = root / ".release-status.json.tmp"
    temporary.write_text(
        json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, target)
    try:
        validate_release_evidence(
            root, channel, manifest["version"], source_sha256(root)
        )
    except Exception:
        if previous is None:
            target.unlink(missing_ok=True)
        else:
            target.write_bytes(previous)
        raise
    return target


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plugin_root")
    parser.add_argument("--static-report", required=True)
    parser.add_argument("--behavior-report", required=True)
    parser.add_argument("--judge-report", required=True)
    parser.add_argument("--security-report", required=True)
    parser.add_argument(
        "--behavior", choices=("dry-run", "live"), default="dry-run"
    )
    parser.add_argument(
        "--security", choices=("static", "professional"), default="static"
    )
    parser.add_argument(
        "--host-runtime",
        choices=("not_verified", "verified"),
        default="not_verified",
    )
    parser.add_argument(
        "--channel",
        choices=("internal-candidate", "public-release"),
        default="internal-candidate",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace an existing status after regenerating all evidence",
    )
    parser.add_argument(
        "--approve",
        action="store_true",
        help="Confirm that a human or authorized reviewer checked all four reports",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        target = create_status(parse_args(argv))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Release status: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
