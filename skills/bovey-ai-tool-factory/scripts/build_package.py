#!/usr/bin/env python3
"""Validate and package a Codex plugin as a versioned .plugin archive."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path

from validate_product import run_official_validators, validate


EXCLUDED_PARTS = {"__pycache__", ".git", ".venv", "venv", "node_modules", "release"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}
EVIDENCE_TYPES = {
    "static_validation",
    "behavior_evaluation",
    "independent_judge",
    "security_review",
}
EVIDENCE_HEADER_FIELDS = {
    "RELEASE_GATE",
    "EVIDENCE_TYPE",
    "PRODUCT_VERSION",
    "EVALUATED_AT",
}


def validate_archive_path(root: Path, path: Path) -> None:
    resolved_root = root.resolve(strict=True)
    if path.is_symlink():
        raise ValueError(f"symbolic links are not allowed in packages: {path}")
    resolved = path.resolve(strict=True)
    if resolved_root not in resolved.parents:
        raise ValueError(f"package file resolves outside plugin root: {path}")


def archive_files(root: Path, excluded_root: Path | None = None):
    resolved_excluded = excluded_root.resolve() if excluded_root else None
    for path in sorted(root.rglob("*")):
        if resolved_excluded:
            candidate = path.resolve()
            if candidate == resolved_excluded or resolved_excluded in candidate.parents:
                continue
        if not path.is_file():
            continue
        validate_archive_path(root, path)
        relative = path.relative_to(root)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if path.suffix.lower() in EXCLUDED_SUFFIXES:
            continue
        yield path, relative


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def source_sha256(root: Path, excluded_root: Path | None = None) -> str:
    digest = hashlib.sha256()
    files = sorted(
        archive_files(root, excluded_root), key=lambda item: item[1].as_posix()
    )
    for path, relative in files:
        if relative.as_posix() == "release-status.json":
            continue
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest().upper()


def archive_source_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with zipfile.ZipFile(path, "r") as archive:
        for name in sorted(archive.namelist()):
            if name == "release-status.json" or name.endswith("/"):
                continue
            digest.update(name.encode("utf-8"))
            digest.update(b"\0")
            with archive.open(name, "r") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            digest.update(b"\0")
    return digest.hexdigest().upper()


def parse_evidence_report(
    path: Path, expected_type: str, expected_version: str
) -> dict[str, str]:
    if expected_type not in EVIDENCE_TYPES:
        raise ValueError(f"unknown evidence type: {expected_type}")
    lines = path.read_text(encoding="utf-8").splitlines()
    header: dict[str, str] = {}
    for line in lines:
        if not line.strip():
            break
        if ":" not in line:
            raise ValueError(f"invalid evidence header line: {path}")
        key, value = (part.strip() for part in line.split(":", 1))
        if key in header:
            raise ValueError(f"duplicate evidence header field: {key}")
        header[key] = value
    if set(header) != EVIDENCE_HEADER_FIELDS:
        raise ValueError(f"evidence header is incomplete or has unknown fields: {path}")
    if header["RELEASE_GATE"] != "PASS":
        raise ValueError(f"evidence report has no PASS gate: {expected_type}")
    if header["EVIDENCE_TYPE"] != expected_type:
        raise ValueError(f"evidence report type mismatch: {expected_type}")
    if header["PRODUCT_VERSION"] != expected_version:
        raise ValueError(f"evidence report version mismatch: {expected_type}")
    try:
        evaluated_at = datetime.fromisoformat(header["EVALUATED_AT"])
    except ValueError:
        raise ValueError(
            f"evidence report requires an ISO EVALUATED_AT timestamp: {expected_type}"
        )
    if evaluated_at.utcoffset() is None:
        raise ValueError(
            f"evidence report EVALUATED_AT requires a timezone: {expected_type}"
        )
    return header


def validate_release_evidence(
    root: Path, channel: str, expected_version: str, expected_source_sha256: str
) -> dict:
    evidence_path = root / "release-status.json"
    if not evidence_path.is_file():
        raise ValueError(f"release evidence missing: {evidence_path}")
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if not isinstance(evidence, dict):
        raise ValueError("release evidence root must be an object")
    required = {
        "static_validation": {"passed"},
        "behavior_evaluation": {"dry_run_passed", "live_passed"},
        "independent_judge": {"passed"},
        "security_review": {"static_passed", "professional_passed"},
        "approved_for_packaging": {True},
    }
    for field, allowed in required.items():
        if evidence.get(field) not in allowed:
            raise ValueError(f"release gate not satisfied: {field}")
    if evidence.get("product_version") != expected_version:
        raise ValueError("release evidence version does not match manifest")
    if evidence.get("source_sha256") != expected_source_sha256:
        raise ValueError("release evidence does not match current source")
    expected_channel = (
        "internal_candidate" if channel == "internal-candidate" else "public_release"
    )
    if evidence.get("release_channel") != expected_channel:
        raise ValueError("release evidence channel does not match requested channel")
    generated_at = evidence.get("generated_at")
    try:
        datetime.fromisoformat(generated_at)
    except (TypeError, ValueError):
        raise ValueError("release evidence requires an ISO generated_at timestamp")
    evidence_paths = evidence.get("evidence_paths")
    required_evidence = {
        "static_validation",
        "behavior_evaluation",
        "independent_judge",
        "security_review",
    }
    if not isinstance(evidence_paths, dict) or set(evidence_paths) != required_evidence:
        raise ValueError("release evidence paths are incomplete")
    if len(set(evidence_paths.values())) != len(required_evidence):
        raise ValueError("release evidence paths must be distinct")
    resolved_root = root.resolve(strict=True)
    for label, relative_value in evidence_paths.items():
        if not isinstance(relative_value, str) or not relative_value.strip():
            raise ValueError(f"evidence path must be a non-empty string: {label}")
        relative = Path(relative_value)
        if relative.is_absolute():
            raise ValueError(f"evidence path must be relative: {label}")
        evidence_file = root / relative
        if evidence_file.is_symlink() or not evidence_file.is_file():
            raise ValueError(f"evidence file missing or unsafe: {label}")
        if resolved_root not in evidence_file.resolve(strict=True).parents:
            raise ValueError(f"evidence file is outside plugin root: {label}")
        parse_evidence_report(evidence_file, label, expected_version)
    if channel == "public-release":
        if evidence.get("behavior_evaluation") != "live_passed":
            raise ValueError("public release requires live behavior evaluation")
        if evidence.get("host_runtime") != "verified":
            raise ValueError("public release requires verified host runtime")
        if evidence.get("security_review") != "professional_passed":
            raise ValueError("public release requires professional security review")
    return evidence


def build(root: Path, output: Path, channel: str) -> tuple[Path, Path]:
    root = root.resolve()
    kind, findings = validate(root, "plugin")
    findings.extend(run_official_validators(root))
    errors = [item for item in findings if item.level == "error"]
    if kind != "plugin" or errors:
        messages = "; ".join(f"{item.code}: {item.path}" for item in errors)
        raise ValueError(f"plugin validation failed: {messages}")
    manifest = json.loads(
        (root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    name = manifest["name"]
    version = manifest["version"]
    output = output.resolve()
    if output == root:
        raise ValueError("output directory cannot be the plugin root")
    if root in output.parents and output != root / "release":
        raise ValueError(
            "an output inside the plugin root must use the reserved release directory"
        )
    excluded_root = output if root in output.parents else None
    digest_before_status = source_sha256(root, excluded_root)
    evidence = validate_release_evidence(
        root, channel, version, digest_before_status
    )
    output.mkdir(parents=True, exist_ok=True)
    suffix = "-candidate" if channel == "internal-candidate" else ""
    package_path = output / f"{name}-v{version}{suffix}.plugin"
    hash_path = output / f"{name}-v{version}{suffix}.sha256"
    if package_path.exists() or hash_path.exists():
        raise FileExistsError(
            f"release already exists; increment the version or choose another output: {package_path}"
        )

    files = list(archive_files(root, excluded_root))
    temporary_handle = tempfile.NamedTemporaryFile(
        prefix=".plugin-package-", suffix=".tmp", dir=output, delete=False
    )
    temporary_path = Path(temporary_handle.name)
    temporary_handle.close()
    try:
        with zipfile.ZipFile(
            temporary_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for path, relative in files:
                archive.write(path, relative.as_posix())
        with zipfile.ZipFile(temporary_path, "r") as archive:
            bad_file = archive.testzip()
            if bad_file:
                raise ValueError(f"archive integrity check failed: {bad_file}")
        if archive_source_sha256(temporary_path) != evidence["source_sha256"]:
            raise ValueError("source changed while packaging; regenerate release status")
        digest = sha256(temporary_path)
        hash_temporary = hash_path.with_suffix(".sha256.tmp")
        hash_temporary.write_text(
            f"{digest}  {package_path.name}\n", encoding="ascii"
        )
        os.replace(temporary_path, package_path)
        try:
            os.replace(hash_temporary, hash_path)
        except Exception:
            package_path.unlink(missing_ok=True)
            hash_temporary.unlink(missing_ok=True)
            raise
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    return package_path, hash_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plugin_root")
    parser.add_argument("--output", default="release")
    parser.add_argument(
        "--channel",
        choices=("internal-candidate", "public-release"),
        default="internal-candidate",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        package, hash_file = build(
            Path(args.plugin_root), Path(args.output), args.channel
        )
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Package: {package}")
    print(f"SHA256: {hash_file.read_text(encoding='ascii').strip()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
