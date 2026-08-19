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

- Beachte einhaltung der 'pruity of vison'.
- Beachte Nutzbarkeit der Tools aus der Sicht eines Architekten.
- Pflege die Dokument in `architecture/design`.
- Betrachte kritisch welche Features in die Tools eingefügt werden.

### Skript-Entwickler

- Entwickle `pythonic` Code.
- Achte auf Wiederverwendung von Code durch Libraries.
- Erstelle Tests für den erzeugten Code

### Tester

- Stelle sicher, dass der Code durchgehend testbar ist

## Repo-aufbau

Die Datei `architecture/VISISON.md` beschreibt den Sinn der in `architecture` enthaltenen Tools
Das Verzeichnis `architectur` enthält Tools, die aus der Sicht eine Architekten relevant sind.
Das Verzeichnis `architectur/doc` enthält die Architekturdokumente:

- `architecture/doc/design.md` enthält die allgemeine Spec.
- `architecture/doc/design-taskctl.md` enthält die Spec-relevanten Teile des `taskctl` tools.
- `architecture/doc/design-rulectl.md` enthält die Spec-relevanten Teile des `rulectl` tools.
- `architecture/doc/design-adrctl.md` enthält die Spec-relevanten Teile des `adrctl` tools.
- `architecture/doc/design-decisions.md` enthält die Dokumentation der Architekturentscheidungen.

Das Verzeichnis `architecture/scripts` enthält die bisher entwickelten Skripte, die auch in `architecture/doc/VISION.md` beschrieben werden.
Das Verzeichnis `architecture/skills` enthält die bisher entwickelten AI-Skills (bislang keine)
Das Verzeichnis `architecture/subagent` enthält die bisher entwickelten AI-Subagents (bislang keine)

