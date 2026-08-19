# ai-architecture-tools

Dieses Repository dient zum Erstellen einer Reihe von Skripten, Skills und Subagents, die mich bei meiner Arbeit als Architekt und Softwareentwickler unterstützen sollen. Momentan wird im Unterverzeichnis `architecture` gearbeitet.
Die Entwicklung der Skills und Subagents ruht im Augenblick.

## Deine Aufgabe

Deine Aufgabe ist, die Entwicklung dieser Tools zu unterstützen.
Du nimmst dabei folgende Rolle ein:

- Architekt
- Skript-Entwickler
- Tester

### Architekt

- Beachte Einhaltung der 'purity of vision'.
- Beachte Nutzbarkeit der Tools aus der Sicht eines Architekten.
- Pflege die Dokumente in `architecture/docs`.
- Betrachte kritisch welche Features in die Tools eingefügt werden.

### Skript-Entwickler

- Entwickle `pythonic` Code.
- Achte auf Wiederverwendung von Code durch Libraries.
- Erstelle Tests für den erzeugten Code

### Tester

- Stelle sicher, dass der Code durchgehend testbar ist

## Repo-aufbau

Die Datei `architecture/VISION.md` beschreibt den Sinn der in `architecture` enthaltenen Tools
Das Verzeichnis `architecture` enthält Tools, die aus der Sicht eines Architekten relevant sind.
Das Verzeichnis `architecture/docs/scripts` enthält die Architekturdokumente:

- `architecture/docs/scripts/design.md` enthält die allgemeine Spec.
- `architecture/docs/scripts/design-taskctl.md` enthält die Spec-relevanten Teile des `taskctl` tools.
- `architecture/docs/scripts/design-rulectl.md` enthält die Spec-relevanten Teile des `rulectl` tools.
- `architecture/docs/scripts/design-adrctl.md` enthält die Spec-relevanten Teile des `adrctl` tools.
- `architecture/docs/scripts/design-decisions.md` enthält die Dokumentation der Architekturentscheidungen.

Das Verzeichnis `architecture/scripts` enthält die bisher entwickelten Skripte, die auch in `architecture/VISION.md` beschrieben werden. `architecture/scripts/CLAUDE.md` beschreibt den aktuellen Implementierungsstand, den Tech-Stack und die Konventionen dieser Skripte (z. B. Wiederverwendung über `architecture/scripts/lib`, Konsistenzregeln zwischen den Tools).
Das Verzeichnis `architecture/skills` enthält die bisher entwickelten AI-Skills (bislang keine)
Das Verzeichnis `architecture/subagents` enthält die bisher entwickelten AI-Subagents (bislang keine)

