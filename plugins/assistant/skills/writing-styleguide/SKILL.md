---
name: writing-styleguide
description: View and edit the personal-brand writing styleguide used by content skills (social-manager, twitter-manager, article-journalist). They read the styleguide files directly; this skill is for Shawn to edit them.
argument-hint: [view <channel> | edit <channel> | (blank for menu)]
allowed-tools: Read, Edit, Write, Glob
---

Styleguide files live in `plugins/assistant/skills/writing-styleguide/styleguide/`:
- general.md — cross-channel rules
- twitter.md — X-specific
- linkedin.md — LinkedIn-specific
- x-articles.md — long-form

## Arguments
$ARGUMENTS

## Routing
- `view <channel>` → Read and display (general | twitter | linkedin | x-articles | all)
- `edit <channel>` → Read file, ask what to change, apply
- blank → Menu:
  > 1. View styleguide
  > 2. Edit styleguide
  > 3. Add a voice sample (points to brand/voice-samples.md in jarvis repo)

## Editing rules
- Keep rules concrete and testable ("no em dashes" not "punctuate thoughtfully")
- If a rule comes from a specific misfired post, add a one-line example under it
- Don't delete existing rules silently; confirm first
