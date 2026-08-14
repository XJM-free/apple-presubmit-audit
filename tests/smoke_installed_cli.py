#!/usr/bin/env python3
"""Smoke-test an installed wheel or sdist from outside the source checkout."""

import json
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path

from apple_presubmit_audit import audit


def run(command, cwd):
    return subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def main(argv):
    if len(argv) != 2:
        raise AssertionError(
            "pass the source rule-catalog.json and project fixture paths"
        )
    source_catalog = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    project_fixture = Path(argv[1]).resolve()
    if not project_fixture.is_dir():
        raise AssertionError("the project fixture is missing")
    prefix = Path(sys.prefix).resolve()
    module_path = Path(audit.__file__).resolve()
    catalog_path = audit.RULE_CATALOG_PATH.resolve()
    if prefix not in module_path.parents or prefix not in catalog_path.parents:
        raise AssertionError("the smoke test imported files outside the fresh environment")
    if not catalog_path.is_file():
        raise AssertionError("the installed rule catalog is missing")
    if audit.load_rule_catalog() != source_catalog:
        raise AssertionError("the installed rule catalog differs from source")
    if source_catalog["schema_version"] != 2 or len(source_catalog["rules"]) != 58:
        raise AssertionError("unexpected rule catalog contract")

    executable = Path(sysconfig.get_path("scripts")) / "apple-presubmit-audit"
    if not executable.is_file():
        raise AssertionError("the installed console entry point is missing")

    with tempfile.TemporaryDirectory(prefix="apple-presubmit-audit-smoke.") as temp:
        cwd = Path(temp)
        catalog = run([executable, "--rule-catalog"], cwd)
        if catalog.returncode != 0 or json.loads(catalog.stdout) != source_catalog:
            raise AssertionError("--rule-catalog failed from outside the checkout")

        static = run(
            [executable, "--explain", "OFFICIAL 2.3.7 name-length"], cwd
        )
        if (
            static.returncode != 0
            or "Family: OFFICIAL 2.3.7 name-length" not in static.stdout
        ):
            raise AssertionError("static --explain lookup failed")

        dynamic = run(
            [
                executable,
                "--explain",
                "READINESS CUSTOM sub-availability-com.example.app",
            ],
            cwd,
        )
        expected_family = "Family: READINESS CUSTOM sub-availability-{product_id}"
        if dynamic.returncode != 0 or expected_family not in dynamic.stdout:
            raise AssertionError("dynamic --explain lookup failed")

        sentinel = "PRIVATE-UNKNOWN-RULE-SENTINEL"
        unknown = run([executable, "--explain", sentinel], cwd)
        if unknown.returncode != 2:
            raise AssertionError("unknown --explain lookup must return exit code 2")
        if sentinel in unknown.stdout or sentinel in unknown.stderr:
            raise AssertionError("unknown --explain lookup echoed its input")

        project_audit = run(
            [
                executable,
                "--project",
                project_fixture,
                "--no-asc",
                "--json",
            ],
            cwd,
        )
        if project_audit.returncode != 0:
            raise AssertionError("installed code-only project audit failed")
        report = json.loads(project_audit.stdout)
        if report.get("errors") != [] or report.get("total_blockers") != 0:
            raise AssertionError("installed project audit returned errors or blockers")
        apps = report.get("apps")
        if not isinstance(apps, list) or len(apps) != 1:
            raise AssertionError("installed project audit returned an invalid app list")
        rules = apps[0].get("rules")
        if not isinstance(rules, list) or not rules:
            raise AssertionError("installed project audit did not run any rules")
        statuses = {rule.get("status") for rule in rules}
        if not {"passed", "not_evaluated"}.issubset(statuses):
            raise AssertionError(
                "installed --no-asc audit did not preserve evaluation states"
            )

    print(f"installed CLI smoke passed: {module_path}")


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except (AssertionError, json.JSONDecodeError, OSError) as exc:
        print(f"installed CLI smoke failed: {exc}", file=sys.stderr)
        sys.exit(1)
