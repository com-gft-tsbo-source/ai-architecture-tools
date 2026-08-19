# scripts/ — Python-CLI-Tools (taskctl.py, rulectl.py, adrctl.py, specctl.py)

Agentische CLI-Tools für Taskmanagement (`taskctl.py`), Code-Qualitäts-Regeln
(`rulectl.py`), Architecture Decision Records (`adrctl.py`) und
Spezifikationsdokumente (`specctl.py`). Objektmodell, Dateiformat und
CLI-Kontrakt sind spezifiziert in:

- `architecture/docs/scripts/design.md` — allgemeines Objektmodell, CLI-Kontrakt,
  Locking, Index-Dateien (gilt für alle vier Tools als Basis; specctl weicht an
  mehreren dort explizit vermerkten Stellen ab).
- `architecture/docs/scripts/design-taskctl.md`, `design-rulectl.md`,
  `design-adrctl.md`, `design-specctl.md` — tool-spezifische Ergänzungen.

Bei Widersprüchen zwischen vorhandenem Code und diesen Dokumenten sind die
Design-Dokumente maßgeblich — nicht der Code.

## Aktueller Implementierungsstand

Kernmodell, Locking, Index-Dateien, Reorder, Multi-Root Read-Only-Merge sowie
`taskctl.py`, `rulectl.py`, `adrctl.py` sind implementiert und laufen End-to-End
— sowohl Directory-Mode als auch Single-File-Mode. `reindex` baut `.index.json`
neu und erkennt/behebt Inkonsistenzen aktiv (verwaiste `.tmp`-Dateien werden
entfernt, doppelte Nummern innerhalb einer Metagroup werden gemeldet).
`add-<metagroup-type>` vergibt die Sortnummer automatisch (`max+1`), wenn keine
explizit angegeben wird; `add --<metagroup-type>` akzeptiert zur Referenz auf
existierende Pfade pro Segment Nummer, Name oder `Nummer-Name` (spezifiziert in
`design.md`, CLI Contract; Begründung in `design-decisions.md`, Abschnitt
"Amendments").

`specctl.py` ist implementiert (Add je Ebene, Status inkl. ADR-Pflicht ab
`stable`, `set-adr`, `set-description`, `rename`, `reorder`, `show`, `list`,
`history`, `render`) — **sowohl Single-File- als auch Directory-Mode**
(`design-specctl.md`, "Object Format"). Es nutzt bewusst *nicht*
`lib/cliapp.py` und `lib/objectfile.py`/`lib/singlefile.py`/`lib/store.py`:
deren generisches Objektformat (Signature-Heading, `## Meta`-Bulletliste,
`> `-Zitatblöcke, Metagroup getrennt vom Objekt) passt nicht zu specctls
leichtgewichtigem Format und kollabiertem Metagroup-=-Objekt-Modell —
eigene Module `lib/spec_model.py`, `lib/spec_comment.py`,
`lib/spec_document.py`, `lib/spec_store.py`, `lib/spec_render.py`.
Wiederverwendet werden die tatsächlich generischen Bausteine:
`lib/locking.py`, `lib/atomicio.py`, `lib/clock.py`, `lib/numbering.py`,
`lib/history.py`, `lib/text.py` (`escape_signature_text`, `slugify` —
Letzteres seit specctl auch von `lib/store.py` genutzt statt eines eigenen
privaten Duplikats), `lib/metagroup.py` (`resolve_segment`,
`assign_leaf_name`) sowie `lib/store.py`s `detect_mode` (Datei- vs.
Directory-Erkennung anhand Dateiendung) und `lib/abbrev.py`, das dafür um
die 4-/5-Ebenen-Breiten aus `design-specctl.md` ("Object Type")
generalisiert wurde, ohne das Verhalten für die anderen drei Tools zu
ändern (deren Breiten summierten schon vorher zu 6).

specctls Directory-Mode weicht vom allgemeinen Modell ab: **jede Section ist
ein Verzeichnis** (`<nr>-<type>-<id>-<slug>/`, nicht nur Blätter), mit einer
`_content.md` für Heading+Kommentar+Description; kein `.index.md`/
`.index.json` (das Object Type steckt bereits pro Section in `_content.md`,
ein Index wäre reine Duplikation); die Dokument-Präambel liegt optional in
`_preamble.md` im Wurzelverzeichnis. Ein Schreibvorgang leert und baut den
gesamten Baum aus der In-Memory-Liste neu auf (wie das komplette Neu-Schreiben
der Datei im Single-File-Mode) — nicht atomar über mehrere Dateien hinweg,
dieselbe bereits im allgemeinen Modell akzeptierte Einschränkung bei einer
unterbrochenen Reorder-Kaskade. Beide Modi konvertieren in dieselbe flache,
präorder `list[SpecSection]`-Repräsentation, sodass sämtliche CRUD-Methoden
(`add`, `set_status`, `rename`, `reorder`, ...) modusunabhängig bleiben —
nur `_read`/`_write` verzweigen.

