# ai-architecture-tools

CLI tools (`taskctl`, `questctl`, `rulectl`, `adrctl`, `specctl`) plus the
Claude Code Skills and Subagents built on them. See `architecture/VISION.md`.

## Install (Claude Code plugin)

```
/plugin marketplace add com-gft-tsbo-source/ai-architecture-tools
/plugin install architecture-tools@ai-architecture-tools
```

The Skills run the CLIs from the plugin directory; requires `python3`
(≥ 3.10, standard library only). To use the CLIs in your own shell, add
`architecture/cli` of a checkout to your `PATH`.

Claude Code on the web has no `/plugin` command and ignores plugins enabled
in a repository's `.claude/settings.json`; there the plugin is only
available through claude.ai organization settings, which require a private
or internal marketplace repository.

## Running taskctl-worker unattended

`taskctl-worker` works locally. Any remote action (push, triggering a
pipeline, changing a ticket, publishing, ...) waits until you approve it
in the Task's History. That rule is followed by the model, not enforced
mechanically, so for unattended runs (especially loop mode):

- run Claude Code's sandbox with outbound network writes restricted;
- don't give the session remote credentials the Tasklist doesn't need
  (no `gh` token, no JIRA or cloud credentials).

Approve a pending remote action by setting the Task back to in progress
with an approving message, e.g.
`taskctl --root <root> set-status <id> "~" --message "Approved: push to origin"`.

## Development

Develop in place under `architecture/`. Run the tests with
`python3 -m unittest discover -s architecture/scripts/tests -t architecture/scripts`,
try the working tree with `claude --plugin-dir ./architecture`, and check
the manifests with `claude plugin validate .`.
