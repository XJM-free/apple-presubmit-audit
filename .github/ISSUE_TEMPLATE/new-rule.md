---
name: New rule suggestion
about: Suggest a new audit rule based on a real rejection
title: "[RULE] "
labels: rule
---

## The rejection

What rejection did you (or someone) get? Paste the exact Apple message if you have it.

## Apple Guideline

Which guideline section does this map to? (e.g., `2.3.8`, `5.1.1(ix)`, or `CUSTOM` if inferred)

## How to detect

How could a script catch this before submit?
- Code grep pattern?
- ASC API field check?
- Info.plist key inspection?

## Severity

- [ ] Blocker (Apple will reject)
- [ ] High (likely rejection)
- [ ] Low (soft warning)

## Additional context

Anything else that helps understand the rule (links to forum posts, PR threads, etc.)
