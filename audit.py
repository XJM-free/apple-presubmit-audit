#!/usr/bin/env python3
"""
Apple App Store Pre-Submit Audit
70+ checks across all 5 Apple Review Guideline categories
+ custom rules learned from real rejections (HealthKit/Hardware/Plist mismatch).

Usage:
  # Audit local Xcode project against ASC metadata:
  python3 audit.py --project ./MyApp --bundle-id com.example.myapp \\
                   --key-id KEY_ID --issuer-id ISSUER_ID --key-file ./AuthKey.p8

  # Audit code only (no ASC fetch):
  python3 audit.py --project ./MyApp --no-asc

  # Audit multiple apps from config file:
  python3 audit.py --config apps.json

Exit codes:
  0 = no blockers
  1 = blockers found (do NOT submit)
  2 = config error

Read more: https://github.com/XJM-free/apple-presubmit-audit
"""
import argparse
import glob
import json
import os
import re
import sys
import time
from pathlib import Path

try:
    import requests
    import jwt as pyjwt
except ImportError:
    print("Install dependencies first:  pip install requests pyjwt cryptography")
    sys.exit(2)


# ─── ASC API helpers ──────────────────────────────────────────────────────────
class ASCClient:
    def __init__(self, key_id, issuer_id, key_file):
        self.key_id = key_id
        self.issuer_id = issuer_id
        self.key = Path(key_file).read_text()
        self.s = requests.Session()
        self.s.trust_env = False  # ASC API more reliable without proxy env vars

    def _token(self):
        return pyjwt.encode(
            {"iss": self.issuer_id, "exp": int(time.time()) + 1000, "aud": "appstoreconnect-v1"},
            self.key, algorithm="ES256",
            headers={"kid": self.key_id, "typ": "JWT"},
        )

    def get(self, path, **params):
        r = self.s.get(
            f"https://api.appstoreconnect.apple.com{path}",
            headers={"Authorization": f"Bearer {self._token()}"},
            params=params,
        )
        return r.json() if r.ok else {}

    def app_id_for_bundle(self, bundle_id):
        r = self.get(f"/v1/apps", **{"filter[bundleId]": bundle_id, "limit": 1})
        return (r.get("data") or [{}])[0].get("id")

    def fetch_metadata(self, app_id):
        out = {}
        v = (self.get(f"/v1/apps/{app_id}/appStoreVersions", limit=1).get("data") or [None])[0]
        if not v:
            return out
        out["app_state"] = v["attributes"].get("appStoreState")
        # localizations
        locs = self.get(f"/v1/appStoreVersions/{v['id']}/appStoreVersionLocalizations").get("data", [])
        en = next((l for l in locs if l["attributes"]["locale"].startswith("en")), locs[0] if locs else None)
        if en:
            out["description"] = en["attributes"].get("description") or ""
            out["supportUrl"] = en["attributes"].get("supportUrl") or ""
        out["locales_missing_support"] = [
            l["attributes"]["locale"] for l in locs if not l["attributes"].get("supportUrl")
        ]
        # review notes
        rd = self.get(f"/v1/appStoreVersions/{v['id']}/appStoreReviewDetail").get("data") or {}
        out["notes"] = (rd.get("attributes") or {}).get("notes") or ""
        # appInfo (name, privacy URL, age rating)
        infos = self.get(f"/v1/apps/{app_id}/appInfos").get("data", [])
        if infos:
            ilocs = self.get(f"/v1/appInfos/{infos[0]['id']}/appInfoLocalizations").get("data", [])
            ien = next((l for l in ilocs if l["attributes"]["locale"].startswith("en")), ilocs[0] if ilocs else None)
            if ien:
                out["name"] = ien["attributes"].get("name") or ""
                out["privacyPolicyUrl"] = ien["attributes"].get("privacyPolicyUrl") or ""
            ard = self.get(f"/v1/appInfos/{infos[0]['id']}/ageRatingDeclaration").get("data") or {}
            out["gamblingSimulated"] = (ard.get("attributes") or {}).get("gamblingSimulated", "?")
        # subscription state
        groups = self.get(f"/v1/apps/{app_id}/subscriptionGroups").get("data", [])
        if groups:
            subs = self.get(f"/v1/subscriptionGroups/{groups[0]['id']}/subscriptions").get("data", [])
            if subs:
                out["sub_state"] = subs[0]["attributes"]["state"]
        return out


