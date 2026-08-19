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

Kernmodell, Locking, Index-Dateien, Reorder sowie `taskctl.py`, `rulectl.py`,
`adrctl.py` sind implementiert und laufen End-to-End — sowohl Directory-Mode
als auch Single-File-Mode. `reindex` baut `.index.json` neu und erkennt/behebt
Inkonsistenzen aktiv (verwaiste `.tmp`-Dateien werden entfernt, doppelte
Nummern innerhalb einer Metagroup werden gemeldet). `add-<metagroup-type>`
vergibt die Sortnummer automatisch (`max+1`), wenn keine explizit angegeben
wird; `add --<metagroup-type>` akzeptiert zur Referenz auf existierende Pfade
pro Segment Nummer, Name oder `Nummer-Name` (spezifiziert in `design.md`, CLI
Contract; Begründung in `design-decisions.md`, Abschnitt "Amendments").

**`--root` ist projektweit gemeinsam** (`design.md`, "File and Directory
Parameters"; `design-decisions.md`, "Amendments (2026-08-19, shared-root
resolution)"): alle vier Tools nehmen denselben `--root`-Pfad entgegen und
lösen ihn über `lib/store.py`s `resolve_root(given_path, name, default_mode)`
zu ihrem eigenen `<name>.md`/`<name>` innerhalb des gemeinsamen Verzeichnisses
auf (`ToolSpec.root_name`/`default_mode`: `tasks`/Directory, `rules`/Directory,
`adrs`/Directory, `spec`/Single-File). Das macht `adrctl`s künftige
`spec-ref`-Verknüpfung zu `specctl` eindeutig auflösbar, ohne einen separat
konfigurierten Pfad. Multi-Root Read-Only-Merge (`--root` mehrfach) ist dafür
ersatzlos entfallen — kein Tool hatte dafür einen echten Anwendungsfall.
`lib/spec_store.py` nutzt `resolve_root` identisch (`_ROOT_NAME = "spec"`).

`specctl.py` ist implementiert (Add je Ebene, Status inkl. ADR-Pflicht ab
`stable`, `set-adr`, `set-description`, `rename`, `reorder`, `move-to-<Ebene>`,
`delete`, `show`, `list`, `history`, `render`) — **sowohl Single-File- als auch Directory-Mode**
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
`assign_leaf_name`) sowie `lib/store.py`s `resolve_root` (siehe oben) und
`lib/abbrev.py`, das dafür um die 4-/5-Ebenen-Breiten aus `design-specctl.md`
("Object Type") generalisiert wurde, ohne das Verhalten für die anderen drei
Tools zu ändern (deren Breiten summierten schon vorher zu 6).

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
(`add`, `set_status`, `rename`, `reorder`, `move`, ...) modusunabhängig
bleiben — nur `_read`/`_write` verzweigen.

