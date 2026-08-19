# scripts/ — Python-CLI-Tools (taskctl.py, rulectl.py, adrctl.py)

Agentische CLI-Tools für Taskmanagement (`taskctl.py`), Code-Qualitäts-Regeln
(`rulectl.py`) und Architecture Decision Records (`adrctl.py`). Objektmodell,
Dateiformat und CLI-Kontrakt sind spezifiziert in:

- `doc/architecture/scripts/workctl/design.md` — allgemeines Objektmodell, CLI-Kontrakt,
  Locking, Index-Dateien (gilt für alle drei Tools).
- `doc/architecture/scripts/workctl/design-taskctl.md`, `design-rulectl.md`,
  `design-adrctl.md` — tool-spezifische Ergänzungen.

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
"Amendments"). 214 Unit-/Integrationstests unter `tests/`
(`python -m unittest discover -s scripts/workctl/tests -t scripts/workctl`).

Noch offen:
- `tasklist` (rulectl/adrctl) ist absichtlich nur als Stub vorhanden
  (Exit 1, "not yet specified") — Verhalten laut Design-Dokumenten separat
  zu spezifizieren.
- Locking wurde nur innerhalb eines Prozesses (Threads) getestet, nicht
  über echte Multi-Prozess-Konkurrenz.

## Tech-Stack

- Python 3.10, ausschließlich Standardbibliothek — keine externen Pakete.

## Geteilter Code

- Funktionalität, die mehrere Tools nutzen, gehört in ein eigenes Modul
  unter `scripts/workctl/lib/`, nicht mehrfach implementieren.
- Ein CLI-Skript importiert ein anderes CLI-Skript nie direkt (z. B. lädt
  `rulectl.py` nicht `taskctl.py` als Ganzes) — nur
  `lib/`-Module werden tool-übergreifend importiert.
- Neuer geteilter Code: erst prüfen, ob er wirklich generisch ist (kein
  Tool-Sonderfall), bevor er nach `lib/` wandert.

## Konsistenz zwischen den Tools

- Exit-Codes: `0` = ok, `1` = Fehler.
- Fehlermeldungen → stderr, reguläre Ausgabe → stdout.
- CLI-Struktur (Subcommands, `--json`-Flag, Positionsargumente ans Ende)
  einheitlich über alle drei Tools halten, auch wenn ein Tool das
  jeweilige Feature (noch) nicht braucht.
- Bei einer Änderung an einem Tool prüfen, ob dieselbe Änderung auch bei
  den anderen beiden Sinn ergibt (z. B. neue CLI-Option, Statuslogik).

## Struktur

```
scripts/workctl/
├── CLAUDE.md
├── taskctl.py         # CLI: Taskliste
├── rulectl.py         # CLI: Code-Qualitäts-Regeln
├── adrctl.py          # CLI: ADRs
└── lib/
    ├── ...            # geteilt: Zukünftige Libraries
```
