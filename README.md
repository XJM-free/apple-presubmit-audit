# Apple App Store Pre-Submit Audit

[![Tests](https://github.com/XJM-free/apple-presubmit-audit/actions/workflows/tests.yml/badge.svg)](https://github.com/XJM-free/apple-presubmit-audit/actions/workflows/tests.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB.svg)](https://www.python.org/downloads/)
[![MIT License](https://img.shields.io/badge/license-MIT-2ea44f.svg)](./LICENSE)

A local Python CLI that surfaces potential App Store submission issues before
review: inconsistent metadata, unused permission declarations, incomplete
subscription disclosures, suspicious entitlement state, and project-specific
release risks.

It is a preflight assistant, not an App Review guarantee. The checks combine
[Apple's published guidelines](https://developer.apple.com/app-store/review/guidelines/)
with conservative, submission-derived heuristics.

```text
🔴 MyApp                [passed=24 skipped=0 total=27] blockers=1
   🔴 OFFICIAL 2.3.7 name-length          App Store name too long (34 chars, max 30)
   ⚠️  ADVISORY 3.1.2(c) renewal-disclosure-copy
                                              Heuristic: verify that price, duration,
                                              and renewal terms are clear
   ℹ️  ADVISORY 4.2 minimum-functionality-shape
                                              Heuristic: file counts do not determine
                                              compliance; review the experience
```

The output above is illustrative.

## What it checks

The audit combines a baseline rule set with condition-aware checks across
Apple's five review categories and additional engineering checks.

- A baseline set runs for every project; metadata-only findings are treated as
  `not_evaluated` when `--no-asc` supplies no corresponding field.
- Extra checks activate when the project declares permissions, subscriptions,
  accounts, third-party login, CloudKit, AI APIs, a paywall, or other relevant
  features.
- A synthetic coverage fixture exercises the broad conditional catalog; a
  normal project runs only the checks relevant to the signals it exposes.

| Area | Examples |
|---|---|
| Safety | misleading sensor or medical claims, Kids Category advertising |
| Performance | metadata completeness, app-name length, implementation evidence for advertised features |
| Business | subscription disclosure, restore flow, privacy and terms links, purchase-price prominence |
| Design | minimum-functionality and duplicate-app heuristics, Sign in with Apple |
| Legal | privacy policy, account deletion, permissions matched to framework use |
| Custom | StoreKit state, CloudKit save patterns, SwiftData defaults, paywall claims matched to code |

See [`audit.py`](./audit.py) for the implementation of every check.

## Quick start

```bash
git clone https://github.com/XJM-free/apple-presubmit-audit.git
cd apple-presubmit-audit

python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

Audit one project against App Store Connect metadata:

```bash
python3 audit.py \
  --project ~/Code/MyApp \
  --bundle-id com.example.myapp \
  --key-id ABC123XYZ \
  --issuer-id 12345-67890-... \
  --key-file ~/AuthKey_ABC123XYZ.p8
```

The credentials can also come from environment variables:

```bash
export ASC_KEY_ID=ABC123XYZ
export ASC_ISSUER_ID=12345-67890-...
export ASC_KEY_FILE=~/AuthKey_ABC123XYZ.p8

python3 audit.py --project ~/Code/MyApp --bundle-id com.example.myapp
```

Code-only mode skips App Store Connect. It is useful for local iteration, but
metadata-dependent checks will not have enough information:

```bash
python3 audit.py --project ~/Code/MyApp --no-asc
```

For several apps, copy [`apps.example.json`](./apps.example.json) to `apps.json`
and run:

```bash
python3 audit.py --config apps.json
python3 audit.py --config apps.json --quiet
python3 audit.py --config apps.json --json
python3 audit.py --config apps.json --sarif > audit.sarif
```

Never commit App Store Connect credentials. This repository ignores common
private-key, provisioning-profile, environment, and local app-config files by
default.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | No blocker was detected among the checks that ran |
| `1` | One or more blocker checks failed |
| `2` | Project/config input is invalid, or App Store Connect data could not be fetched safely |

Do not treat exit code `0` as proof that Apple will approve an app.

Configuration failures are written to stderr. With `--json`, stdout remains
valid JSON and includes an `errors` array, so CI callers can distinguish invalid
input from review findings.

In JSON output, `passed` is `true`, `false`, or `null`; `null` is paired with
`"status": "not_evaluated"` and is never counted as a blocker.

`--sarif` emits SARIF 2.1.0 while preserving the same exit codes. Failed
findings become results (`blocker` → `error`, `high` → `warning`, `low` →
`note`); passed and `not_evaluated` rules are omitted. Configuration failures
become tool execution notifications. Run the command from the repository root
when uploading the report to GitHub Code Scanning. Because most checks combine
project-wide code and App Store Connect metadata, SARIF locations point to a
real project file as an explicitly labeled audit anchor, not an exact match
line. If no safe repository-relative project file exists, the finding remains
locationless instead of exposing an absolute local path.

## How to read the findings

Every rule ID starts with its evidence basis:

- `OFFICIAL` — directly validates a field or limit published by Apple, such as
  the [30-character app-name limit](https://developer.apple.com/app-store/review/guidelines/#accurate-metadata),
  a required
  [Support URL](https://developer.apple.com/help/app-store-connect/reference/app-information/platform-version-information/),
  or a published
  [age-rating value](https://developer.apple.com/documentation/appstoreconnectapi/appstoreagerating).
- `READINESS` — directly observes a submission or StoreKit catalog state that
  can prevent the intended release or purchase flow.
- `ADVISORY` — a regex, keyword, typography, file-count, or submission-derived
  heuristic. It is evidence to inspect, not proof of an Apple violation.

Apple does not publish a 200-character minimum for review notes, a 36-point
price-font rule, a minimum number of SwiftUI views, or a mandatory literal
`auto-renewing` CTA phrase. Those checks are therefore labeled `ADVISORY`.

Treat findings as prompts for review:

1. Confirm the relevant guideline and current App Store Connect requirements.
2. Inspect the matched code or metadata.
3. Fix real issues and dismiss false positives with project context.

Severity describes release impact:

- `blocker` — reserved for `OFFICIAL` or directly observed `READINESS` findings.
- `high` — a significant manual-review prompt.
- `low` — a lower-confidence or product-quality prompt.

`ADVISORY` findings are enforced in code and tests to never use `blocker`
severity or hard-requirement wording.

## Limitations

- Swift and plist inspection is regex-based; generated code and dynamic framework
  loading can produce false negatives.
- Some checks are deliberately conservative and can produce false positives.
- The tool does not inspect the final signed binary or screenshots.
- App Store Connect does not expose every review field through its API.
- Apple can change its guidelines and reviewer behavior independently of this
  repository.

Always perform a manual final review.

## Development

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile audit.py
```

Contributions are welcome. Read [`CONTRIBUTING.md`](./CONTRIBUTING.md) before
adding a rule, and include both a triggering fixture and a non-triggering
fixture when possible.

## License

[MIT](./LICENSE)
