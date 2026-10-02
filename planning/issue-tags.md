# Issue Tags

Numeric GitHub issues and checkpoint filenames are normal for new work. The
eight historical four-letter aliases remain valid, immutable references; no
allocation or registry change is needed to start an issue.

The registry is `planning/issue-tags.json`. The optional compatibility utility can register a
tag with `python tools/issue_tags.py register <issue-number>`. The command
serializes concurrent allocation attempts and updates the registry itself.
The `check` subcommand remains in CI and validates registry integrity.

Tagged checkpoints use `Issue: TAG (#N)` matching the registry. Numeric references
use `#N`; PRs can use `Closes #N` without a tag.
