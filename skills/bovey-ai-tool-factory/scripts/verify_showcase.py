#!/usr/bin/env python3
"""Verify the packaged dry-run showcase and its evidence boundaries."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SHOWCASE_ROOT = PLUGIN_ROOT / "examples" / "meeting-action-followup"
MANIFEST_PATH = SHOWCASE_ROOT / "showcase.json"
EXPECTED_ROLES = {
    "项目经理",
    "交付负责人",
    "研究负责人",
    "行政协调人",
    "讨论",
}
EXPECTED_STAGE_EVIDENCE = {
    "S0": ("outputs/产品设计摘要.md", "## 本轮边界"),
    "S1": ("outputs/产品设计摘要.md", "## 产品合同"),
    "S2": ("outputs/研究与指标摘要.md", "## S2 方法证据"),
    "S3": ("outputs/研究与指标摘要.md", "## S3 同类方案"),
    "S4": ("outputs/eval-catalog.json", "\"counts\""),
    "S5": ("outputs/without-skill基线.md", "## 断言快照"),
    "S6": ("outputs/产品设计摘要.md", "## 形态决策"),
}
FORBIDDEN_PATTERNS = {
    "windows_user_path": re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+", re.IGNORECASE),
    "mac_user_path": re.compile(r"/Users/"),
    "linux_home_path": re.compile(r"/home/"),
    "api_key_assignment": re.compile(
        r"(api[_-]?key|token|password)\s*[:=]\s*[\"'][^\"']+[\"']",
        re.IGNORECASE,
    ),
    "bearer_token": re.compile(r"Bearer\s+[A-Za-z0-9._-]{12,}", re.IGNORECASE),
    "email_address": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    "cn_mobile_number": re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    "cn_identity_number": re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"),
    "cn_legacy_identity_number": re.compile(r"(?<!\d)\d{15}(?!\d)"),
    "cn_landline_number": re.compile(r"(?<!\d)0\d{2,3}-?\d{7,8}(?!\d)"),
    "internal_domain": re.compile(r"\b[A-Za-z0-9.-]+\.(?:internal|local)\b", re.IGNORECASE),
    "unc_path": re.compile(r"\\\\[^\\\s]+\\[^\\\s]+"),
    "private_ipv4": re.compile(
        r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
        r"192\.168\.\d{1,3}\.\d{1,3}|"
        r"172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b"
    ),
}


def validate_showcase(root: Path = SHOWCASE_ROOT) -> dict:
    manifest_path = root / "showcase.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assertions: dict[str, bool] = {}

    assertions["synthetic_only"] = manifest.get("data_classification") == "synthetic-only"
    assertions["evidence_is_dry_run"] = manifest.get("evidence_level") == "dry_run"
    assertions["host_not_overclaimed"] = manifest.get("host_runtime") == "not_verified"
    assertions["release_not_overclaimed"] = manifest.get("release_ready") is False
    assertions["selected_minimum_artifact"] = manifest.get("selected_artifact") == "skill"
    assertions["stages_s0_to_s6_only"] = manifest.get("stages_completed") == [
        f"S{index}" for index in range(7)
    ]
    assertions["next_gate_is_s7"] = manifest.get("current_gate") == "S7"
    assertions["baseline_is_single_trial"] = manifest.get("baseline_assertions") == {
        "passed": 5,
        "total": 10,
        "trials": 1,
    }
    baseline_text = (root / "outputs" / "without-skill基线.md").read_text(
        encoding="utf-8"
    )
    baseline_passed = len(re.findall(r"\|\s*通过\s*\|", baseline_text))
    baseline_failed = len(re.findall(r"\|\s*未通过\s*\|", baseline_text))
    assertions["baseline_table_recounts_to_5_of_10"] = (
        baseline_passed == 5
        and baseline_failed == 5
        and manifest.get("baseline_assertions", {}).get("passed") == baseline_passed
        and manifest.get("baseline_assertions", {}).get("total")
        == baseline_passed + baseline_failed
    )

    included_files = manifest.get("included_files")
    assertions["included_file_list_present"] = (
        isinstance(included_files, list) and len(included_files) >= 8
    )
    declared_files = set(included_files) if isinstance(included_files, list) else set()
    missing: list[str] = []
    empty: list[str] = []
    for relative in included_files if isinstance(included_files, list) else []:
        path = root / relative
        if not path.is_file():
            missing.append(relative)
        elif path.stat().st_size == 0:
            empty.append(relative)
    assertions["all_declared_files_exist"] = not missing
    assertions["all_declared_files_nonempty"] = not empty

    stage_evidence = manifest.get("stage_evidence")
    stage_evidence_failures: list[str] = []
    expected_stages = {f"S{index}" for index in range(7)}
    if not isinstance(stage_evidence, dict) or set(stage_evidence) != expected_stages:
        stage_evidence_failures.append("stage_keys")
    else:
        for stage, evidence in stage_evidence.items():
            if not isinstance(evidence, dict):
                stage_evidence_failures.append(stage)
                continue
            relative = str(evidence.get("file", ""))
            path = root / relative
            anchor = evidence.get("anchor")
            expected_relative, expected_anchor = EXPECTED_STAGE_EVIDENCE[stage]
            resolved = path.resolve()
            if (
                relative != expected_relative
                or anchor != expected_anchor
                or root.resolve() not in resolved.parents
                or relative not in declared_files
                or not path.is_file()
                or not isinstance(anchor, str)
                or anchor not in path.read_text(encoding="utf-8")
            ):
                stage_evidence_failures.append(stage)
    assertions["stage_evidence_anchors_resolve"] = not stage_evidence_failures

    eval_catalog = json.loads(
        (root / "outputs" / "eval-catalog.json").read_text(encoding="utf-8")
    )
    cases = eval_catalog.get("cases", [])
    case_types = [case.get("type") for case in cases]
    actual_counts = {
        "positive": case_types.count("positive"),
        "negative": case_types.count("negative"),
        "boundary": case_types.count("boundary"),
        "total": len(case_types),
    }
    assertions["eval_catalog_is_5_5_3"] = actual_counts == {
        "positive": 5,
        "negative": 5,
        "boundary": 3,
        "total": 13,
    } == eval_catalog.get("counts")
    case_ids = [case.get("id") for case in cases]
    assertions["eval_case_ids_are_unique"] = (
        len(case_ids) == len(set(case_ids)) == 13
        and all(isinstance(case_id, str) and case_id for case_id in case_ids)
    )
    assertions["eval_cases_are_not_empty_shells"] = all(
        isinstance(case.get("prompt"), str)
        and bool(case["prompt"].strip())
        and isinstance(case.get("assertions"), list)
        and bool(case["assertions"])
        and all(
            isinstance(assertion, str) and bool(assertion.strip())
            for assertion in case["assertions"]
        )
        and case.get("should_trigger") == (case.get("type") != "negative")
        for case in cases
    )

    fixture_text = (root / "fixtures" / "虚构会议记录-01.md").read_text(
        encoding="utf-8"
    )
    fixture_roles = set(re.findall(r"\*\*P\d+｜([^：]+)：\*\*", fixture_text))
    declared_roles_match = re.search(r"^- 参会角色：(.+)$", fixture_text, re.MULTILINE)
    declared_roles = (
        {role.strip() for role in declared_roles_match.group(1).split("、")}
        if declared_roles_match
        else set()
    )
    allowed_roles = set(manifest.get("allowed_roles", []))
    assertions["fixture_roles_are_fixed_and_allowlisted"] = (
        fixture_roles == EXPECTED_ROLES
        and allowed_roles == EXPECTED_ROLES
        and declared_roles == EXPECTED_ROLES - {"讨论"}
    )

    result_card = (root / "assets" / "结果卡.svg").read_text(encoding="utf-8")
    result_card_tokens = (
        "dry_run",
        "not_verified",
        "not_ready",
        "S0–S6：7/7",
        "5 正向 · 5 负向 · 3 边界",
    )
    assertions["result_card_matches_manifest"] = all(
        token in result_card for token in result_card_tokens
    )

    findings: list[dict[str, str]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".md", ".json", ".svg"}:
            continue
        text = path.read_text(encoding="utf-8")
        for name, pattern in FORBIDDEN_PATTERNS.items():
            if pattern.search(text):
                findings.append(
                    {"file": path.relative_to(root).as_posix(), "pattern": name}
                )
    assertions["no_private_paths_or_credentials"] = not findings

    failed = [name for name, passed in assertions.items() if not passed]
    return {
        "showcase": root.name,
        "result": "PASS" if not failed else "FAIL",
        "assertions_passed": sum(assertions.values()),
        "assertions_total": len(assertions),
        "failed_assertions": failed,
        "missing_files": missing,
        "empty_files": empty,
        "stage_evidence_failures": stage_evidence_failures,
        "eval_catalog_counts": actual_counts,
        "eval_case_ids": case_ids,
        "baseline_recount": {
            "passed": baseline_passed,
            "failed": baseline_failed,
            "total": baseline_passed + baseline_failed,
        },
        "fixture_roles": sorted(fixture_roles),
        "declared_roles": sorted(declared_roles),
        "sensitive_findings": findings,
        "evidence_level": manifest.get("evidence_level"),
        "host_runtime": manifest.get("host_runtime"),
    }


def main() -> int:
    try:
        result = validate_showcase()
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"result": "ERROR", "message": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