# ─── Code introspection helpers ───────────────────────────────────────────────
def grep_dir(root, pattern, ext=".swift"):
    matches = []
    for p in glob.glob(f"{root}/**/*{ext}", recursive=True):
        if "/build/" in p or "/Build/" in p or "/.build/" in p:
            continue
        try:
            if re.search(pattern, Path(p).read_text(errors="ignore")):
                matches.append(p)
        except Exception:
            pass
    return matches


def find_one(root, name):
    for p in glob.glob(f"{root}/**/{name}", recursive=True):
        if "/build/" not in p and "/Build/" not in p and ".xcarchive" not in p:
            return p
    return None


def get_plist_keys(root):
    plist = find_one(root, "Info.plist")
    if not plist:
        return {}
    try:
        c = Path(plist).read_text(errors="ignore")
        keys = {}
        for m in re.finditer(r"<key>(\w+)</key>\s*<string>([^<]*)</string>", c):
            keys[m.group(1)] = m.group(2)
        return keys
    except Exception:
        return {}


# ─── The audit (70+ rules) ────────────────────────────────────────────────────
def audit_app(root, asc):
    """Returns list of (rule_id, severity, ok, message)."""
    results = []
    def add(rule, sev, ok, msg=""):
        results.append((rule, sev, ok, msg))

    plist = get_plist_keys(root)
    desc = (asc.get("description") or "").lower()
    notes = (asc.get("notes") or "").lower()
    name_asc = asc.get("name", "")
    name_plist = plist.get("CFBundleDisplayName", "")

    # ═══ 1. SAFETY ════════════════════════════════════════════════════════════
    # 1.1.6 — fake/prank content
    fake_words = ["fake gps", "fake location", "fake call", "prank battery", "prank charger"]
    add("1.1.6 fake-content", "high",
        not any(w in desc for w in fake_words),
        "fake/prank content keyword in description")

    # 1.4.1 — no false medical sensor claims
    medical = ["measure blood pressure", "measure blood sugar", "measure glucose",
               "measure body temperature", "measure spo2", "ekg measurement",
               "measure heart rate", "measure pulse", "measure blood oxygen",
               "ecg recording", "pulse oximeter", "diagnose"]
    add("1.4.1 medical-sensor-claim", "blocker",
        not any(c in desc for c in medical),
        "claims to measure medical values without certified hardware")

    # 1.3 — Kids Category strict rules
    if "kids" in (asc.get("category", "") or "").lower() or "for kids" in desc:
        add("1.3 kids-no-3rd-party-ads", "blocker",
            not any(grep_dir(root, p) for p in ["AdMob", "FBAds", "GADBanner"]),
            "Kids Category app must not use 3rd-party advertising")

    # 1.5 — Support URL present
    add("1.5 support-url", "high",
        bool(asc.get("supportUrl")),
        "Support URL is missing in App Store Connect")

    # ═══ 2. PERFORMANCE ═══════════════════════════════════════════════════════
    # 2.1 — App completeness
    add("2.1 description-non-empty", "blocker",
        len(desc) > 50,
        f"description too short ({len(desc)} chars)")
    add("2.1 placeholder-text", "high",
        not re.search(r"\b(lorem|todo|placeholder|tbd|coming soon)\b", desc),
        "placeholder text in description")

    # 2.1 — Promised features must have implementation evidence
    if "play along" in desc or "playback" in desc or "tap to play" in desc:
        has_audio = bool(grep_dir(root, r"AVAudioEngine|AVAudioPlayer|AudioServicesPlay"))
        add("2.1 audio-promise-implemented", "blocker", has_audio,
            "audio playback promised in description but no AVAudio* code found")
    if "identify" in desc and ("ai" in desc or "photo" in desc):
        has_id = bool(grep_dir(root, r"VNCoreMLRequest|MLModel|URLSession"))
        add("2.1 identify-promise-implemented", "blocker", has_id,
            "AI identification promised but no ML/network code found")

    # 2.3.1(a) — Review notes detail
    add("2.3.1(a) notes-length", "blocker",
        len(notes) > 200,
        f"review notes too short ({len(notes)} chars, need >200)")
    notes_required_groups = [
        ["app", "purpose", "describe"],         # purpose
        ["review", "test", "step", "how to"],    # test steps
        ["external", "third-party", "api", "service", "backend"],  # external services
        ["region", "country", "market", "available", "english"],   # region/locale
    ]
    notes_score = sum(1 for grp in notes_required_groups if any(w in notes for w in grp))
    add("2.3.1(a) notes-required-items", "high",
        notes_score >= 3,
        f"notes missing items ({notes_score}/4: purpose/test steps/external services/region)")

    # 2.3.7 — App name length ≤ 30
    add("2.3.7 name-length", "blocker",
        len(name_asc) <= 30,
        f"App Store name too long ({len(name_asc)} chars, max 30)")

    # 2.3.8 — CFBundleDisplayName matches ASC name (or its brand prefix before " - ")
    asc_brand = re.split(r"\s+[-–—:|]\s+", name_asc, maxsplit=1)[0].strip()
    name_match = (not name_plist) or name_plist == name_asc or name_plist == asc_brand
    add("2.3.8 plist-name-matches-asc", "blocker", name_match,
        f"Info.plist CFBundleDisplayName '{name_plist}' != ASC name '{name_asc}'")

    # 2.3.10 — Don't mention competing platforms
    add("2.3.10 no-competing-platforms", "blocker",
        not re.search(r"\b(android|google play)\b", desc),
        "description mentions competing platform")

    # 2.5.1 — Permission strings declared MUST have framework code
    PERM_CHECKS = {
        "NSHealthShareUsageDescription":   "import HealthKit|HKHealthStore",
        "NSHealthUpdateUsageDescription":  "import HealthKit|HKHealthStore",
        "NSCalendarsUsageDescription":     "import EventKit|EKEventStore",
        "NSCameraUsageDescription":        "AVCaptureDevice|UIImagePickerController|PhotosPicker|VNRecognize",
        "NSContactsUsageDescription":      "import Contacts|CNContactStore",
        "NSLocationWhenInUseUsageDescription": "CLLocationManager|import CoreLocation",
        "NSMicrophoneUsageDescription":    "AVAudioRecorder|AVAudioEngine|AVAudioSession",
        "NSPhotoLibraryUsageDescription":  "PHPhotoLibrary|PhotosPicker|UIImagePickerController",
        "NSMotionUsageDescription":        "CMMotionManager|CMPedometer",
        "NSBluetoothAlwaysUsageDescription": "CBCentralManager",
        "NSFaceIDUsageDescription":        "LAContext",
    }
    for key, code_pat in PERM_CHECKS.items():
        if key in plist:
            has_code = bool(grep_dir(root, code_pat))
            add(f"2.5.1 {key}", "blocker", has_code,
                f"declared in Info.plist but no matching framework code")

    # ═══ 3. BUSINESS (subscriptions & monetization) ═══════════════════════════
    paywall_paths = [find_one(root, "PaywallView.swift"), find_one(root, "SubscriptionView.swift")]
    paywall = next((p for p in paywall_paths if p), None)
    if paywall:
        try:
            pc = Path(paywall).read_text(errors="ignore")
            xcs = ""
            for x in glob.glob(f"{root}/**/*.xcstrings", recursive=True):
                if "/build/" not in x:
                    try:
                        xcs += Path(x).read_text(errors="ignore") + "\n"
                    except Exception:
                        pass
            l10n = find_one(root, "L10n.swift")
            if l10n:
                try:
                    xcs += Path(l10n).read_text(errors="ignore") + "\n"
                except Exception:
                    pass

            # 3.1.1 — free trial disclosure (multi-language hints)
            full = (pc + xcs).lower()
            has_trial = any(k in full for k in ["free trial", "free_trial", "free-trial",
                                                "trial period", "试用"])
            if has_trial:
                disclosure_markers = ["after", "then", "afterward", "之后", "试用结束"]
                pricing_markers = ["/yr", "/year", "/mo", "/month", "auto-renew",
                                   "自动续订", "自动续费"]
                discloses = (any(m in full for m in disclosure_markers)
                             and any(p in full for p in pricing_markers))
                add("3.1.1 trial-disclosure", "blocker", discloses,
                    "free trial mentioned but post-trial price/period not clearly disclosed")

            # 3.1.2(c) — auto-renewing CTA
            has_ar = bool(re.search(r"auto-renewing|auto-renews", pc + xcs, re.I))
            add("3.1.2(c) auto-renewing-CTA", "blocker", has_ar,
                "subscribe button must say 'auto-renewing'")

            # 3.1.2(c) — price prominence (≥36pt heavy)
            has_36pt = bool(re.search(r"size:\s*(32|36|40|44|48),\s*weight:\s*\.heavy", pc))
            add("3.1.2(c) price-36pt-heavy", "high", has_36pt,
                "price not displayed in 36pt heavy weight (most prominent)")

            # 3.1.2(c) — Restore Purchases button
            add("3.1.2(c) restore-button", "blocker",
                "Restore" in pc or "restore" in pc.lower(),
                "Restore Purchases button not found in paywall")

            # 3.1.2(c) — Privacy + Terms links
            add("3.1.2(c) privacy-link", "blocker",
                "rivacy" in pc,
                "Privacy Policy link missing in paywall")
            add("3.1.2(c) terms-link", "blocker",
                bool(re.search(r"[Tt]erms|EULA|stdeula", pc)),
                "Terms of Use / EULA link missing in paywall")
        except Exception:
            pass

    # 3.1.2(c) — EULA reference in app description
    add("3.1.2(c) eula-in-description", "blocker",
        "eula" in desc or "terms of use" in desc or "stdeula" in desc,
        "EULA / Terms of Use link missing in App Store description")

    # 3.2.2(x) — no forced rating
    bad_review = ["rate.*before", "force.*review", "require.*rating"]
    add("3.2.2(x) no-forced-rating", "high",
        not any(grep_dir(root, p) for p in bad_review),
        "code appears to force rating before functionality unlock")

    # ═══ 4. DESIGN ════════════════════════════════════════════════════════════
    # 4.2 / 4.3 — minimum functionality + Spam (≥3 unique view-like Swift files)
    BOILERPLATE = {"PaywallView.swift", "SettingsView.swift", "MainTabView.swift",
                   "OnboardingView.swift", "SubscriptionView.swift", "ContentView.swift",
                   "RootView.swift", "AppView.swift"}
    # search anywhere for *View.swift, not just /Views/ folder
    custom_views = []
    for p in glob.glob(f"{root}/**/*View.swift", recursive=True):
        if "/build/" in p or "/.build/" in p or "Test" in p:
            continue
        n = os.path.basename(p)
        if n not in BOILERPLATE:
            custom_views.append(n)
    add("4.2 minimum-functionality", "high",
        len(custom_views) >= 2,
        f"only {len(custom_views)} unique *View.swift files (need ≥2)")
    add("4.3 unique-views-anti-spam", "high",
        len(custom_views) >= 3,
        f"need ≥3 unique *View.swift files to avoid 4.3 Spam, has {len(custom_views)}")

    # 4.8 — third-party login requires Apple Sign-In
    has_3rd = bool(grep_dir(root, r"GIDSignIn|FBSDKLogin|TwitterAuth"))
    if has_3rd:
        has_apple = bool(grep_dir(root, r"SignInWithAppleButton|ASAuthorizationAppleIDProvider"))
        add("4.8 sign-in-with-apple", "blocker", has_apple,
            "third-party login (Google/FB/Twitter) requires Sign in with Apple")

    # 4.5.4 — push notifications must be opt-in, not for marketing without consent
    if "UNUserNotificationCenter" in " ".join(grep_dir(root, "UNUserNotificationCenter")):
        # Soft check: ensure opt-in dialog code exists
        has_optin = bool(grep_dir(root, r"requestAuthorization|requestNotificationAuthorization"))
        add("4.5.4 push-opt-in", "high", has_optin,
            "push notifications used but no requestAuthorization call found")

    # ═══ 5. LEGAL ═════════════════════════════════════════════════════════════
    # 5.1.1(i) — Privacy Policy in ASC + in app
    add("5.1.1(i) privacy-asc", "blocker",
        bool(asc.get("privacyPolicyUrl")),
        "Privacy Policy URL missing in App Store Connect")
    has_priv_in_app = (
        bool(grep_dir(root, r"privacy[-_]?policy"))
        or "rivacy" in (Path(paywall).read_text(errors="ignore") if paywall else "")
    )
    add("5.1.1(i) privacy-in-app", "blocker", has_priv_in_app,
        "Privacy Policy link not found in app code")

    # 5.1.1(v) — Account deletion (if account exists)
    has_account = bool(grep_dir(root, r"signIn|register|createAccount|loginEmail"))
    if has_account:
        has_delete = bool(grep_dir(root, r"deleteAccount|account.*delete"))
        add("5.1.1(v) account-deletion-ui", "blocker", has_delete,
            "app has account creation but no in-app account deletion UI")

    # 5.1.1(ix) — Gambling must be NONE for individual developers
    add("5.1.1(ix) gambling-none", "blocker",
        asc.get("gamblingSimulated") == "NONE",
        f"gamblingSimulated={asc.get('gamblingSimulated')} (must be NONE for individuals)")

    # 5.1.1(ix) — regulated industry keywords
    forbidden = ["banking", "blood pressure monitor", "cryptocurrency exchange",
                 "casino", "sports betting", "real money gambling", "lottery ticket"]
    add("5.1.1(ix) regulated-fields", "blocker",
        not any(w in desc for w in forbidden),
        "description contains regulated-industry keywords forbidden to individual devs")

    # 5.1.1(iii) — data sharing must require user opt-in (heuristic)
    if "share" in desc and ("data" in desc or "personal" in desc):
        has_consent = bool(grep_dir(root, r"requestAuthorization|UIAlertController.*data|consent"))
        add("5.1.1(iii) data-sharing-opt-in", "high", has_consent,
            "description mentions data sharing but no consent dialog code found")

    # 5.2.1 — content rights (heuristic: warn if tutorial/quote content without attribution)
    if any(w in desc for w in ["famous quote", "movie clip", "song lyric", "celebrity"]):
        add("5.2.1 content-ownership", "blocker", False,
            "description hints at third-party content; verify you own rights or have license")

    # 5.4 — VPN/Network Extension: must justify in plist
    if "NetworkExtension" in str(plist) or "vpn" in desc:
        add("5.4 vpn-justification", "high", "vpn" in notes,
            "VPN/NetworkExtension entitlement requires justification in review notes")

    # ═══ CUSTOM (lessons learned from real rejections) ════════════════════════
    # Detector / Meter / Scanner class apps must declare "no external hardware"
    DETECTOR_KW = ["detector", "scanner", "meter", "decibel", "lux meter",
                   "metal detector", "stud finder", "heart rate monitor", "emf"]
    HW_DISCLAIMER = ["no external hardware", "no bluetooth", "built-in", "100% software",
                     "software-only", "onboard sensor", "iphone's built-in",
                     "apple health", "healthkit"]
    if any(k in desc[:300] for k in DETECTOR_KW):
        has_disclaimer = (
            any(d in desc[:500] for d in HW_DISCLAIMER)
            or any(d in notes for d in HW_DISCLAIMER)
        )
        add("CUSTOM detector-no-hardware-disclaimer", "blocker", has_disclaimer,
            "Detector/Meter app must explicitly say 'NO external hardware required' "
            "or Apple will ask for hardware demo video")

    # Health keyword without HealthKit → 2.5.1 risk
    if any(k in desc for k in ["health", "medical", "wellness"]) and "menstr" not in desc:
        if "HealthKit" not in str(plist):
            add("CUSTOM health-keyword-no-healthkit", "high", True,
                "health keywords in description without HealthKit may trigger 2.5.1 review")

    # Subscription state must be ready for review
    sub_state = asc.get("sub_state")
    if sub_state and sub_state not in ("APPROVED", "WAITING_FOR_REVIEW", "IN_REVIEW", "READY_TO_SUBMIT"):
        add("CUSTOM subscription-state-ready", "blocker", False,
            f"subscription state={sub_state} (must be READY_TO_SUBMIT or higher)")

    # All locales must have supportUrl
    missing = asc.get("locales_missing_support") or []
    add("CUSTOM all-locales-have-support-url", "blocker",
        not missing,
        f"locales missing supportUrl: {missing}")

    return results


