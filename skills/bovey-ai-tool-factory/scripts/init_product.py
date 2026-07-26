#!/usr/bin/env python3
"""Create a standard AI-tool product workspace from bundled templates."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path


PRODUCT_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TEXT_TEMPLATES = {
    "design.md": "design.md",
    "plan.md": "plan.md",
    "research/research-brief.md": "research-brief.md",
    "research/source-ledger.csv": "source-ledger.csv",
    "evals/evals.json": "evals.json",
    "reports/release-checklist.md": "release-checklist.md",
    "stage-status.json": "stage-status.json",
}


def plugin_root() -> Path:
    return Path(__file__).resolve().parents[1]


def render(text: str, values: dict[str, str], json_mode: bool = False) -> str:
    for key, value in values.items():
        replacement = value
        if json_mode:
            replacement = json.dumps(value, ensure_ascii=False)[1:-1]
        text = text.replace("{{" + key + "}}", replacement)
    return text


def validate_product_id(value: str) -> str:
    if not PRODUCT_ID_RE.fullmatch(value):
        raise argparse.ArgumentTypeError(
            "product_id must use lowercase letters, digits, and single hyphens"
        )
    return value


def build_plan(
    product_id: str,
    target: Path,
    artifact_type: str,
    owner: str,
    display_name: str,
) -> list[tuple[Path, Path | None]]:
    templates = plugin_root() / "assets" / "templates"
    values = {
        "PRODUCT_ID": product_id,
        "ARTIFACT_TYPE": artifact_type,
        "OWNER": owner,
        "DISPLAY_NAME": display_name,
    }
    files: list[tuple[Path, Path | None]] = []
    for relative_target, template_name in TEXT_TEMPLATES.items():
        source = templates / template_name
        destination = target / relative_target
        files.append((destination, source))
    files.append(
        (
            target / "metrics" / "Skill开发指标字典与Stage-Gate模板.xlsx",
            plugin_root()
            / "assets"
            / "Skill开发指标字典与Stage-Gate模板.xlsx",
        )
    )
    for directory in ("src", "release"):
        files.append((target / directory / ".gitkeep", None))
    return files


def create_workspace(args: argparse.Namespace) -> Path:
    output = Path(args.output)
    output_root = output.resolve()
    target = output_root / args.product_id
    if target.exists():
        raise FileExistsError(f"target already exists: {target}")

    display_name = args.display_name or args.product_id
    values = {
        "PRODUCT_ID": args.product_id,
        "ARTIFACT_TYPE": args.artifact_type,
        "OWNER": args.owner,
        "DISPLAY_NAME": display_name,
    }
    plan = build_plan(
        args.product_id, target, args.artifact_type, args.owner, display_name
    )
    if args.dry_run:
        for destination, source in plan:
            label = str(source) if source else "empty marker"
            print(f"PLAN {destination} <- {label}")
        return target

    output_root.mkdir(parents=True, exist_ok=True)
    templates = plugin_root() / "assets" / "templates"
    if not templates.is_dir():
        raise FileNotFoundError(f"template directory missing: {templates}")
    staging = Path(
        tempfile.mkdtemp(prefix=f".{args.product_id}-", dir=output_root)
    )
    try:
        for destination, source in plan:
            staged_destination = staging / destination.relative_to(target)
            staged_destination.parent.mkdir(parents=True, exist_ok=True)
            if source is None:
                staged_destination.write_text("", encoding="utf-8")
            elif source.suffix.lower() == ".xlsx":
                if not source.is_file():
                    raise FileNotFoundError(f"Excel template missing: {source}")
                shutil.copy2(source, staged_destination)
            else:
                content = source.read_text(encoding="utf-8")
                staged_destination.write_text(
                    render(
                        content,
                        values,
                        json_mode=staged_destination.suffix.lower() == ".json",
                    ),
                    encoding="utf-8",
                )

        metadata = {
            "product_id": args.product_id,
            "display_name": display_name,
            "artifact_type": args.artifact_type,
            "owner": args.owner,
            "factory_version": "0.1.0",
        }
        (staging / "product.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        for json_path in (
            staging / "product.json",
            staging / "stage-status.json",
            staging / "evals" / "evals.json",
        ):
            json.loads(json_path.read_text(encoding="utf-8"))
        staging.rename(target)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return target


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create an S0-S11 AI-tool development workspace."
    )
    parser.add_argument("product_id", type=validate_product_id)
    parser.add_argument("--output", default="work", help="Parent output directory")
    parser.add_argument(
        "--artifact-type",
        choices=("auto", "prompt", "instructions", "skill", "plugin", "mcp"),
        default="auto",
    )
    parser.add_argument("--owner", default="未指定")
    parser.add_argument("--display-name")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print planned files without writing"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        target = create_workspace(args)
    except (FileExistsError, FileNotFoundError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.dry_run:
        print(f"Dry run only; no files created: {target}")
    else:
        print(f"Created product workspace: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
