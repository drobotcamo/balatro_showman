# Issue Tags

New work items use a unique, immutable four-letter uppercase tag. GitHub issue
numbers remain the backing identifier and are included where GitHub needs a
numeric reference.

The registry is `planning/issue-tags.json`. Atomically allocate and register a
tag with `python tools/issue_tags.py register <issue-number>`. The command
serializes concurrent allocation attempts and updates the registry itself.
Numeric references and numeric thread filenames remain valid for historical
work.

New references use `TAG (#N)` in prose, `Issue: TAG (#N)` in thread files, and
both the tag and `Closes #N` in pull requests.
