from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch


PLUGIN_ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


init_product = load_module("init_product", PLUGIN_ROOT / "scripts" / "init_product.py")
validate_product = load_module(
    "validate_product", PLUGIN_ROOT / "scripts" / "validate_product.py"
)
build_package = load_module(
    "build_package", PLUGIN_ROOT / "scripts" / "build_package.py"
)
create_release_status = load_module(
    "create_release_status",
    PLUGIN_ROOT / "scripts" / "create_release_status.py",
)
verify_showcase = load_module(
    "verify_showcase", PLUGIN_ROOT / "scripts" / "verify_showcase.py"
)


def write_evidence_report(
    path: Path,
    evidence_type: str,
    product_version: str,
    *,
    evaluated_at: str = "2026-07-26T12:00:00+08:00",
) -> None:
    path.write_text(
        "\n".join(
            (
                "RELEASE_GATE: PASS",
                f"EVIDENCE_TYPE: {evidence_type}",
                f"PRODUCT_VERSION: {product_version}",
                f"EVALUATED_AT: {evaluated_at}",
                "",
                "# Test evidence",
                "",
            )
        ),
        encoding="utf-8",
    )


def write_release_evidence(root: Path, *, live: bool = False) -> dict:
    reports = root / "reports"
    reports.mkdir(exist_ok=True)
    evidence_paths = {
        "static_validation": "reports/static.md",
        "behavior_evaluation": "reports/behavior.md",
        "independent_judge": "reports/judge.md",
        "security_review": "reports/security.md",
    }
    manifest = json.loads(
        (root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    for evidence_type, relative in evidence_paths.items():
        write_evidence_report(root / relative, evidence_type, manifest["version"])
    digest = build_package.source_sha256(root, root / "release")
    evidence = {
        "product_version": manifest["version"],
        "source_sha256": digest,
        "generated_at": "2026-07-26T12:00:00+08:00",
        "static_validation": "passed",
        "behavior_evaluation": "live_passed" if live else "dry_run_passed",
        "independent_judge": "passed",
        "security_review": "professional_passed" if live else "static_passed",
        "host_runtime": "verified" if live else "not_verified",
        "approved_for_packaging": True,
        "release_channel": "public_release" if live else "internal_candidate",
        "evidence_paths": evidence_paths,
    }
    (root / "release-status.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return evidence


class FactoryTests(unittest.TestCase):
    def test_showcase_is_complete_and_honest(self):
        result = verify_showcase.validate_showcase()
        self.assertEqual(result["result"], "PASS", msg=json.dumps(result, ensure_ascii=False))
        self.assertEqual(
            result["assertions_passed"], result["assertions_total"]
        )

    def test_rejects_invalid_product_id(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            init_product.validate_product_id("Bad Name")

    def test_initializes_and_validates_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            args = argparse.Namespace(
                product_id="meeting-follow-up",
                output=directory,
                artifact_type="skill",
                owner="测试负责人",
                display_name="会议跟进工具",
                dry_run=False,
            )
            target = init_product.create_workspace(args)
            self.assertTrue((target / "design.md").is_file())
            self.assertTrue(
                (
                    target
                    / "metrics"
                    / "Skill开发指标字典与Stage-Gate模板.xlsx"
                ).is_file()
            )
            product = json.loads((target / "product.json").read_text(encoding="utf-8"))
            self.assertEqual(product["product_id"], "meeting-follow-up")
            kind, findings = validate_product.validate(target, "project")
            self.assertEqual(kind, "project")
            self.assertFalse([item for item in findings if item.level == "error"])

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            args = argparse.Namespace(
                product_id="dry-run-demo",
                output=directory,
                artifact_type="auto",
                owner="测试负责人",
                display_name=None,
                dry_run=True,
            )
            target = init_product.create_workspace(args)
            self.assertFalse(target.exists())

    def test_existing_target_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "existing-demo"
            target.mkdir()
            args = argparse.Namespace(
                product_id="existing-demo",
                output=directory,
                artifact_type="skill",
                owner="测试负责人",
                display_name=None,
                dry_run=False,
            )
            with self.assertRaises(FileExistsError):
                init_product.create_workspace(args)

    def test_json_values_are_escaped(self):
        with tempfile.TemporaryDirectory() as directory:
            args = argparse.Namespace(
                product_id="json-escape-demo",
                output=directory,
                artifact_type="plugin",
                owner='负责人 "A"\\第二组',
                display_name='工具 "A"',
                dry_run=False,
            )
            target = init_product.create_workspace(args)
            status = json.loads(
                (target / "stage-status.json").read_text(encoding="utf-8")
            )
            self.assertEqual(status["owner"], '负责人 "A"\\第二组')

    def test_initialization_failure_leaves_no_partial_product(self):
        with tempfile.TemporaryDirectory() as directory:
            args = argparse.Namespace(
                product_id="atomic-demo",
                output=directory,
                artifact_type="skill",
                owner="测试负责人",
                display_name=None,
                dry_run=False,
            )
            with patch.object(
                init_product.shutil, "copy2", side_effect=OSError("simulated failure")
            ):
                with self.assertRaises(OSError):
                    init_product.create_workspace(args)
            self.assertFalse((Path(directory) / "atomic-demo").exists())
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_plugin_source_validates(self):
        kind, findings = validate_product.validate(PLUGIN_ROOT, "plugin")
        self.assertEqual(kind, "plugin")
        self.assertFalse(
            [item for item in findings if item.level == "error"],
            msg="\n".join(f"{item.code}: {item.path}" for item in findings),
        )

    def test_project_rejects_invalid_stage_status(self):
        with tempfile.TemporaryDirectory() as directory:
            args = argparse.Namespace(
                product_id="invalid-stage-demo",
                output=directory,
                artifact_type="skill",
                owner="测试负责人",
                display_name=None,
                dry_run=False,
            )
            target = init_product.create_workspace(args)
            status_path = target / "stage-status.json"
            status = json.loads(status_path.read_text(encoding="utf-8"))
            status["stages"]["S1"] = "unknown"
            status_path.write_text(
                json.dumps(status, ensure_ascii=False), encoding="utf-8"
            )
            _, findings = validate_product.validate(target, "project")
            self.assertIn("invalid_stage_value", {item.code for item in findings})

    def test_project_requires_minimum_eval_catalog(self):
        with tempfile.TemporaryDirectory() as directory:
            args = argparse.Namespace(
                product_id="small-eval-demo",
                output=directory,
                artifact_type="skill",
                owner="测试负责人",
                display_name=None,
                dry_run=False,
            )
            target = init_product.create_workspace(args)
            eval_path = target / "evals" / "evals.json"
            data = json.loads(eval_path.read_text(encoding="utf-8"))
            data["cases"] = data["cases"][:3]
            eval_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            _, findings = validate_product.validate(target, "project")
            self.assertIn(
                "insufficient_project_evals", {item.code for item in findings}
            )

    def test_trigger_catalog_has_minimum_cases(self):
        catalog = json.loads(
            (PLUGIN_ROOT / "evals" / "trigger-cases.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            set(catalog["skills"]),
            {
                "develop-ai-tool",
                "research-ai-tool",
                "build-ai-tool",
                "evaluate-ai-tool",
            },
        )
        prompts = []
        for groups in catalog["skills"].values():
            self.assertGreaterEqual(len(groups["positive"]), 5)
            self.assertGreaterEqual(len(groups["negative"]), 5)
            self.assertGreaterEqual(len(groups["boundary"]), 3)
            prompts.extend(groups["positive"] + groups["negative"] + groups["boundary"])
        self.assertEqual(len(prompts), len(set(prompts)))

    def test_candidate_package_is_atomic_and_excludes_output(self):
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / PLUGIN_ROOT.name
            shutil.copytree(
                PLUGIN_ROOT,
                copied,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "release"),
            )
            write_release_evidence(copied)
            package, hash_file = build_package.build(
                copied, copied / "release", "internal-candidate"
            )
            self.assertTrue(package.is_file())
            self.assertTrue(hash_file.is_file())
            with zipfile.ZipFile(package) as archive:
                self.assertIsNone(archive.testzip())
                self.assertNotIn(package.name, archive.namelist())

    def test_public_release_requires_live_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / PLUGIN_ROOT.name
            shutil.copytree(
                PLUGIN_ROOT,
                root,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "release"),
            )
            evidence = write_release_evidence(root)
            with self.assertRaises(ValueError):
                build_package.validate_release_evidence(
                    root,
                    "public-release",
                    evidence["product_version"],
                    evidence["source_sha256"],
                )

    def test_candidate_package_requires_release_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                build_package.validate_release_evidence(
                    Path(directory), "internal-candidate", "0.1.0", "0" * 64
                )

    def test_source_change_invalidates_release_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / PLUGIN_ROOT.name
            shutil.copytree(
                PLUGIN_ROOT,
                root,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "release"),
            )
            evidence = write_release_evidence(root)
            (root / "使用说明.md").write_text("changed\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                build_package.validate_release_evidence(
                    root,
                    "internal-candidate",
                    evidence["product_version"],
                    build_package.source_sha256(root),
                )

    def test_release_status_generator_binds_reports_and_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / PLUGIN_ROOT.name
            shutil.copytree(
                PLUGIN_ROOT,
                root,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "release"),
            )
            reports = root / "reports"
            reports.mkdir(exist_ok=True)
            manifest = json.loads(
                (root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
            )
            report_types = {
                "static.md": "static_validation",
                "behavior.md": "behavior_evaluation",
                "judge.md": "independent_judge",
                "security.md": "security_review",
            }
            for name, evidence_type in report_types.items():
                write_evidence_report(
                    reports / name, evidence_type, manifest["version"]
                )
            args = argparse.Namespace(
                plugin_root=str(root),
                static_report="reports/static.md",
                behavior_report="reports/behavior.md",
                judge_report="reports/judge.md",
                security_report="reports/security.md",
                behavior="dry-run",
                security="static",
                host_runtime="not_verified",
                channel="internal-candidate",
                replace=True,
                approve=True,
            )
            target = create_release_status.create_status(args)
            status = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(status["source_sha256"], build_package.source_sha256(root))
            self.assertEqual(status["release_channel"], "internal_candidate")

    def test_evidence_report_rejects_wrong_type(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "static.md"
            write_evidence_report(path, "behavior_evaluation", "0.1.1")
            with self.assertRaisesRegex(ValueError, "type mismatch"):
                build_package.parse_evidence_report(
                    path, "static_validation", "0.1.1"
                )

    def test_evidence_report_rejects_stale_version(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "static.md"
            write_evidence_report(path, "static_validation", "0.1.0")
            with self.assertRaisesRegex(ValueError, "version mismatch"):
                build_package.parse_evidence_report(
                    path, "static_validation", "0.1.1"
                )

    def test_evidence_report_rejects_invalid_or_naive_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "static.md"
            for evaluated_at in ("not-a-time", datetime.now().isoformat()):
                write_evidence_report(
                    path,
                    "static_validation",
                    "0.1.1",
                    evaluated_at=evaluated_at,
                )
                with self.assertRaisesRegex(ValueError, "EVALUATED_AT"):
                    build_package.parse_evidence_report(
                        path, "static_validation", "0.1.1"
                    )

    def test_archive_rejects_symbolic_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.txt"
            target.write_text("safe", encoding="utf-8")
            with patch.object(Path, "is_symlink", return_value=True):
                with self.assertRaises(ValueError):
                    build_package.validate_archive_path(root, target)

    def test_archive_rejects_outside_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "plugin"
            root.mkdir()
            outside = Path(directory) / "outside.txt"
            outside.write_text("private", encoding="utf-8")
            with self.assertRaises(ValueError):
                build_package.validate_archive_path(root, outside)


if __name__ == "__main__":
    unittest.main()
