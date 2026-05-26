---
name: changelog-entry
description: Generate a new changelog entry for cibuildwheel based on all changes since the last tag. Use when updating the changelog or preparing a release.
---

# Generate Changelog Entry

Produce a new version section at the top of `docs/changelog.md` summarizing all changes since the last git tag.

## Steps

1. **Find the last tag** — run `git tag --sort=-version:refname | head -1` to get the most recent version tag.
2. **Gather changes** — run `git log <last-tag>..HEAD --oneline` and `git log <last-tag>..HEAD --format="%H %s"` to see all commits since that tag.
3. **Read each merge/commit** — for substantive commits, read the full message and any linked PRs to understand the change. Use `git log <last-tag>..HEAD --format="---%n%B"` for full messages. If a commit message is ambiguous, use `gh pr view <number>` to get richer context from GitHub.
4. **Classify and draft entries** — assign each change an emoji and write a one-line description following the style rules below. Combine related small PRs of the same type (bot dependency updates, dependabot CI action bumps, pre-commit autoupdates) into a single entry listing all PR numbers. Skip meta-changelog PRs (e.g., "Add missing CHANGELOG entries") — they don't describe user-facing changes. If a bot/dependency PR contains a substantive fix mixed in (e.g., a pip revert inside a dependency update), split it: mention the fix separately under its own category.
5. **Determine the new version number** — inspect commits for breaking changes or new features to decide patch/minor/major bump. Ask the user if unclear.
6. **Determine the date** — use today's date.
7. **Insert the new section** — add it at the top of `docs/changelog.md`, right after the `# Changelog` heading and a blank line, before any existing version sections.

## Style Rules

These are non-negotiable formatting conventions derived from the existing changelog.

### Version heading

```markdown
### v3.4.2
```

`###` heading, `v` prefix, full semver.

### Date line

```markdown
_14 May 2026_
```

Italic (underscore-wrapped), day without leading zero, full month name, 4-digit year. One blank line after the date.

### Entry format

```markdown
- <emoji> <Description> (#<PR number>)
```

- Each entry is a single bullet starting with `- `.
- Emoji immediately after the dash-space.
- Space between emoji and description text.
- PR number(s) in parens at end: `(#1234)` or `(#1234, #5678)`.
- No trailing period for single-sentence entries.
- Period at end of multi-sentence entries only.

### Emoji categories

Use exactly one emoji per entry, chosen by category:

| Emoji | Category | Used for |
|-------|----------|----------|
| 🌟 | Major feature | New platforms, significant new capabilities |
| ✨ | Feature | New features, additions, user-visible enhancements |
| 🐛 | Bug fix | Bug fixes |
| 🛠 | Maintenance | Dep updates, internal improvements, behavior tweaks |
| ⚠️ | Warning | Deprecations, breaking changes, dropped support |
| 📚 | Docs | Documentation changes |
| 💼 | Internal | Non-user-facing infra/tooling changes |
| 🧪 | Tests | Test changes |
| 🔐 | Security | Security-related changes (used in past changelogs) |

### Category disambiguation

When a change could fit multiple categories, use these tiebreakers:

- **CI/workflow fixes** → 💼 (not 🧪) — they fix infra, not test logic.
- **Test suite changes** → 🧪 — only for changes to the test code itself.
- **Diagnostic output changes** (e.g., printing more info during builds) → 🛠 (not 🐛) — they're improvements, not bug fixes.
- **A bug fix that also changes test code** → 🐛 — the user-facing fix takes priority; test changes are implicit.

### Writing style

- **Present tense**: "Adds", "Fixes", "Updates", not "Added", "Fixed".
- **Sentence case**: capitalize only the first word after the emoji.
- **Link option names to docs**: `[`option-name`](https://cibuildwheel.pypa.io/en/stable/options/#option-name)`. Option anchors match the option name — verify in `docs/options.md` by searching for `{: #option-name }`.
- Be specific about what changed and why, not just that something changed.

### Ordering

Within a version section, order entries by importance:

1. 🌟 entries first
2. ⚠️ entries next
3. ✨ entries
4. 🐛 entries
5. 🛠 entries
6. 📚 entries
7. 💼 entries
8. 🧪 entries last

### Multi-line entries

For complex features needing explanation, use an indented italic paragraph:

```markdown
- ✨ Short summary here. (#1234)

    _Longer explanation with details and caveats._ (#1234)
```

Adding a new Python beta version always has a specific longer explanation, check for a previous addition (like 3.14) for the note to use.

### Blank lines

- One blank line between version sections.
- No blank lines between bullets within a version.

## Validation

After inserting the new section:

1. Check that the new section follows all style rules above.
2. Verify PR numbers match actual PRs in the commit log.
3. Ensure no duplicate entries — multiple commits to the same PR should produce one entry.
4. Run a final review of the file to confirm formatting is consistent with surrounding entries.
