#!/usr/bin/env python3
"""Validate an AI-tool project workspace or a Codex plugin source tree."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

try:
    import yaml
except ImportError:  # pragma: no cover - reported as a finding at runtime
    yaml = None


PLUGIN_FIELDS = ("name", "version", "description", "skills")
PLUGIN_INTERFACE_FIELDS = (
    "displayName",
    "shortDescription",
    "longDescription",
    "developerName",
    "category",
    "defaultPrompt",
)
SKILL_INTERFACE_FIELDS = ("display_name", "short_description", "default_prompt")
PROJECT_PATHS = (
    "product.json",
    "design.md",
    "plan.md",
    "stage-status.json",
    "research/research-brief.md",
    "research/source-ledger.csv",
    "metrics/Skill开发指标字典与Stage-Gate模板.xlsx",
    "evals/evals.json",
    "src",
    "reports/release-checklist.md",
    "release",
)
TEXT_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".csv", ".py", ".toml", ".txt"}
SKIP_PARTS = {"__pycache__", ".git", ".venv", "venv", "node_modules"}
PLACEHOLDER_RE = re.compile(r"\bTODO\b|{{[A-Z0-9_]+}}|\[TODO[:\]]", re.IGNORECASE)
SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{12,}"
)
USER_ABSOLUTE_RE = re.compile(
    r"(?i)(?:\b[A-Z]:[\\/]+Users[\\/]+[^\\/\s]+[\\/]|/(?:Users|home)/[^/\s]+/)"
)
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
BACKTICK_PATH_RE = re.compile(
    r"`((?:\.\./)+[^`\s]+\.(?:md|json|yaml|yml|py|xlsx)|references/[^`\s]+\.md)`"
)
STAGE_VALUES = {
    "not_started",
    "in_progress",
    "passed",
    "failed",
    "blocked",
    "not_applicable",
}


@dataclass
class Finding:
    level: str
    code: str
    path: str
    message: str


def add(
    findings: list[Finding], level: str, code: str, path: Path, message: str
) -> None:
    findings.append(Finding(level, code, str(path), message))


def load_json(path: Path, findings: list[Finding]) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        add(findings, "error", "invalid_json", path, str(exc))
        return None
    if not isinstance(value, dict):
        add(findings, "error", "invalid_json_root", path, "JSON root must be an object")
        return None
    return value


def load_yaml(path: Path, findings: list[Finding]) -> dict | None:
    if yaml is None:
        add(findings, "error", "yaml_dependency", path, "PyYAML is required")
        return None
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        add(findings, "error", "invalid_yaml", path, str(exc))
        return None
    if not isinstance(value, dict):
        add(findings, "error", "invalid_yaml_root", path, "YAML root must be a map")
        return None
    return value


def iter_text_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        yield path


def scan_text(root: Path, findings: list[Finding]) -> None:
    for path in iter_text_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            add(findings, "error", "unreadable_text", path, str(exc))
            continue
        relative_parts = path.relative_to(root).parts
        is_template = len(relative_parts) >= 2 and relative_parts[:2] == (
            "assets",
            "templates",
        )
        is_validator = path.name == "validate_product.py"
        if not is_template and not is_validator and PLACEHOLDER_RE.search(text):
            add(findings, "error", "placeholder", path, "unresolved placeholder found")
        if SECRET_RE.search(text):
            add(findings, "error", "possible_secret", path, "possible embedded secret")
        if USER_ABSOLUTE_RE.search(text):
            add(
                findings,
                "error",
                "local_absolute_path",
                path,
                "contains a user-specific Windows path",
            )


def parse_frontmatter(path: Path, findings: list[Finding]) -> dict[str, str] | None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        add(findings, "error", "unreadable_skill", path, str(exc))
        return None
    match = FRONTMATTER_RE.match(text)
    if not match:
        add(findings, "error", "missing_frontmatter", path, "SKILL.md has no frontmatter")
        return None
    if yaml is None:
        add(findings, "error", "yaml_dependency", path, "PyYAML is required")
        return None
    try:
        result = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        add(findings, "error", "invalid_frontmatter", path, str(exc))
        return None
    if not isinstance(result, dict):
        add(
            findings,
            "error",
            "invalid_frontmatter_root",
            path,
            "frontmatter must be a map",
        )
        return None
    return result


def validate_plugin(root: Path, findings: list[Finding]) -> None:
    manifest_path = root / ".codex-plugin" / "plugin.json"
    if not manifest_path.is_file():
        add(findings, "error", "missing_manifest", manifest_path, "plugin.json missing")
        return
    manifest = load_json(manifest_path, findings)
    if manifest:
        for field in PLUGIN_FIELDS:
            if not manifest.get(field):
                add(
                    findings,
                    "error",
                    "missing_manifest_field",
                    manifest_path,
                    f"required field missing: {field}",
                )
        interface = manifest.get("interface", {})
        if not isinstance(interface, dict):
            add(
                findings,
                "error",
                "invalid_plugin_interface",
                manifest_path,
                "interface must be an object",
            )
        else:
            for field in PLUGIN_INTERFACE_FIELDS:
                if not interface.get(field):
                    add(
                        findings,
                        "error",
                        "missing_plugin_interface_field",
                        manifest_path,
                        f"interface field missing: {field}",
                    )
        if manifest.get("name") != root.name:
            add(
                findings,
                "error",
                "name_mismatch",
                manifest_path,
                "manifest name must match plugin directory",
            )
        version = manifest.get("version", "")
        if version and not SEMVER_RE.fullmatch(version):
            add(
                findings,
                "error",
                "invalid_version",
                manifest_path,
                "version must follow semantic versioning",
            )
        skills_value = manifest.get("skills")
        if not isinstance(skills_value, str) or not (root / skills_value).is_dir():
            add(
                findings,
                "error",
                "invalid_skills_path",
                manifest_path,
                "skills must be a directory path that exists",
            )
    skill_files = sorted((root / "skills").glob("*/SKILL.md"))
    if not skill_files:
        add(findings, "error", "missing_skills", root / "skills", "no skills found")
    names: set[str] = set()
    for skill_file in skill_files:
        metadata = parse_frontmatter(skill_file, findings)
        if not metadata:
            continue
        for field in ("name", "description"):
            if not metadata.get(field):
                add(
                    findings,
                    "error",
                    "missing_skill_field",
                    skill_file,
                    f"frontmatter field missing: {field}",
                )
        name = metadata.get("name", "")
        if name != skill_file.parent.name:
            add(
                findings,
                "error",
                "skill_name_mismatch",
                skill_file,
                "skill name must match directory",
            )
        if name in names:
            add(findings, "error", "duplicate_skill", skill_file, f"duplicate: {name}")
        names.add(name)
        skill_text = skill_file.read_text(encoding="utf-8")
        for relative_path in BACKTICK_PATH_RE.findall(skill_text):
            resolved_path = (skill_file.parent / relative_path).resolve()
            if not resolved_path.exists():
                add(
                    findings,
                    "error",
                    "missing_skill_reference",
                    skill_file,
                    f"referenced file does not exist: {relative_path}",
                )
        interface_path = skill_file.parent / "agents" / "openai.yaml"
        if not interface_path.is_file():
            add(
                findings,
                "error",
                "missing_skill_interface",
                interface_path,
                "agents/openai.yaml missing",
            )
        else:
            interface_data = load_yaml(interface_path, findings)
            if interface_data:
                interface = interface_data.get("interface", {})
                if not isinstance(interface, dict):
                    add(
                        findings,
                        "error",
                        "invalid_skill_interface",
                        interface_path,
                        "interface must be a map",
                    )
                else:
                    for field in SKILL_INTERFACE_FIELDS:
                        if not interface.get(field):
                            add(
                                findings,
                                "error",
                                "missing_skill_interface_field",
                                interface_path,
                                f"interface field missing: {field}",
                            )
                    short = interface.get("short_description", "")
                    if short and not 25 <= len(short) <= 64:
                        add(
                            findings,
                            "error",
                            "skill_short_description_length",
                            interface_path,
                            "short_description must be 25-64 characters",
                        )
    eval_path = root / "evals" / "trigger-cases.json"
    if not eval_path.is_file():
        add(
            findings,
            "error",
            "missing_trigger_evals",
            eval_path,
            "plugin must include positive, negative, and boundary trigger cases",
        )
    else:
        catalog = load_json(eval_path, findings)
        if catalog:
            skill_cases = catalog.get("skills", {})
            if not isinstance(skill_cases, dict):
                add(
                    findings,
                    "error",
                    "invalid_trigger_catalog",
                    eval_path,
                    "skills must be an object",
                )
                skill_cases = {}
            for name in names:
                groups = skill_cases.get(name, {})
                if not isinstance(groups, dict):
                    add(
                        findings,
                        "error",
                        "invalid_trigger_groups",
                        eval_path,
                        f"{name} groups must be an object",
                    )
                    groups = {}
                for group, minimum in (("positive", 5), ("negative", 5), ("boundary", 3)):
                    cases = groups.get(group, [])
                    if not isinstance(cases, list) or len(cases) < minimum:
                        add(
                            findings,
                            "error",
                            "insufficient_trigger_evals",
                            eval_path,
                            f"{name}.{group} requires at least {minimum} cases",
                        )
    scan_text(root, findings)


def validate_project(root: Path, findings: list[Finding]) -> None:
    for relative in PROJECT_PATHS:
        path = root / relative
        if not path.exists():
            add(findings, "error", "missing_project_path", path, "required path missing")
    for relative in ("product.json", "stage-status.json", "evals/evals.json"):
        path = root / relative
        if path.is_file():
            load_json(path, findings)
    eval_path = root / "evals" / "evals.json"
    if eval_path.is_file():
        eval_data = load_json(eval_path, findings)
        if eval_data:
            cases = eval_data.get("cases", [])
            if not isinstance(cases, list):
                add(
                    findings,
                    "error",
                    "invalid_project_evals",
                    eval_path,
                    "cases must be an array",
                )
                cases = []
            counts = {
                group: sum(
                    isinstance(case, dict) and case.get("type") == group
                    for case in cases
                )
                for group in ("positive", "negative", "boundary")
            }
            for group, minimum in (("positive", 5), ("negative", 5), ("boundary", 3)):
                if counts[group] < minimum:
                    add(
                        findings,
                        "error",
                        "insufficient_project_evals",
                        eval_path,
                        f"{group} requires at least {minimum} cases",
                    )
    status_path = root / "stage-status.json"
    if status_path.is_file():
        status = load_json(status_path, findings)
        if status:
            stages = status.get("stages", {})
            if not isinstance(stages, dict):
                add(
                    findings,
                    "error",
                    "invalid_stages",
                    status_path,
                    "stages must be an object",
                )
                stages = {}
            expected = {f"S{i}" for i in range(12)}
            if set(stages) != expected:
                add(
                    findings,
                    "error",
                    "stage_set",
                    status_path,
                    "stage-status must contain S0 through S11 exactly",
                )
            for stage, value in stages.items():
                if value not in STAGE_VALUES:
                    add(
                        findings,
                        "error",
                        "invalid_stage_value",
                        status_path,
                        f"{stage} has invalid status: {value}",
                    )
            ordered_values = [stages.get(f"S{i}") for i in range(12)]
            if ordered_values.count("in_progress") > 1:
                add(
                    findings,
                    "error",
                    "multiple_active_stages",
                    status_path,
                    "at most one stage may be in_progress",
                )
            gap_seen = False
            for index, value in enumerate(ordered_values):
                if value not in {"passed", "not_applicable"}:
                    gap_seen = True
                elif gap_seen:
                    add(
                        findings,
                        "error",
                        "stage_order",
                        status_path,
                        f"S{index} cannot pass before all earlier stages",
                    )
            if status.get("release_readiness") not in {
                "not_ready",
                "candidate",
                "ready",
                "blocked",
            }:
                add(
                    findings,
                    "error",
                    "invalid_release_readiness",
                    status_path,
                    "release_readiness has an invalid value",
                )
            if status.get("host_runtime") not in {
                "not_verified",
                "verified",
                "failed",
                "not_applicable",
            }:
                add(
                    findings,
                    "error",
                    "invalid_host_runtime",
                    status_path,
                    "host_runtime has an invalid value",
                )
            readiness = status.get("release_readiness")
            if readiness == "candidate" and any(
                stages.get(f"S{i}") not in {"passed", "not_applicable"}
                for i in range(10)
            ):
                add(
                    findings,
                    "error",
                    "candidate_gate",
                    status_path,
                    "candidate requires S0 through S9 to pass",
                )
            if readiness == "ready":
                if any(
                    stages.get(f"S{i}") not in {"passed", "not_applicable"}
                    for i in range(12)
                ):
                    add(
                        findings,
                        "error",
                        "release_stage_gate",
                        status_path,
                        "ready requires S0 through S11 to pass",
                    )
                if status.get("host_runtime") != "verified":
                    add(
                        findings,
                        "error",
                        "release_runtime_gate",
                        status_path,
                        "ready requires verified host runtime",
                    )
            if status.get("release_readiness") != "ready":
                add(
                    findings,
                    "info",
                    "not_release_ready",
                    status_path,
                    "workspace is not yet marked ready for release",
                )
            if status.get("host_runtime") != "verified":
                add(
                    findings,
                    "info",
                    "runtime_pending",
                    status_path,
                    "target-host runtime is not verified",
                )
    scan_text(root, findings)


def detect_kind(root: Path) -> str:
    if (root / ".codex-plugin" / "plugin.json").is_file():
        return "plugin"
    return "project"


def run_official_validators(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    system_root = Path.home() / ".codex" / "skills" / ".system"
    skill_validator = system_root / "skill-creator" / "scripts" / "quick_validate.py"
    plugin_validator = system_root / "plugin-creator" / "scripts" / "validate_plugin.py"
    for path in (skill_validator, plugin_validator):
        if not path.is_file():
            add(
                findings,
                "error",
                "official_validator_missing",
                path,
                "official validator is not installed at the standard location",
            )
    if findings:
        return findings

    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    for skill_dir in sorted((root / "skills").iterdir()):
        if not (skill_dir / "SKILL.md").is_file():
            continue
        result = subprocess.run(
            [sys.executable, str(skill_validator), str(skill_dir)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=environment,
            check=False,
        )
        if result.returncode != 0:
            add(
                findings,
                "error",
                "official_skill_validation_failed",
                skill_dir,
                (result.stdout + result.stderr).strip(),
            )
    result = subprocess.run(
        [sys.executable, str(plugin_validator), str(root)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
        check=False,
    )
    if result.returncode != 0:
        add(
            findings,
            "error",
            "official_plugin_validation_failed",
            root,
            (result.stdout + result.stderr).strip(),
        )
    return findings


def render_markdown(root: Path, kind: str, findings: list[Finding]) -> str:
    errors = sum(item.level == "error" for item in findings)
    warnings = sum(item.level == "warning" for item in findings)
    infos = sum(item.level == "info" for item in findings)
    lines = [
        "# AI 工具校验报告",
        "",
        f"- 检查对象：`{root}`",
        f"- 类型：`{kind}`",
        f"- 结果：{'PASS' if errors == 0 else 'FAIL'}",
        f"- 错误：{errors}",
        f"- 警告：{warnings}",
        f"- 提示：{infos}",
        "",
        "## 发现",
        "",
    ]
    if not findings:
        lines.append("- 未发现问题。")
    else:
        for item in findings:
            lines.append(
                f"- [{item.level.upper()}] `{item.code}`｜`{item.path}`｜{item.message}"
            )
    return "\n".join(lines) + "\n"


def validate(root: Path, kind: str = "auto") -> tuple[str, list[Finding]]:
    root = root.resolve()
    selected = detect_kind(root) if kind == "auto" else kind
    findings: list[Finding] = []
    if not root.is_dir():
        add(findings, "error", "missing_root", root, "target directory does not exist")
        return selected, findings
    if selected == "plugin":
        validate_plugin(root, findings)
    else:
        validate_project(root, findings)
    return selected, findings


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path")
    parser.add_argument("--kind", choices=("auto", "project", "plugin"), default="auto")
    parser.add_argument("--json-out")
    parser.add_argument("--markdown-out")
    parser.add_argument(
        "--run-official",
        action="store_true",
        help="Run installed OpenAI Skill and Plugin validators",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.path)
    kind, findings = validate(root, args.kind)
    if args.run_official and kind == "plugin" and root.is_dir():
        findings.extend(run_official_validators(root.resolve()))
    payload = {
        "path": str(root.resolve()),
        "kind": kind,
        "result": "PASS"
        if not any(item.level == "error" for item in findings)
        else "FAIL",
        "findings": [asdict(item) for item in findings],
    }
    json_text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    markdown = render_markdown(root.resolve(), kind, findings)
    if args.json_out:
        Path(args.json_out).write_text(json_text, encoding="utf-8")
    if args.markdown_out:
        Path(args.markdown_out).write_text(markdown, encoding="utf-8")
    print(markdown, end="")
    return 1 if payload["result"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
