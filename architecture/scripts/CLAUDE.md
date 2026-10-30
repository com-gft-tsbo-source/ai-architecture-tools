# scripts/ — Python-CLI-Tools (taskctl.py, questctl.py, rulectl.py, adrctl.py, specctl.py)

Agentische CLI-Tools für Taskmanagement (`taskctl.py`), offene Fragen
(`questctl.py`), Code-Qualitäts-Regeln (`rulectl.py`), Architecture Decision
Records (`adrctl.py`) und Spezifikationsdokumente (`specctl.py`).

Maßgeblich sind die Design-Dokumente, nicht der Code:

- `architecture/docs/scripts/design.md` — allgemeines Objektmodell,
  CLI-Kontrakt, Locking, Index-Dateien (Basis für alle fünf Tools).
- `design-taskctl.md`, `design-questctl.md`, `design-rulectl.md`,
  `design-adrctl.md`, `design-specctl.md` — tool-spezifische Ergänzungen.
- `design-decisions.md` — Begründungen und Historie aller Änderungen
  (Amendments, mit Inhaltsverzeichnis). Diese Datei hier beschreibt nur den
  aktuellen Stand; Historie gehört dorthin.

## Tech-Stack

- Python 3.10, ausschließlich Standardbibliothek — keine externen Pakete.

## Implementierungsstand

Alle fünf Tools sind End-to-End implementiert, jeweils in Directory- und
Single-File-Mode.

- **Generisches Modell** (`lib/cliapp.py`, `lib/store.py`, `lib/toolspec.py`,
  `lib/objectfile.py`, `lib/singlefile.py`, `lib/index.py`, ...): genutzt
  von taskctl, questctl, rulectl, adrctl. Ein Tool ist im Wesentlichen ein
  `ToolSpec` (`lib/<tool>_spec.py` bzw. in `<tool>.py`).
- **specctl** hat eine eigene CLI und ein eigenes, leichtgewichtiges Format
  (`lib/spec_*.py`) — bewusst *nicht* `lib/cliapp.py`/`lib/store.py`, da
  dessen Objektformat und das getrennte Metagroup-/Objekt-Modell nicht
  passen. Wiederverwendet werden nur die generischen Bausteine (`locking`,
  `atomicio`, `clock`, `numbering`, `history`, `text`, `metagroup`,
  `abbrev`, `store.resolve_root`). Abweichungen im Detail:
  - Metagroup = Objekt (jede Section ist zugleich Pfadknoten); `move-to-<Ebene>`
    verschiebt den ganzen Teilbaum und leitet Object Types neu ab.
  - Directory-Mode: jede Section ist ein Verzeichnis mit `_content.md`;
    `_title.md` (Pflicht) und optional `_preamble.md` im Root; kein
    `.index.md`/`.index.json`.
  - Explizites `init`; jede andere schreibende Operation verlangt ein
    initialisiertes Dokument.
  - Kein `show-metagroups` (stattdessen `list`).
- **Gemeinsamer `--root`**: alle Tools lösen denselben Pfad über
  `store.resolve_root` zu ihrem eigenen `<name>.md`/`<name>` auf
  (`tasks`, `questions`, `rules`, `adrs` als Directory; `spec` als Single-File).
- **Drei Verb-Präfixe** (fest in `lib/cliapp.py`): `group-<Metagroup-Typ>`
  (Metagroup wechseln), `info-<Metainfo-Typ>` (Metainfo), `set-<Content-Block>`
  (Inhalt). `MetainfoSpec.choices` wird bei `add`/`info-*` durchgesetzt.
- **Variable Metagroup-Tiefe** (`ToolSpec.variable_depth`; taskctl 0–1,
  questctl 0–2): store-weit, aus dem Inhalt abgeleitet, vom ersten `add`
  bzw. `add-<tiefster Typ>` festgelegt.
- **`next`/`next-all`** melden "nichts zu tun" als `NoWorkAvailable` mit
  `reason` (bei `--json` als Feld) — u. a. `all_done`, `in_progress`,
  `all_answered`, `awaiting_interaction`.
