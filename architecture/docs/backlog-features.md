# Feature-Backlog: Weiterentwicklung der CLI-Tools

Aufgeschobene Weiterentwicklungen an `architecture/scripts/` — Features und
Code-Umbauten, die erst umgesetzt werden, wenn ihr Auslöser eintritt.
Wann und wie ein Eintrag angegangen wird, regelt
[`CLAUDE.md`](CLAUDE.md), Abschnitt "Backlogs". Ein Eintrag ist keine
Freigabe zur Umsetzung.

Agent-/Skill-Optimierungen und Agent-Evals stehen in
[`backlog-optimization.md`](backlog-optimization.md).

## F1: Metagroup-Rename für taskctl, questctl, rulectl, adrctl

- **Auslöser**: Ein Agent, Skill oder der User braucht konkret das
  Umbenennen eines Metagroup-Pfads (Phase, Group/Subgroup,
  Language/Context/Category, Domain/Component); oder es wird ohnehin an der
  Metagroup-Verwaltung gearbeitet (`lib/metagroup.py`,
  `Store.add_metagroup_path`/`set_metagroup` in `lib/store.py`).
- **Nutzen**: Schließt die letzte dokumentierte Lücke im Metagroup-Kontrakt;
  ein Tippfehler oder eine geänderte Taxonomie erfordert heute, alle Objekte
  einzeln per `group-<Typ>` auf einen neuen Pfad zu verschieben.
- **Aufwand**: mittel — eine Store-Operation für Directory- und
  Single-File-Mode, ein generisches CLI-Kommando, Tests; zuvor eine kurze
  Designklärung.
