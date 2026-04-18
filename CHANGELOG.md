# Changelog

## [0.2.0] - 2026-04-18

### Added
- 7 new rules:
  - `1.3 kids-no-3rd-party-ads` — Kids Category restriction
  - `4.5.4 push-opt-in` — push notifications must call `requestAuthorization`
  - `5.1.1(iii) data-sharing-opt-in` — data sharing requires consent dialog
  - `5.2.1 content-ownership` — third-party content requires license
  - `5.4 vpn-justification` — NetworkExtension entitlement requires review notes
- `--no-asc` flag for code-only audit (skip ASC fetch)
- `--config` for batch auditing multiple apps
- Multi-language `3.1.1 trial-disclosure` (English + Chinese keywords)
- L10n.swift content included in `3.1.2(c)` checks

### Changed
- `1.4.1 medical-sensor-claim` — expanded keyword list (heart rate, pulse, blood oxygen, ECG, diagnose)
- `2.3.1(a) notes-required-items` — keyword groups instead of single keywords
- `2.3.8 plist-name-matches-asc` — accepts brand prefix variants ("MyApp" matches "MyApp - Tagline")
- `4.3 unique-views-anti-spam` — searches anywhere for `*View.swift`, not just `/Views/`
- README updated to honest 40+ rule claim

### Fixed
- Token refresh handling for batch audits running > 20 minutes
- False positive on `2.3.8` when ASC name has tagline
- False positive on `3.1.1` for paywalls using `then` instead of `after`

## [0.1.0] - 2026-04-18

### Added
- Initial open-source release
- 32 static rules + 11 dynamic permission checks
- ASC API integration for live metadata fetching
- CLI with `--project`, `--bundle-id`, `--config` options
- MIT License
