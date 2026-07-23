---
name: New rule suggestion
about: Suggest an evidence-backed audit rule
title: "[RULE] "
labels: rule
---

## Evidence

Link current Apple documentation or describe the directly observed submission
state. If the idea comes from a rejection, share only the relevant, redacted
portion of the message.

## Apple Guideline

Which guideline section does this map to? (For example, `2.3.8`, `5.1.1(ix)`,
or `CUSTOM` for an engineering heuristic.)

## How to detect

How could a script catch this before submit?
- Code grep pattern?
- ASC API field check?
- Info.plist key inspection?

## Evidence basis

- [ ] `OFFICIAL` — directly testable in current Apple documentation
- [ ] `READINESS` — directly observed submission or catalog state
- [ ] `ADVISORY` — heuristic or rejection-derived prompt for manual review

## Additional context

Anything else that helps explain the rule (links to documentation, forum posts,
or PR threads). Do not include credentials, unredacted bundle identifiers,
customer data, or proprietary source code.
