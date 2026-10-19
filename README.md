# ai-architecture-tools

CLI tools (`taskctl`, `questctl`, `rulectl`, `adrctl`, `specctl`) plus the
Claude Code Skills and Subagents built on them. See `architecture/VISION.md`.

## Install (Claude Code plugin)

```
/plugin marketplace add com-gft-tsbo-source/ai-architecture-tools
/plugin install architecture-tools@ai-architecture-tools
```

The CLIs then are on `PATH` inside Claude Code; requires `python3` (≥ 3.10,
standard library only). To use them in your own shell, add
`architecture/bin` of a checkout to your `PATH`.

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
