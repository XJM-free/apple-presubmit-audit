# Changelog

## [0.4.0] - 2026-04-23

### Added — 8 new rules from real production debugging

After a user reported "subscription unbuyable + iCloud sync broken" across 8 in-store apps, we traced 4 distinct silent failure modes that ASC marks "APPROVED" but Apple's StoreKit catalog cannot serve. All 8 are now BLOCKER checks:

- **CUSTOM sub-availability-{pid}** — Per-subscription `subscriptionAvailability` must have ≥1 territory. ASC creates sub at `state=APPROVED` but with 0 territories until you call `POST /v1/subscriptionAvailabilities` — Product is invisible to StoreKit. Found on 4 in-store apps.
- **CUSTOM sub-never-submitted-{pid}** — Subscription state `READY_TO_SUBMIT` means it was created but **never reviewed**. First-time IAPs MUST attach to an App version + go through unified review (cannot independently submit via API per Apple `feedback_subscription_iap_apple_limits` #5).
- **CUSTOM sub-group-loc-stuck** — Subscription **group** localizations stuck in `PREPARE_FOR_SUBMISSION`. Even if individual subs are APPROVED, group not LIVE → `https://amp-api-edge.apps.apple.com/.../in-app-purchasables` returns empty → StoreKit silently shows no products. Symptom: paywall says "loading..." or "no products available". Fix: DELETE the stuck group locs via API.
- **CUSTOM transaction-updates-listener** — `SubscriptionManager` must spawn a background `Task { for await in Transaction.updates }`. Without it: promo code redemption / auto-renewal / refund / Family Sharing changes are NOT propagated to `isPremium`. User taps "redeem code" → success on Apple side, but app UI never updates.
- **CUSTOM is-premium-bypass** — Direct writes to `dataStore.isPremium = true` (outside SubscriptionManager + outside demo mode) are a critical security bug: subscription expiry/refund will never revoke access. Found in `DivorceCalc/PaywallView.swift` where the paywall set `store.isPremium = true` after purchase, completely independent of the StoreKit entitlement check.
- **CUSTOM cloudkit-sync-fetch-then-modify** — Apps using CloudKit must fetch existing record before save: `if let existing = try? await db.record(for: id) { record = existing } else { record = CKRecord(recordType:, recordID:) }`. The naive `db.save(CKRecord(recordType:, recordID:))` works the FIRST time, but every subsequent sync fails with `CKError 11 "record to insert already exists"`. Affects: AquaLog, HomeManager, WeddingCalculator, RenoBudget, PetBook, DocGuard, CarCare, PocketTask.
- **CUSTOM cloudkit-prod-schema-deploy** — `cktool import-schema` ONLY deploys to `--environment DEVELOPMENT`. Production deploy must be done via CloudKit Dashboard "Deploy Schema Changes..." button. Without it: `CKError 1011 PartialFailure / Unknown record type` on every write. Apps with `com.apple.developer.icloud-container-environment = Production` (or App Store builds — production by default) fail silently.
- **CUSTOM paywall-benefit-{keyword}** — Extends earlier "Play along/Identify" cross-checks to common subscription claims: `iCloud`, `CSV`, `unlimited`, `notification`, `提醒`, `导出`. If paywall lists a feature with no implementation evidence in `**/*.swift`, flag it. Avoids "feature paywall is a lie" rejection AND user complaints.

### Internal
- `ASCClient.fetch_metadata` now returns:
  - `sub_states`: list of `(productId, state)` tuples
  - `sub_territories`: dict `{productId: territory_count}`
  - `sub_group_loc_states`: list of `(group_id, locale, state)` tuples

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
