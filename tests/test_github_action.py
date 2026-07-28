import json
import re
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "github-action-project"
ACTION = REPO_ROOT / "action.yml"
WORKFLOW = REPO_ROOT / "examples" / "github-actions" / "apple-presubmit-audit.yml"


class GitHubActionIntegrationTests(unittest.TestCase):
    def test_minimal_fixture_emits_sarif_before_returning_blocker_exit(self):
        result = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "audit.py"),
                "--config",
                "apps.json",
                "--no-asc",
                "--sarif",
            ],
            cwd=FIXTURE_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(1, result.returncode)
        report = json.loads(result.stdout)
        invocation = report["runs"][0]["invocations"][0]
        self.assertTrue(invocation["executionSuccessful"])
        self.assertEqual(1, invocation["exitCode"])
        self.assertTrue(
            any(finding["level"] == "error" for finding in report["runs"][0]["results"])
        )

    def test_copyable_workflow_is_credential_free_and_sha_pinned(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        action = ACTION.read_text(encoding="utf-8")

        self.assertIn("security-events: write", workflow)
        self.assertGreaterEqual((workflow + action).count("--no-asc"), 2)
        self.assertNotRegex(
            workflow + action,
            r"ASC_(?:KEY_ID|ISSUER_ID|KEY_FILE|PRIVATE_KEY|P8_PATH)",
        )
        self.assertNotRegex(
            action,
            r"cache-dependency-path:\s*\$\{\{\s*github\.action_path",
        )
        audit_commit = re.search(
            r"^\s*AUDIT_COMMIT:\s+(\S+)",
            workflow,
            re.MULTILINE,
        )
        self.assertIsNotNone(audit_commit)
        self.assertRegex(audit_commit.group(1), r"^[0-9a-f]{40}$")

        action_refs = re.findall(
            r"^\s*uses:\s+\S+@(\S+)",
            workflow + action,
            re.MULTILINE,
        )
        self.assertGreaterEqual(len(action_refs), 5)
        for action_ref in action_refs:
            with self.subTest(action_ref=action_ref):
                self.assertRegex(action_ref, r"^[0-9a-f]{40}$")

        audit_step = action.index("id: audit")
        upload_step = action.index("github/codeql-action/upload-sarif")
        preserve_step = action.index("Preserve audit exit status")
        self.assertLess(audit_step, upload_step)
        self.assertLess(upload_step, preserve_step)
        self.assertIn("steps.audit.outputs.exit_code", action)


if __name__ == "__main__":
    unittest.main()