- **Tool-übergreifende Verknüpfungen** (nie über Import des anderen CLI-Skripts):
  - specctl → adrctl: `lib/adr_lookup.py` prüft ADR-Existenz unter dem
    adrctl-Store-Lock, ohne einen fehlenden Store anzulegen.
  - adrctl → specctl: `spec-ref` wird über `cliapp.main`s
    `after_dispatch`-Hook (`lib/spec_link.py`) propagiert; nicht aus
    superseded/deprecated/rejected ADRs. Nicht transaktional: scheitert die
    Propagation, bleibt die ADR gespeichert, Exit 1.
  - rulectl → taskctl: `rulectl tasklist` (`lib/tasklist.py`) exportiert
    `active`-Regeln als Tasks (eine Phase je Language/Context/Category-Pfad,
    Task-ID = Regel-ID, `origin=rulectl:<rule-id>`). Re-Export aktualisiert
    nur geänderte Felder und setzt Status und `review` zurück.
- **Guards** (taskctl, Review-Guards auch questctl; `design-taskctl.md`,
  "Guards"): `lib/guards.py` (`GuardViolation`, `reason`
  `sequence_blocked`/`approval_required`, bei `--json` als JSON auf stdout),
  `ToolSpec.sequence_guard`/`metainfo_guard`, geprüft in `Store.set_status`/
  `add`/`set_metainfo` unter dem Lock; `[R]`→`[X]` gesperrt im gemeinsamen
  `validate_transition`. `--user-approved <text>` (generisch in
  `lib/cliapp.py` für `add`, `set-status`, `info-*`) hebt die Guards auf und
  landet als `USER-APPROVED: <text>` in der History; `--force` verlangt ihn
  bei allen Engine-Tools. Store-internes `force` umgeht alle Guards ohne
  Marker (nur `lib/tasklist.py`). taskctl-Metainfo `gate`
  (`sequential`|`none`): `rulectl tasklist` setzt `none`, damit
  `rulectl-checker` nach `[R]`/`[B]` weiterprüft; `next` überspringt solche
  Tasks in `[B]`/`[R]`/`[C]`.
- **questctl** `answer` schreibt `### Answer` per `Store.annotate_content`
  (History `T`); `ToolSpec.no_generic_setter` unterdrückt `set-answer`.
- Schreibvorgänge sind atomar (`.tmp` + `os.replace`); neue Datei vor dem
  Löschen der alten. Object-IDs werden bei `add` auf Eindeutigkeit geprüft.

## Offene Punkte

- Metagroup-Rename für taskctl/questctl/rulectl/adrctl — in `design.md`
  ("Metagroup Operations") nur als nicht implementiert erwähnt
  → `docs/backlog-features.md`, F1.
- ADR umbenennen: `adrctl` kann Name/Signatur eines ADR nicht ändern;
  nach einer Korrektur durch `specctl-adr-author` bleibt ein falscher Titel
  stehen.
- `resolve_root`: zeigt `--root` auf ein existierendes Verzeichnis eines
  *anderen* Tools (z. B. `adrctl --root ./project/tasks`), wird es als
  gemeinsames Verzeichnis behandelt (`./project/tasks/adrs/`) statt dessen
  Elternverzeichnis. Nicht entschieden.
- `adrctl add --set-status <status>` schreibt nur "Object created", keinen
  Status-Eintrag — nicht geprüft, ob das `design.md` ("Object Status")
  entspricht.
- specctl Object-Type-Breiten: `design-specctl.md` nennt 2 Buchstaben je
  Ebene, `lib/abbrev.py` nutzt für 1–3 Ebenen die allgemeinen Breiten
  (6 / 3+3 / 2+2+2). Nicht entschieden, ob Code oder Spec angepasst wird
  (ein Code-Fix änderte bestehende Object Types).
- Locking ist nur innerhalb eines Prozesses (Threads) getestet, nicht über
  echte Multi-Prozess-Konkurrenz.

## Geteilter Code

- Funktionalität, die mehrere Tools nutzen, gehört in ein eigenes Modul
  unter `architecture/scripts/lib/`, nicht mehrfach implementieren.
- Ein CLI-Skript importiert ein anderes CLI-Skript nie direkt (z. B. lädt
  `rulectl.py` nicht `taskctl.py` als Ganzes) — nur `lib/`-Module werden
  tool-übergreifend importiert (daher `lib/taskctl_spec.py`,
  `lib/adrctl_spec.py`).
- Neuer geteilter Code: erst prüfen, ob er wirklich generisch ist (kein
  Tool-Sonderfall), bevor er nach `lib/` wandert.

## Konsistenz zwischen den Tools