`move-to-<metagroup-type>` (das allgemeine Modell nennt es
`set-<metagroup-type>`, design.md: "Changing an object's metagroup ...
re-derives everything downstream") verschiebt eine Section zu einem neuen
Elternpfad — bei specctl trifft das den **gesamten verschobenen Teilbaum**,
nicht nur die Section selbst: jedes Nachkommen-Object-Type wird aus seinem
eigenen vollständigen Vorfahren-Namenspfad abgeleitet, der sich durch die
Verschiebung ändert, muss also neu abgeleitet werden (nicht nur gepatcht wie
bei `rename`/`reorder`). Abgelehnt werden Verschiebungen in den eigenen
Teilbaum (Zyklus), zum aktuellen Elternpfad (No-op, `reorder` verwenden) und
solche, die für die Section selbst oder einen Nachkommen die 5-Ebenen-Grenze
überschreiten würden.

Ein Spec-vs-Implementierung-Abgleich (2026-08-19) deckte mehrere in
`design.md` bereits dokumentierte, aber nie verdrahtete Operationen auf; die
folgenden wurden daraufhin nachgezogen (`design-decisions.md`, "Amendments
(2026-08-19, closing spec/implementation gaps)"):
- **`delete <id>`** bei allen vier Tools. Bei taskctl/rulectl/adrctl eine
  einfache Entfernung (Objekt ist immer Metagroup-Blatt, keine Kinder
  möglich); bei specctl lehnt `delete` eine Section mit Kind-Sections ab,
  außer `--force-delete` löscht den gesamten Teilbaum. Hinterlässt wie jede
  Löschung eine dauerhafte Nummernlücke, wird nirgends nachträglich geloggt.
- **`set-<user-content-block> <id> <value>`** bei taskctl/rulectl/adrctl
  (z. B. `set-description`, rulectls `set-procedure`, adrctls
  `set-motivation`/`set-rationale`) — dieselbe `set-<type>`-Form wie bei
  Metagroups/Metainfo, jetzt auch für Content-Blöcke. specctl hatte
  `set-description` bereits.
- **`list`-Filter** bei allen vier Tools: `--<metagroup-type> <path>`
  (taskctl/rulectl/adrctl) bzw. `--under <path>` (specctl) — inklusive aller
  Nachfahren, nicht nur exakter Treffer; `--<metainfo-type> <value>`
  (taskctl/rulectl/adrctl) bzw. `--adr <id>` (specctl) — exakter Treffer.
  Höchstens ein Metagroup-Filter pro Aufruf, Metainfo-Filter kombinieren
  sich (AND).
- **`MetainfoSpec.choices` wird jetzt durchgesetzt** (`lib/store.py`,
  `_validate_metainfo_choice`, greift bei `add` und `set-<metainfo-type>`)
  — vorher war das Feld deklariert (z. B. taskctls `review`), aber nie
  geprüft; ein ungültiger Wert wurde still akzeptiert und fiel bei taskctl
  sogar still auf den 3-Schritt-Pfad zurück statt zu scheitern.

Bewusst noch offen aus demselben Abgleich (siehe `design.md`, "Metagroup
Operations"/"Object Operations"): Metagroup-**Rename** und **Change
metagroup** (`set-<metagroup-type>`) für taskctl/rulectl/adrctl — beide im
CLI Contract dokumentiert, aber weder als Store-Methode noch als CLI-Befehl
vorhanden. specctl deckt beides bereits implizit ab (`rename`,
`move-to-<Ebene>`).

374 Unit-/Integrationstests insgesamt unter `tests/`
(`python -m unittest discover -s architecture/scripts/tests -t architecture/scripts`),
davon rund 104 specctl-spezifisch (Single-File- und Directory-Mode, inkl.
`move`), mehrere Tests für `resolve_root` (Kollision, Default-Modus,
`.md`-/Name-Override, Multi-Tool-Koexistenz unter einem `--root`), 17 Tests
für die `spec-ref`-Verknüpfung (`receive_adr_link`, `lib/spec_link.py`, den
generischen `after_dispatch`-Hook, End-to-End über `adrctl`/`specctl`:
`add --spec-ref`, `set-status`-Re-Propagation, retroaktives `set-spec-ref`,
fehlendes Ziel) sowie rund 27 neue Tests für `delete`,
`set-<user-content-block>`, `list`-Filter und die `choices`-Validierung
(Store-Ebene, CLI-Ebene für alle vier Tools, inkl. specctls
`--force-delete`-Kaskade).

Noch offen:
- `tasklist` (rulectl/adrctl) ist absichtlich nur als Stub vorhanden
  (Exit 1, "not yet specified") — Verhalten laut Design-Dokumenten separat
  zu spezifizieren.
- Metagroup-Rename und Change-metagroup (`set-<metagroup-type>`) für
  taskctl/rulectl/adrctl (siehe oben) — im Contract dokumentiert, noch nicht
  implementiert.
- specctl: die bidirektionale adrctl-Verknüpfung ist implementiert —
  `spec-ref=<id>`-Metainfo bei adrctl (einwertig, `design-decisions.md`,
  "Amendments (2026-08-19, spec-ref single-valued)"), `lib/spec_link.py`,
  Auto-Propagation nach `adrctl add`/`set-status`/`set-spec-ref` über
  `lib/cliapp.py`s `after_dispatch`-Hook in `SpecStore.receive_adr_link`
  (loggt einen `M`-History-Eintrag, anders als das weiterhin manuelle
  `set-adr`). Keine Transaktionalität über beide Stores hinweg: schlägt die
  Propagation fehl (z. B. unbekannte `spec-ref`), bleibt die ADR trotzdem
  persistiert, `adrctl` beendet sich mit Exit 1.
- `resolve_root`-Lücke, beim Testen entdeckt, noch nicht entschieden: Zeigt
  `--root` auf ein **existierendes Verzeichnis eines anderen Tools** (z. B.
  `adrctl --root ./project/tasks`, wobei `tasks/` bereits taskctl gehört),
  wird dieses Verzeichnis unverändert als *gemeinsames* Verzeichnis behandelt
  (`design.md`: "path exists and is a directory → path itself") — adrctl
  legt dann `./project/tasks/adrs/` an, verschachtelt unter dem fremden
  Tool-Verzeichnis, statt dessen Elternverzeichnis als geteiltes Verzeichnis
  zu erkennen. Nur der `.md`-Datei-Fall und der exakte Name-Match-Fall (beide
  bestätigt) lösen das Elternverzeichnis auf; für ein fremdes, bereits
  existierendes Tool-*Verzeichnis* gibt es noch keine analoge Regel.
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
- CLI-Struktur (Subcommands, `--json`-Flag, `--root` als einzelner,
  projektweit gemeinsamer Pfad, Positionsargumente ans Ende) einheitlich über
  alle vier Tools halten, auch wenn ein Tool das jeweilige Feature (noch)
  nicht braucht — das gilt für specctl trotz eigener CLI-Implementierung
  (kein `lib/cliapp.py`) genauso.
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
