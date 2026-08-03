# Anonymized production regression fixtures

These fixtures are hand-reduced from issues found while maintaining shipping
apps. They preserve only the detector-relevant shape and use generic type,
record, URL, and product names. They contain no App Store Connect payloads,
credentials, user content, or original application identifiers.

Each case has a `before` project that must fail its named advisory and an
`after` project that must pass it. `cases.json` records the evidence level:

- `observed-runtime-failure` means the failure was reproduced in a shipping
  app's maintenance history.
- `verified-production-fix` means the pattern failed a release audit, was
  removed from shipping-app source, and passed a later audit. It does not claim
  that App Review rejected the app or that a user encountered the failure.

These are regression tests for the audit detectors, not evidence that a static
match proves an App Review violation.