- **Kontext und Quellen**:
  - `docs/scripts/design.md`, "Metagroup Operations" (Rename nur als "not yet
    implemented" erwähnt — kein Kontrakt), "Metagroups", "Object Type"
    (insb. "Stability": eine gespeicherte Abkürzung wird nie stillschweigend
    geändert), "Numbering".
  - Vorbild für Kaskaden: specctls `rename` (`docs/scripts/design-specctl.md`,
    "Operations"; `lib/spec_store.py`) und `Store.set_metagroup`
    (`lib/store.py`, neue Datei zuerst schreiben, dann alte löschen).
  - Betroffener Speicher: Metagroup-Verzeichnisse `<nr>-<name>/` mit
    `.index.md` (Abkürzung) und `.index.json` (Directory-Mode),
    `## Metagroups`-Abschnitt (Single-File-Mode), sowie in **jedem**
    enthaltenen Objekt die Metagroup-Bullets im `## Meta`-Abschnitt
    (`lib/objectfile.py`) und — falls sich der Object Type ändert — der
    Dateiname/die Signatur.
  - CLI-Erzeugung: `lib/cliapp.py`, `build_parser`/`dispatch` (dort entsteht
    auch `add-<Typ>`).
  - Seiteneffekt: `rulectl tasklist` leitet Phasen-Namen aus dem
    Regel-Pfad ab (`lib/tasklist.py`); ein Rename ändert beim nächsten
    Re-Export die Ziel-Phase.
- **Offene Designfragen** (vor der Implementierung mit dem User klären;
  Empfehlungen sind Vorschläge, keine Festlegung):
  1. CLI-Form — Empfehlung: `rename-<metagroup-type> <path> <new-name>`,
     analog zu `add-<metagroup-type>`; `<path>` wird wie überall aufgelöst
     (Nummer, Name oder `Nummer-Name` je Segment).
  2. Abkürzung/Object Type — Empfehlung: bleiben standardmäßig unverändert
     (stabile Dateinamen, "Stability"-Regel); optional `--abbrev <code>`
     setzt sie neu, dann werden Object Type, Signatur und Dateiname aller
     enthaltenen Objekte kaskadierend neu abgeleitet.
  3. Sortnummer — Empfehlung: bleibt erhalten; Reihenfolge ändert `reorder`.
  4. History — Empfehlung: `M`-Eintrag je betroffenem Objekt nur, wenn sich
     dessen Object Type ändert; ein reiner Namenswechsel der Metagroup wird
     nicht pro Objekt geloggt.
  5. Geltung — Empfehlung: alle vier generischen Tools, beide Modi, jede
     Metagroup-Ebene; Rename auf einen bereits existierenden
     Geschwister-Namen und No-op werden abgelehnt.
- **Vorgehen**:
  1. Offene Designfragen mit dem User klären.
  2. `docs/scripts/design.md` ("Metagroup Operations", ggf. "Object Type")
     um den Kontrakt ergänzen — Design-Dokumente sind maßgeblich, nicht der
     Code.
  3. Store-Methode in `lib/store.py` für beide Modi implementieren
     (Lock halten, atomare Schreibvorgänge, bei Kaskaden neue Dateien vor
     dem Löschen der alten), Hilfsfunktionen in `lib/metagroup.py`.
  4. CLI-Kommando generisch in `lib/cliapp.py` erzeugen (kein
     Tool-Sonderfall).
  5. Tests: `tests/lib/test_store.py`, `tests/lib/test_metagroup.py`,
     `tests/lib/test_cliapp.py`, plus je ein End-to-End-Fall in den
     Tool-Tests; Fehlerfälle (unbekannter Pfad, Kollision, No-op).
  6. Betroffene Skills prüfen (`skills/*-author-cli/SKILL.md` und ihre
     Design-Dokumente unter `docs/skills/`) und ggf. ergänzen; dann
     `version` in `.claude-plugin/plugin.json` erhöhen.
- **Fertig, wenn**: Rename funktioniert in beiden Modi für alle vier Tools,
  `design.md` beschreibt den Kontrakt, die vollständige Testsuite ist unter
  Python 3.10 und 3.13 grün (CI), `reindex` meldet nach einem Rename keine
  Inkonsistenzen.
- **Abschluss**: siehe [`CLAUDE.md`](CLAUDE.md), "Backlogs"; zusätzlich den
  Punkt "Metagroup-Rename" in `scripts/CLAUDE.md`, "Offene Punkte", und die
  "not yet implemented"-Zeile in `design.md` entfernen.

## F2: Parser und Dispatch tabellengesteuert umbauen

- **Auslöser**: Ein neuer Subcommand-*Typ* kommt hinzu (eine neue Familie wie
  `rename-<Typ>`, nicht nur ein weiterer Eintrag einer bestehenden), oder
  `build_parser`/`dispatch` in `lib/cliapp.py` bzw. `specctl.py` werden
  ohnehin größer umgebaut. Fällt F1 an, F2 vorher oder zusammen mit F1
  anbieten.
- **Nutzen**: Jeder neue Subcommand verlängert heute lange if/elif-Ketten;
  eine Tabelle Subcommand → Handler macht Erweiterungen lokal und
  übersichtlich.
- **Aufwand**: mittel — rein strukturell, aber zwei Implementierungen und
  breite Verhaltensoberfläche.
- **Kontext und Quellen**:
  - `lib/cliapp.py`: `build_parser` (~98 Zeilen), `dispatch` (~99 Zeilen);
    `dispatch` hat mit `extra_handlers` bereits einen Tabellen-Ansatz für
    tool-eigene Kommandos.
  - `specctl.py`: `build_parser` (~114 Zeilen), `dispatch` (~84 Zeilen).
  - specctl behält seine eigene CLI (`design-decisions.md`, "Amendments
    (2026-10-21, cross-tool CLI contract tests)": Zusammenführen abgelehnt).
  - Konventionen: `scripts/CLAUDE.md`, "Geteilter Code" und "Konsistenz
    zwischen den Tools".
- **Vorgehen**:
  1. Vorher-Stand sichern: `--help` jedes Tools und jedes Subcommands in
     eine Datei im Scratchpad schreiben.
  2. In `lib/cliapp.py` die Subcommand-Familien (Add, `add-<Typ>`,
     `group-`/`info-`/`set-<Typ>`, Lese-Kommandos, ...) als Tabelle
     Subcommand → (Parser-Konfiguration, Handler) abbilden; `extra_handlers`
     darin aufgehen lassen.
  3. In `specctl.py` dasselbe Muster anwenden. Kein gemeinsames Modul in
     `lib/`, solange es nicht ohne Tool-Sonderfall generisch ist.
  4. Nachher-Stand der `--help`-Ausgaben erzeugen und vergleichen.
- **Fertig, wenn**: verhaltensneutral — die bestehende Testsuite inkl.
  `tests/test_cli_contract.py` läuft unverändert grün (keine Tests
  angepasst), die `--help`-Ausgaben sind identisch, keine Funktion in den
  beiden Parser-/Dispatch-Pfaden ist länger als ~50 Zeilen.
- **Nicht Teil von F2**: `Store.add` (`lib/store.py`, ~108 Zeilen) und
  `SpecStore.move` (`lib/spec_store.py`, ~83 Zeilen) nur zerlegen, wenn sie
  ohnehin fachlich geändert werden.
- **Abschluss**: siehe [`CLAUDE.md`](CLAUDE.md), "Backlogs".