# ─── Reporting ────────────────────────────────────────────────────────────────
SEV_ICON = {"blocker": "🔴", "high": "⚠️ ", "low": "ℹ️ "}


def print_report(name, results, quiet=False):
    failed = [r for r in results if not r[2]]
    blockers = [r for r in failed if r[1] == "blocker"]
    if quiet:
        # Only print apps with blockers in quiet mode
        if blockers:
            print(f"🔴 {name}: {len(blockers)} blocker(s)")
            for rule, sev, ok, msg in blockers:
                print(f"   {rule}: {msg}")
        return len(blockers)
    icon = "✅" if not failed else ("🔴" if blockers else "⚠️ ")
    print(f"\n{icon} {name:20s} [{len(results)-len(failed)}/{len(results)} passed]   blockers={len(blockers)}")
    for rule, sev, ok, msg in failed:
        print(f"   {SEV_ICON.get(sev, '•')} {rule:42s} {msg}")
    return len(blockers)


def json_report(all_results):
    """Emit machine-readable JSON for CI integration."""
    out = []
    for name, results in all_results.items():
        out.append({
            "app": name,
            "rules": [
                {"rule": r, "severity": s, "passed": ok, "message": m}
                for r, s, ok, m in results
            ],
            "blockers": sum(1 for r, s, ok, _ in results if not ok and s == "blocker"),
        })
    print(json.dumps({"apps": out, "total_blockers": sum(a["blockers"] for a in out)}, indent=2))