89 Unit-/Integrationstests für specctl (Single-File- und Directory-Mode)
kommen zu den 221 der anderen drei Tools/geteilten Module hinzu (214 plus 7
neue Tests für die 4-/5-Ebenen-Generalisierung von `lib/abbrev.py`) — 310
insgesamt, unter `tests/`
(`python -m unittest discover -s architecture/scripts/tests -t architecture/scripts`).

Noch offen:
- `tasklist` (rulectl/adrctl) ist absichtlich nur als Stub vorhanden
  (Exit 1, "not yet specified") — Verhalten laut Design-Dokumenten separat
  zu spezifizieren.
- specctl: die bidirektionale adrctl-Verknüpfung (`spec-ref`-Metainfo bei
  adrctl, `lib/spec_link.py`, Auto-Propagation — `design-specctl.md`, "ADR
  Linkage") ist spezifiziert, aber bewusst noch nicht implementiert; `adr`
  wird bis dahin nur manuell über `set-status --adr` / `set-adr` gepflegt.
- specctl: `move` (Wechsel der Metagroup-Ebene/des Elternpfads eines
  bestehenden Sections, inkl. kaskadierender Neuableitung des Object Type für
  den gesamten verschobenen Teilbaum) ist nicht implementiert — nur `add`
  (neu anlegen), `rename` (Name ändern, kaskadiert bereits in
  `ancestor_levels` der Nachkommen) und `reorder` (Geschwister-Reihenfolge
  innerhalb desselben Elternpfads, ebenfalls kaskadierend). Design.md listet
  "Change metagroup" als generische Objekt-Operation; für specctl fehlt dafür
  noch eine CLI-Entsprechung.
- Locking wurde nur innerhalb eines Prozesses (Threads) getestet, nicht
  über echte Multi-Prozess-Konkurrenz.

## Tech-Stack

- Python 3.10, ausschließlich Standardbibliothek — keine externen Pakete.

## Geteilter Code

- Funktionalität, die mehrere Tools nutzen, gehört in ein eigenes Modul
  unter `architecture/scripts/lib/`, nicht mehrfach implementieren.
- Ein CLI-Skript importiert ein anderes CLI-Skript nie direkt (z. B. lädt
  `rulectl.py` nicht `taskctl.py` als Ganzes) — nur
  `lib/`-Module werden tool-übergreifend importiert.
- Neuer geteilter Code: erst prüfen, ob er wirklich generisch ist (kein
  Tool-Sonderfall), bevor er nach `lib/` wandert.

## Konsistenz zwischen den Tools

- Exit-Codes: `0` = ok, `1` = Fehler.
- Fehlermeldungen → stderr, reguläre Ausgabe → stdout.
- CLI-Struktur (Subcommands, `--json`-Flag, `--root` wiederholbar für
  Read-Only-Merge, Positionsargumente ans Ende) einheitlich über alle vier
  Tools halten, auch wenn ein Tool das jeweilige Feature (noch) nicht
  braucht — das gilt für specctl trotz eigener CLI-Implementierung (kein
  `lib/cliapp.py`) genauso.
- Bei einer Änderung an einem Tool prüfen, ob dieselbe Änderung auch bei
  den anderen Sinn ergibt (z. B. neue CLI-Option, Statuslogik).

## Struktur

```
architecture/scripts/
├── CLAUDE.md
├── taskctl.py         # CLI: Taskliste
├── rulectl.py         # CLI: Code-Qualitäts-Regeln
├── adrctl.py          # CLI: ADRs
├── specctl.py         # CLI: Spezifikationsdokumente (eigene CLI, kein lib/cliapp.py)
└── lib/
    ├── ...                # geteilt zwischen allen vier Tools (Locking, Atomic-IO,
    │                      # Numbering, History, Text, Abbrev, Clock, ...)
    ├── model.py, objectfile.py, singlefile.py, store.py, toolspec.py, index.py, render.py
    │                      # generisches Objektformat: taskctl/rulectl/adrctl
    └── spec_model.py, spec_comment.py, spec_document.py, spec_store.py, spec_render.py
                           # specctl-eigenes, leichtgewichtiges Format (design-specctl.md)
```
