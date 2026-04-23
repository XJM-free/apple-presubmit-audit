# Apple App Store Pre-Submit Audit

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#contributing)
![Rules: 70+](https://img.shields.io/badge/rules-70+-success)
![Lessons: 50+ rejections](https://img.shields.io/badge/distilled%20from-50%2B%20real%20rejections-orange)

> **70+ static checks codifying ~50 real Apple App Store rejections** across one indie developer's submission history.
> Catches preventable mistakes — plist mismatches, missing "auto-renewing" CTAs, declared-but-unused permissions, paywall-benefit lies, SwiftData migration crashes — **before you hit Submit**.
>
> Maintained by an indie dev who has shipped [53 iOS apps](https://github.com/XJM-free/iOS-apps-portfolio). Each new rule maps to a specific rejection that cost a week of resubmission.

## Why this exists

Every App Store rejection is a strike on your account. Stack enough strikes and Apple silently raises your review bar. This tool helps independent developers **stay compliant** — it is a quality gate, not a workaround. If your app design genuinely violates a guideline, fix the design; this script only catches the mechanical mistakes (typos, forgot a key, missing disclosure) that cause most preventable rejections.

If you're an indie shipping carefully, this saves you days. If you're trying to mass-produce shovelware, this tool will not help you and Apple's 4.3 Spam policy will catch you regardless.

```
🔴 MyApp                [22/27 passed]   blockers=2
   🔴 2.3.8 plist-name-matches-asc        Info.plist 'MyApp' != ASC name 'MyAwesome - Tracker'
   🔴 3.1.2(c) auto-renewing-CTA          subscribe button must say 'auto-renewing'
   ⚠️  4.3 unique-views-anti-spam          need ≥3 unique custom views, has 2
```

## What it doesn't do

- Doesn't make a low-effort app pass review (Apple's reviewers are humans and will spot it)
- Doesn't bypass any guideline (every rule here is a guideline restated mechanically)
- Doesn't replace careful design, testing, or honest description writing

## What it checks (70+ rules across 5 categories + custom)

| Category | Sample checks |
|---|---|
| **1. Safety** | fake/prank content, false medical claims, Support URL present |
| **2. Performance** | description completeness, audio/AI promises have implementation, Notes ≥200 chars, name length ≤30, **plist CFBundleDisplayName matches ASC name**, no competing-platform mentions, every `NSXxxUsageDescription` has matching framework code |
| **3. Business** | trial disclosure complete, "auto-renewing" CTA, price 36pt heavy, Restore button, Privacy + Terms links in paywall, EULA in description, no forced rating |
| **4. Design** | minimum functionality, ≥3 unique custom views (4.3 Spam protection), Sign in with Apple if 3rd-party login |
| **5. Legal** | Privacy Policy in app + ASC, account deletion UI if account, gambling=NONE for individuals, no banking/blood-pressure/casino keywords |
| **Custom (real rejection lessons)** | Detector/Meter apps must say "no external hardware", health keyword without HealthKit warning, subscription state ready, all locales have Support URL |

Full rule list in [audit.py](./audit.py) — every rule cites its Apple Guideline number.

## Quick start

```bash
pip install requests pyjwt cryptography

# Audit a single app:
python3 audit.py \
  --project ~/MyApp \
  --bundle-id com.example.myapp \
  --key-id ABC123XYZ \
  --issuer-id 12345-67890-... \
  --key-file ~/AuthKey_ABC123XYZ.p8

# Or via env vars:
export ASC_KEY_ID=ABC123XYZ
export ASC_ISSUER_ID=12345-67890-...
export ASC_KEY_FILE=~/AuthKey_ABC123XYZ.p8
python3 audit.py --project ~/MyApp --bundle-id com.example.myapp

# Code-only audit (no ASC fetch — many false negatives):
python3 audit.py --project ~/MyApp --no-asc

# Multiple apps from config file:
python3 audit.py --config apps.json

# CI-friendly: only print blockers, exit 1 on failure
python3 audit.py --config apps.json --quiet

# JSON output for scripting:
python3 audit.py --config apps.json --json
```

`apps.json` format:

```json
[
  {"name": "MyApp1", "project": "/path/to/MyApp1", "bundle_id": "com.example.app1"},
  {"name": "MyApp2", "project": "/path/to/MyApp2", "bundle_id": "com.example.app2"}
]
```

## Exit codes

| Code | Meaning |
|---|---|
| `0` | All checks pass — safe to submit |
| `1` | One or more **blockers** failed — do NOT submit |
| `2` | Config / credentials error |

Use exit code `1` to gate your CI submit step:

```bash
python3 audit.py --config apps.json && fastlane submit
```

## Get an ASC API key

App Store Connect → Users and Access → Keys → "+" → role **App Manager**. Save the `.p8` file (you can only download it once). The `Key ID` and `Issuer ID` show on the same page.

## How the rules were learned

Each rule maps to an actual rejection pattern observed in indie apps. A few generalized examples:

- **2.3.8 plist-name-matches-asc** — Renamed an app in App Store Connect after submitting the binary, forgot to update `CFBundleDisplayName`. Apple rejected on next submit (and the one after). Easy to forget, easy to grep.
- **2.5.1 NSHealthShareUsageDescription** — Declared `NSHealthShareUsageDescription` in `Info.plist` "just in case", never actually imported `HealthKit`. Apple rejected: a permission string with no matching framework code looks deceptive.
- **CUSTOM detector-no-hardware-disclaimer** — Magnetometer-based app described as "metal detector". Apple's reviewer assumed it needed an MFi accessory and asked for a hardware demo video. Adding "100% software, uses iPhone built-in magnetometer" to the first sentence resolved it.
- **3.1.2(c) auto-renewing-CTA** — Subscribe button said "Subscribe — $9.99/yr" instead of "Subscribe — $9.99/yr **auto-renewing**". One missing word in the CTA text is enough to trigger this rejection.

## Limitations

- Code grep is heuristic — false positives possible (e.g., the rule for `import HealthKit` won't catch dynamically-loaded frameworks).
- Some rules need the actual binary or screenshots to verify (e.g., 2.3.3 mockup screenshots, 2.4.5 unused background modes). Those rules are skipped.
- ASC API doesn't expose every metadata field (e.g., screenshot localization status). You still need a manual final review.
- Catches the things humans miss; doesn't replace careful design.

## Contributing

PRs welcome — especially new rules from your own rejection history. Format:

```python
add("CATEGORY.SECTION rule-id", "blocker|high|low",
    <bool: true if passing>,
    "human-readable failure message")
```

Add a comment citing the rejection that motivated the rule.

## Contact

Issues, PRs, or feedback: open a [GitHub issue](https://github.com/XJM-free/apple-presubmit-audit/issues) or email **jie.xiang.jm@gmail.com**.

## License

MIT. Use it, fork it, ship it.