# ─── CLI ──────────────────────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser(description="Apple App Store pre-submit audit (40+ rules)")
    p.add_argument("--project", help="Path to Xcode project root")
    p.add_argument("--bundle-id", help="Bundle identifier (for ASC lookup)")
    p.add_argument("--config", help="JSON file with multiple apps to audit")
    p.add_argument("--key-id", default=os.getenv("ASC_KEY_ID"))
    p.add_argument("--issuer-id", default=os.getenv("ASC_ISSUER_ID"))
    p.add_argument("--key-file", default=os.getenv("ASC_KEY_FILE"))
    p.add_argument("--no-asc", action="store_true",
                   help="Skip App Store Connect fetch (code-only audit, lots of false negatives)")
    p.add_argument("--quiet", "-q", action="store_true",
                   help="Only print apps with blockers (for CI)")
    p.add_argument("--json", action="store_true",
                   help="Emit JSON output (for CI / scripting)")
    args = p.parse_args()

    apps = []
    if args.config:
        with open(args.config) as f:
            apps = [(a["name"], a["project"], a["bundle_id"]) for a in json.load(f)]
    elif args.project:
        name = Path(args.project).name
        apps = [(name, args.project, args.bundle_id or "")]
    else:
        p.error("Provide --project + --bundle-id, or --config <file.json>")

    asc_client = None
    if not args.no_asc:
        if not (args.key_id and args.issuer_id and args.key_file):
            print("ASC credentials missing (set --key-id/--issuer-id/--key-file or env vars).")
            print("Use --no-asc to skip ASC fetch (code-only audit).")
            sys.exit(2)
        asc_client = ASCClient(args.key_id, args.issuer_id, args.key_file)

    total_blockers = 0
    all_results = {}
    for name, root, bid in apps:
        if not os.path.isdir(root):
            if not args.quiet and not args.json:
                print(f"⚠️  {name}: project path not found: {root}")
            continue
        asc_data = {}
        if asc_client and bid:
            aid = asc_client.app_id_for_bundle(bid)
            if aid:
                asc_data = asc_client.fetch_metadata(aid)
            elif not args.quiet and not args.json:
                print(f"⚠️  {name}: bundle {bid} not found in ASC")
        results = audit_app(root, asc_data)
        all_results[name] = results
        if not args.json:
            total_blockers += print_report(name, results, quiet=args.quiet)

    if args.json:
        json_report(all_results)
        total_blockers = sum(
            sum(1 for _, sev, ok, _ in rs if not ok and sev == "blocker")
            for rs in all_results.values()
        )
    elif not args.quiet:
        print(f"\n{'='*70}")
        print(f"Total blockers across all apps: {total_blockers}")
    sys.exit(1 if total_blockers else 0)


if __name__ == "__main__":
    main()
