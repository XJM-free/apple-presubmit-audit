import ast
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import audit  # noqa: E402


class AuditRuleTests(unittest.TestCase):
    def test_minimal_project_runs_the_baseline_rule_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = audit.audit_app(tmp, {})

        rule_ids = [result[0] for result in results]
        self.assertGreaterEqual(len(rule_ids), 20)
        self.assertEqual(len(rule_ids), len(set(rule_ids)))
        self.assertTrue(all(
            rule.startswith(("OFFICIAL ", "READINESS ", "ADVISORY "))
            for rule in rule_ids
        ))

    def test_relevant_features_expand_the_catalog_without_duplicates(self):
        with tempfile.TemporaryDirectory() as baseline_tmp:
            baseline_ids = {
                result[0] for result in audit.audit_app(baseline_tmp, {})
            }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_coverage_project(root)
            results = audit.audit_app(root, self._coverage_metadata())

        rule_ids = {result[0] for result in results}
        self.assertGreater(len(rule_ids), len(baseline_ids))
        self.assertEqual(len(results), len(rule_ids))
        self.assertIn(
            "ADVISORY 2.5.1 NSCameraUsageDescription",
            rule_ids,
        )
        self.assertIn(
            "ADVISORY 3.1.2(c) renewal-disclosure-copy",
            rule_ids,
        )
        self.assertIn(
            "ADVISORY CUSTOM paywall-benefit-icloud_sync",
            rule_ids,
        )
        self.assertIn(
            "READINESS CUSTOM sub-never-submitted-product.one",
            rule_ids,
        )

    def test_advisories_never_block_or_assert_hard_requirements(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_coverage_project(root)
            results = audit.audit_app(root, self._coverage_metadata())

        advisories = [result for result in results if result[0].startswith("ADVISORY ")]
        self.assertGreater(len(advisories), 40)
        for rule, severity, _passed, message in advisories:
            with self.subTest(rule=rule):
                self.assertIn(severity, {"high", "low"})
                self.assertNotEqual("blocker", severity)
                self.assertIsNone(
                    re.search(r"\b(?:must|required)\b", message, re.IGNORECASE)
                )

        tree = ast.parse((REPO_ROOT / "audit.py").read_text(encoding="utf-8"))
        advisory_calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "advisory"
        ]
        self.assertGreater(len(advisory_calls), 30)
        for call in advisory_calls:
            severity = call.args[1]
            self.assertIsInstance(severity, ast.Constant)
            self.assertIn(severity.value, {"high", "low"})

    def test_current_published_age_rating_values_are_accepted(self):
        for rating in ("THIRTEEN_PLUS", "SIXTEEN_PLUS", "EIGHTEEN_PLUS"):
            with self.subTest(rating=rating), tempfile.TemporaryDirectory() as tmp:
                results = audit.audit_app(
                    tmp,
                    {
                        "appStoreAgeRating": rating,
                        "description": "A complete and accurate app description.",
                        "name": "Fixture",
                    },
                )
            age_rule = next(
                result for result in results
                if result[0] == "OFFICIAL 2.3.6 age-rating-set"
            )
            self.assertTrue(age_rule[2])

    def test_missing_project_reports_human_error_and_exit_two(self):
        result = self._run_cli(
            "--project",
            "/tmp/apple-presubmit-audit-path-that-does-not-exist",
            "--no-asc",
        )
        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertIn(
            "Configuration error: project path for "
            "'apple-presubmit-audit-path-that-does-not-exist' "
            "is not a directory:",
            result.stderr,
        )

    def test_missing_project_reports_structured_json_error(self):
        result = self._run_cli(
            "--project",
            "/tmp/apple-presubmit-audit-path-that-does-not-exist",
            "--no-asc",
            "--json",
        )

        self.assertEqual(2, result.returncode)
        report = json.loads(result.stdout)
        self.assertEqual([], report["apps"])
        self.assertEqual(0, report["total_blockers"])
        self.assertEqual("invalid_project_path", report["errors"][0]["code"])
        self.assertIn("Configuration error:", result.stderr)

    def test_config_rejects_missing_and_non_directory_project_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            regular_file = root / "NotAProject.txt"
            regular_file.write_text("not a directory", encoding="utf-8")
            config = root / "apps.json"
            config.write_text(json.dumps([
                {
                    "name": "MissingApp",
                    "project": str(root / "missing"),
                    "bundle_id": "com.example.missing",
                },
                {
                    "name": "FileApp",
                    "project": str(regular_file),
                    "bundle_id": "com.example.file",
                },
            ]), encoding="utf-8")

            result = self._run_cli(
                "--config",
                str(config),
                "--no-asc",
                "--json",
            )

        self.assertEqual(2, result.returncode)
        report = json.loads(result.stdout)
        self.assertEqual(
            ["invalid_project_path", "invalid_project_path"],
            [error["code"] for error in report["errors"]],
        )
        self.assertEqual(2, result.stderr.count("Configuration error:"))

    def test_invalid_config_json_reports_parse_location_and_exit_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "apps.json"
            config.write_text('[{"name": "Broken",}]', encoding="utf-8")

            result = self._run_cli(
                "--config",
                str(config),
                "--no-asc",
                "--json",
            )

        self.assertEqual(2, result.returncode)
        report = json.loads(result.stdout)
        error = report["errors"][0]
        self.assertEqual("invalid_config_json", error["code"])
        self.assertEqual(1, error["line"])
        self.assertGreater(error["column"], 1)
        self.assertIn("cannot parse config file", result.stderr)

    def test_unreadable_config_path_reports_stable_error_and_exit_two(self):
        result = self._run_cli(
            "--config",
            "/tmp/apple-presubmit-audit-config-that-does-not-exist.json",
            "--no-asc",
            "--json",
        )

        self.assertEqual(2, result.returncode)
        report = json.loads(result.stdout)
        self.assertEqual("config_unreadable", report["errors"][0]["code"])
        self.assertIn("cannot read config file", result.stderr)

    def test_non_utf8_config_reports_decode_error_and_exit_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "apps.json"
            config.write_bytes(b"\xff\xfe\x00")

            result = self._run_cli(
                "--config",
                str(config),
                "--no-asc",
                "--json",
            )

        self.assertEqual(2, result.returncode)
        report = json.loads(result.stdout)
        self.assertEqual("invalid_config_encoding", report["errors"][0]["code"])
        self.assertIn("cannot decode config file", result.stderr)

    def test_dot_project_uses_resolved_directory_name(self):
        result = self._run_cli(
            "--project",
            ".",
            "--no-asc",
            "--json",
            cwd=REPO_ROOT,
        )

        self.assertEqual(0, result.returncode)
        report = json.loads(result.stdout)
        self.assertEqual("apple-presubmit-audit", report["apps"][0]["app"])
        self.assertEqual([], report["errors"])
        self.assertEqual(0, report["total_blockers"])
        self.assertTrue(all(
            rule["basis"] in {"OFFICIAL", "READINESS", "ADVISORY"}
            for rule in report["apps"][0]["rules"]
        ))
        metadata_rules = [
            rule for rule in report["apps"][0]["rules"]
            if rule["rule"] in {
                "OFFICIAL 1.5 support-url",
                "OFFICIAL 2.1 description-present",
                "OFFICIAL 5.1.1(i) privacy-asc",
                "OFFICIAL 2.3.6 age-rating-set",
                "READINESS 2.3.6 appinfo-not-rejected",
                "OFFICIAL 1.5 all-locales-have-support-url",
            }
        ]
        self.assertEqual(6, len(metadata_rules))
        self.assertTrue(all(
            rule["passed"] is None
            and rule["status"] == "not_evaluated"
            for rule in metadata_rules
        ))

    def test_invalid_private_key_reports_sanitized_authentication_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key_file = root / "synthetic-invalid-key.p8"
            synthetic_key = "not-a-private-key"
            key_file.write_text(synthetic_key, encoding="utf-8")

            result = self._run_cli(
                "--project",
                str(root),
                "--bundle-id",
                "com.example.synthetic-fixture",
                "--key-id",
                "SYNTHETIC",
                "--issuer-id",
                "00000000-0000-0000-0000-000000000000",
                "--key-file",
                str(key_file),
                "--json",
            )

        self.assertEqual(2, result.returncode)
        report = json.loads(result.stdout)
        self.assertEqual([], report["apps"])
        self.assertEqual(
            "asc_authentication_failed",
            report["errors"][0]["code"],
        )
        self.assertNotIn(synthetic_key, result.stdout)
        self.assertNotIn(synthetic_key, result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_missing_private_key_file_reports_structured_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self._run_cli(
                "--project",
                str(root),
                "--bundle-id",
                "com.example.synthetic-fixture",
                "--key-id",
                "SYNTHETIC",
                "--issuer-id",
                "00000000-0000-0000-0000-000000000000",
                "--key-file",
                str(root / "missing-synthetic-key.p8"),
                "--json",
            )

        self.assertEqual(2, result.returncode)
        report = json.loads(result.stdout)
        self.assertEqual("key_file_unreadable", report["errors"][0]["code"])
        self.assertNotIn("Traceback", result.stderr)

    def test_asc_http_authentication_error_is_sanitized(self):
        client = audit.ASCClient.__new__(audit.ASCClient)
        client._token = mock.Mock(return_value="synthetic-token")
        client.s = mock.Mock()
        client.s.get.return_value = mock.Mock(ok=False, status_code=401)

        with self.assertRaises(audit.ASCRequestError) as context:
            client.get("/v1/apps")

        self.assertEqual("asc_authentication_failed", context.exception.code)
        self.assertEqual(
            "App Store Connect rejected the supplied credentials (HTTP 401)",
            str(context.exception),
        )
        self.assertNotIn("synthetic-token", str(context.exception))

    def test_asc_network_error_retries_without_exposing_exception_detail(self):
        client = audit.ASCClient.__new__(audit.ASCClient)
        client._token = mock.Mock(return_value="synthetic-token")
        client.s = mock.Mock()
        client.s.get.side_effect = audit.requests.ConnectionError(
            "synthetic-private-detail"
        )

        with (
            mock.patch.object(audit.time, "sleep") as sleep,
            self.assertRaises(audit.ASCRequestError) as context,
        ):
            client.get("/v1/apps")

        self.assertEqual("asc_network_error", context.exception.code)
        self.assertEqual(3, client.s.get.call_count)
        self.assertEqual(2, sleep.call_count)
        self.assertNotIn(
            "synthetic-private-detail",
            str(context.exception),
        )

    @staticmethod
    def _write_coverage_project(root):
        plist_keys = [
            "CFBundleDisplayName",
            "NSHealthShareUsageDescription",
            "NSHealthUpdateUsageDescription",
            "NSCalendarsUsageDescription",
            "NSCameraUsageDescription",
            "NSContactsUsageDescription",
            "NSLocationWhenInUseUsageDescription",
            "NSMicrophoneUsageDescription",
            "NSPhotoLibraryUsageDescription",
            "NSMotionUsageDescription",
            "NSBluetoothAlwaysUsageDescription",
            "NSFaceIDUsageDescription",
            "NSRemindersUsageDescription",
            "NSUserNotificationsUsageDescription",
        ]
        plist = "".join(
            f"<key>{key}</key><string>"
            f"{'Fixture' if key == 'CFBundleDisplayName' else 'Needed'}"
            "</string>"
            for key in plist_keys
        )
        (root / "Info.plist").write_text(
            f"<plist><dict>{plist}</dict></plist>",
            encoding="utf-8",
        )
        (root / "PaywallView.swift").write_text(
            """
import SwiftUI
struct PaywallView: View {
    var body: some View {
        Text("iCloud sync CSV export unlimited notifications PDF export "
             "calendar export photo attachments advanced charts and trends "
             "themes multiple kits voice guidance double elimination "
             "auto-renewing free trial price after trial Restore Privacy Terms EULA")
    }
}
""",
            encoding="utf-8",
        )
        (root / "LoginView.swift").write_text(
            'import SwiftUI\nText("Continue with Google or Facebook")\n',
            encoding="utf-8",
        )
        (root / "NotificationManager.swift").write_text(
            "UNUserNotificationCenter.current().requestAuthorization()\n",
            encoding="utf-8",
        )
        (root / "SubscriptionManager.swift").write_text(
            "Product.products(for: [])\n"
            "Transaction.currentEntitlements\n"
            "Transaction.updates\n",
            encoding="utf-8",
        )
        for index in range(4):
            (root / f"Feature{index}View.swift").write_text(
                "import SwiftUI\n"
                f"struct Feature{index}View: View {{ "
                'var body: some View { Text("Feature") } }\n',
                encoding="utf-8",
            )

    @staticmethod
    def _coverage_metadata():
        return {
            "description": (
                "This app purpose describes play along audio playback and "
                "identify AI photos for health. It is for kids, can share "
                "personal data, contains famous quotes, uses VPN features, "
                "and acts as a detector. Terms of use: "
                "https://example.com/terms. "
            )
            * 4,
            "notes": (
                "Review test steps explain the app purpose, external service "
                "and API, supported region and country, VPN behavior, and that "
                "the detector uses built-in sensors with no external hardware. "
            )
            * 4,
            "name": "Fixture",
            "category": "Kids",
            "gamblingSimulated": "NONE",
            "appStoreAgeRating": "FOUR_PLUS",
            "appInfoState": "READY_FOR_SUBMISSION",
            "has_account": True,
            "sub_state": "DEVELOPER_ACTION_NEEDED",
            "sub_territories": {"product.one": 1},
            "sub_states": [("product.one", "READY_TO_SUBMIT")],
            "sub_group_loc_states": [
                ("group.one", "en-US", "PREPARE_FOR_SUBMISSION")
            ],
            "locales_missing_support": ["fr-FR"],
        }

    @staticmethod
    def _run_cli(*args, cwd=None):
        command = [sys.executable, str(REPO_ROOT / "audit.py"), *args]
        return subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )


if __name__ == "__main__":
    unittest.main()
