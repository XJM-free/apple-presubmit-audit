import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = REPO_ROOT / "pyproject.toml"
PACKAGE_INIT = REPO_ROOT / "__init__.py"
MANIFEST = REPO_ROOT / "MANIFEST.in"
INSTALLED_SMOKE = REPO_ROOT / "tests" / "smoke_installed_cli.py"


class PackagingContractTests(unittest.TestCase):
    def test_console_entry_point_uses_the_packaged_audit_module(self):
        metadata = PYPROJECT.read_text(encoding="utf-8")

        self.assertRegex(
            metadata,
            re.compile(
                r'^apple-presubmit-audit\s*=\s*'
                r'"apple_presubmit_audit\.audit:main"$',
                re.MULTILINE,
            ),
        )

    def test_distribution_keeps_audit_and_catalog_in_one_package(self):
        metadata = PYPROJECT.read_text(encoding="utf-8")

        self.assertTrue(PACKAGE_INIT.is_file())
        self.assertEqual("", PACKAGE_INIT.read_text(encoding="utf-8").strip())
        self.assertIn('packages = ["apple_presubmit_audit"]', metadata)
        self.assertIn("include-package-data = false", metadata)
        self.assertRegex(
            metadata,
            re.compile(
                r'^apple_presubmit_audit\s*=\s*"\."$',
                re.MULTILINE,
            ),
        )
        self.assertRegex(
            metadata,
            re.compile(
                r'^apple_presubmit_audit\s*=\s*'
                r'\["rule-catalog\.json"\]$',
                re.MULTILINE,
            ),
        )

    def test_sdist_manifest_keeps_the_source_test_suite_runnable(self):
        manifest = MANIFEST.read_text(encoding="utf-8")

        self.assertIn("include action.yml", manifest)
        self.assertIn("recursive-include .github/workflows *.yml", manifest)
        self.assertIn("recursive-include examples *.yml", manifest)
        self.assertIn(
            "recursive-include tests *.json *.md *.pbxproj *.py *.swift",
            manifest,
        )

    def test_distribution_reuses_runtime_dependency_constraints(self):
        metadata = PYPROJECT.read_text(encoding="utf-8")

        self.assertIn('dynamic = ["dependencies"]', metadata)
        self.assertRegex(
            metadata,
            re.compile(
                r'^dependencies\s*=\s*'
                r'\{file\s*=\s*\["requirements\.txt"\]\}$',
                re.MULTILINE,
            ),
        )

    def test_installed_smoke_runs_the_core_code_only_audit(self):
        smoke = INSTALLED_SMOKE.read_text(encoding="utf-8")

        self.assertIn('"--project"', smoke)
        self.assertIn('"--no-asc"', smoke)
        self.assertIn('"--json"', smoke)
        self.assertIn('report.get("total_blockers")', smoke)


if __name__ == "__main__":
    unittest.main()
