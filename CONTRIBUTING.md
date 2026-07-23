# Contributing

Thanks for considering a contribution. New checks should be traceable to
current documentation, directly observed submission state, or a clearly
bounded heuristic.

## What to contribute

**New evidence-backed rules.** Each rule should map to:

1. An Apple requirement, a reproducible rejection, or a clearly labeled
   engineering heuristic
2. A specific Apple Guideline section when one exists (use `CUSTOM` otherwise)
3. A detector with both triggering and non-triggering fixtures

Examples of rule types we'd love:

- App Store Connect metadata checks
- Info.plist / entitlement validation
- Swift code → permission cross-checks
- Subscription / IAP compliance details
- New Apple guidelines as they're announced

## How to add a rule

1. Open `audit.py` and find the right category section (`1. SAFETY`, `2. PERFORMANCE`, etc.)
2. Add your rule using the helper that matches its evidence:

   ```python
   official("CATEGORY.SECTION rule-id", "blocker|high|low", passed, message)
   readiness("CUSTOM rule-id", "blocker|high|low", passed, message)
   advisory("CATEGORY.SECTION rule-id", "high|low", passed, message)
   ```

   Use `official` only for a directly testable limit or field in current Apple
   documentation. Use `readiness` for directly observed submission/catalog
   state. Regex, keyword, typography, file-count, and rejection-derived rules
   belong in `advisory`.

3. Link the current Apple source when claiming an official requirement, or add
   a one-line comment explaining the evidence and limits of an advisory
4. Update `CHANGELOG.md` under `## [Unreleased]`
5. Submit PR

## Severity levels

- **`blocker`** — Only for directly observed `OFFICIAL` or `READINESS` failures.
- **`high`** — Significant manual-review prompt.
- **`low`** — Lower-confidence or product-quality prompt.

An `ADVISORY` can never be a blocker and its message cannot use `must` or
`required` to turn a heuristic into a false Apple mandate. Runtime guards and
tests enforce this invariant.

## Code style

- Support Python 3.10 or newer.
- Keep third-party dependencies limited to `requirements.txt`.
- Pattern: regex / file glob / string check (avoid spawning subprocesses)
- Prefer false negatives over false positives.

## Testing your rule

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests -v
python3 -m py_compile audit.py
```

Make sure your rule:
- Doesn't trigger on a known-good fixture
- Does trigger on a known-bad fixture
- Has a clear, actionable error message

## Reporting bugs

Open an issue with:
- Audit command you ran
- Output you got
- What you expected
- App project structure (don't share the whole project; just the relevant parts)

## License

By contributing, you agree your contribution is licensed under MIT.
