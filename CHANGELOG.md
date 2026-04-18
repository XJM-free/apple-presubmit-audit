# Changelog

## [0.3.0] - 2026-04-18

### Added
- **5.1.1(i) privacy-url-reachable**: HEAD request to verify Privacy URL returns 200. Apple's automated review fetches it; 404 = hard reject.
- **1.5 support-url-reachable**: same check for Support URL.

### Changed
- **3.2.2(x) no-forced-rating**: tightened patterns to detect actual gating code (`SKStoreReviewController.*if.*!rated`, `guard.*hasRated.*else`) instead of free-text matches like `rate.*before` which produced false positives on description text "review and adjust before publishing".
- **4.2 / 4.3 spam check**: combine multiple signals — unique View files + Service/Manager/ViewModel/Store/Repository/Client classes + files in `/Models/` + total non-boilerplate Swift files. Single-purpose utility apps with engine classes (e.g. magnetometer with `MagnetEngine.swift` + `RootView.swift`) no longer false-flagged.
- **5.1.1(i) privacy-in-app**: broadened pattern to catch `Privacy Policy` (with space), URL paths containing `/privacy`, `PrivacyPolicy` class names, and Chinese 隐私政策. Old kebab-only regex missed real shipping apps.

### Fixed
- False positive on `2.3.8 plist-name-matches-asc` when ASC name has a tagline (e.g., `MyApp` plist matches `MyApp - Tracker` ASC name)
- False positive on `4.3 unique-views` for apps using flat structure (no `/Views/` folder)
- False positive on `3.2.2(x)` from description text containing "before"

## [0.2.1] - 2026-04-18

### Added
- **2.3.6 age-rating-set** — verify `appStoreAgeRating` is set to FOUR_PLUS / NINE_PLUS / TWELVE_PLUS / SEVENTEEN_PLUS
- **2.3.6 appinfo-not-rejected** — flag when `appInfo.state == REJECTED` (means age rating data is stale; must re-save in ASC web UI). Found in the wild on a v1.0.2 resubmission rejected with "no rating assigned" despite `appStoreAgeRating: FOUR_PLUS` because the previous appInfo was stuck in REJECTED state.

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