- Exit-Codes: `0` = ok, `1` = Fehler, `2` = Aufruffehler (argparse).
- Fehlermeldungen → stderr, reguläre Ausgabe → stdout.
- CLI-Struktur (Subcommands, `--json`-Flag, `--root` als einzelner,
  projektweit gemeinsamer Pfad, Positionsargumente ans Ende) einheitlich über
  alle fünf Tools halten, auch wenn ein Tool das jeweilige Feature (noch)
  nicht braucht — das gilt für specctl trotz eigener CLI-Implementierung.
  `tests/test_cli_contract.py` prüft diese Punkte für alle fünf Tools; ein
  neues Tool dort in `TOOLS` eintragen.
- Bei einer Änderung an einem Tool prüfen, ob dieselbe Änderung auch bei
  den anderen Sinn ergibt (z. B. neue CLI-Option, Statuslogik).

## Tests

```
python -m unittest discover -s architecture/scripts/tests -t architecture/scripts
```

Keine Testzahlen in Dokumenten festschreiben — sie veralten sofort.

## Distribution (Claude-Code-Plugin)

`architecture/` ist zugleich Plugin-Root des Plugins `architecture-tools`
(Begründung: `design-decisions.md`, "Amendments (2026-10-19, plugin
distribution)"). Daraus folgen Pflichten bei Änderungen:

- Neues CLI-Tool `scripts/<tool>.py` → Wrapper `architecture/bin/<tool>`
  (ausführbar, Muster der vorhandenen Wrapper) anlegen.
- Subagents (`architecture/agents/*.md`) und Skills
  (`architecture/skills/<name>/SKILL.md`) werden automatisch gefunden —
  `plugin.json` darf keinen `agents`-Key setzen (er ersetzt den
  Default-Scan).
- Skills rufen CLIs nur über den nackten Namen auf (`rulectl ...`), nie über
  einen Pfad in dieses Repository.
- `tests/test_plugin.py` prüft diese Punkte; zusätzlich vor einem Release
  `claude plugin validate .` (Repo-Root) ausführen.
- Jede Änderung unter `agents/`, `skills/` oder `bin/` braucht eine neue
  `version` in `plugin.json` — der CI-Job `plugin-version` lässt einen PR
  sonst scheitern.
- Lokal testen: `claude --plugin-dir ./architecture` (in diesem Repo ist das
  installierte Plugin per `.claude/settings.json` deaktiviert).

## CI

`.github/workflows/tests.yml` (GitHub-gehostete Runner, kostenlos für das
öffentliche Repo) führt bei jedem Push/PR beide Testsuites
(`architecture/scripts/tests`, `evals`) unter Python 3.10 (garantiertes
Minimum der Zielumgebungen) und 3.13 aus. Kein Laufzeit-Versionscheck in
`bin/` — ältere Pythons werden nicht unterstützt, Fehler dort sind akzeptiert.

## Struktur

```
architecture/scripts/
├── CLAUDE.md
├── ../bin/<tool>      # Plugin-Wrapper je CLI (auf PATH, wenn Plugin aktiv)
├── taskctl.py         # CLI: Taskliste (0/1 Ebenen: Phase)
├── questctl.py        # CLI: offene Fragen (0/1/2 Ebenen: Group/Subgroup)
├── rulectl.py         # CLI: Code-Qualitäts-Regeln (+ tasklist-Export)
├── adrctl.py          # CLI: ADRs (+ spec-ref-Propagation)
├── specctl.py         # CLI: Spezifikationsdokumente (eigene CLI)
├── tests/             # Unit-/Integrationstests, tests/lib/ je lib-Modul
└── lib/
    ├── locking, atomicio, clock, numbering, history, text, abbrev, metagroup
    │                      # geteilt zwischen allen fünf Tools
    ├── model, objectfile, singlefile, store, toolspec, index, render, cliapp, guards
    │                      # generisches Objektformat: taskctl/questctl/rulectl/adrctl
    ├── taskctl_spec, questctl_spec, adrctl_spec
    │                      # ToolSpecs; questctl nutzt taskctls Status-Maschine
    ├── adr_lookup         # specctl -> adrctl (eigenes Modul gegen Zirkelimport)
    ├── spec_link          # adrctl -> specctl
    ├── tasklist           # rulectl -> taskctl
    └── spec_model, spec_comment, spec_document, spec_store, spec_render
                           # specctl-eigenes Format (design-specctl.md)
```
