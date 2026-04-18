# Contributing

Thanks for considering a contribution! This project lives on real rejection stories — yours could save someone weeks of debugging.

## What to contribute

**New rules from your own rejection history.** Each rule should map to:
1. An actual rejection (yours or someone else's, with reference if public)
2. A specific Apple Guideline section (or be marked CUSTOM if it's an inferred pattern)
3. A grep-able heuristic that catches it

Examples of rule types we'd love:

- App Store Connect metadata checks
- Info.plist / entitlement validation
- Swift code → permission cross-checks
- Subscription / IAP compliance details
- New Apple guidelines as they're announced

## How to add a rule

1. Open `audit.py` and find the right category section (`1. SAFETY`, `2. PERFORMANCE`, etc.)
2. Add your rule using the `add()` helper:

   ```python
   add("CATEGORY.SECTION rule-id", "blocker|high|low",
       <bool: true if passing>,
       "human-readable failure message")
   ```

3. Add a one-line code comment explaining the rejection that motivated the rule
4. Update `CHANGELOG.md` under `## [Unreleased]`
5. Submit PR

## Severity levels

- **`blocker`** — Apple will reject. Submission MUST stop.
- **`high`** — Likely rejection or strong warning. Fix before submit.
- **`low`** — Soft issue. Fix when convenient.

## Code style

- Stay in pure Python (no third-party deps beyond `requests` + `pyjwt`)
- Pattern: regex / file glob / string check (avoid spawning subprocesses)
- Prefer false negatives over false positives — better to miss a rule than to block a legit submit

## Testing your rule

```bash
# Audit a real project
python3 audit.py --project ~/path/to/test-app --bundle-id com.example.test
```

Make sure your rule:
- Doesn't trigger on a known-good app
- Does trigger on a known-bad app
- Has a clear, actionable error message

## Reporting bugs

Open an issue with:
- Audit command you ran
- Output you got
- What you expected
- App project structure (don't share the whole project; just the relevant parts)

## License

By contributing, you agree your contribution is licensed under MIT.
