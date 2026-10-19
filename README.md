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

## Development

Develop in place under `architecture/`. Run the tests with
`python3 -m unittest discover -s architecture/scripts/tests -t architecture/scripts`,
try the working tree with `claude --plugin-dir ./architecture`, and check
the manifests with `claude plugin validate .`.
