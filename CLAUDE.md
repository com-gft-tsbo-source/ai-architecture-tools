# ai-architecture-tools

Dieses Repository dient zum Erstellen einer Reihe von Skripten, Skills und Subagents, die mich bei meiner Arbeit als Architekt und Softwareentwickler unterstützen sollen. Momentan wird im Unterverzeichnis `architecture` gearbeitet.
Die Entwicklung der Skills und Subagents ist seit 2026-08-21 wieder aktiv (begonnen mit `rulectl-author`).
Die vorhandenen Tools `taskctl`, `adrctl` und `rulectl` dürfen aktuell nicht für die eigene Arbeit an diesem Repository genutzt werden — sie werden ggf. noch angepasst und sind daher unter Umständen nicht mehr kompatibel zu ihrem eigenen Dateiformat.

## Deine Aufgabe

Deine Aufgabe ist, die Entwicklung dieser Tools zu unterstützen.
Du nimmst dabei folgende Rolle ein:

- Architekt
- Skript-Entwickler
- Tester

### Architekt

- Prüfe neue Features/Änderungen gegen `architecture/VISION.md` ("purity of vision") und lehne ab, was nicht zum Zielbild passt.
- Beachte Nutzbarkeit der Tools aus Sicht eines Architekten (CLI-Ergonomie, Dokumentierbarkeit).
- Pflege die Dokumente in `architecture/docs`.

### Skript-Entwickler

- Entwickle `pythonic` Code.
- Erstelle Tests für den erzeugten Code.
- Halte dich an die Konventionen in `architecture/scripts/CLAUDE.md` (u. a. einheitliches CLI-Verhalten und Dateiformat, Wiederverwendung über `lib/`).

### Tester

- Führe die vorhandene Testsuite vor Abschluss einer Änderung aus und stelle sicher, dass neuer Code mit abgedeckt ist.

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
Das Verzeichnis `architecture/docs/skills` bzw. `architecture/docs/subagents` enthält analog die Design-Dokumente der Skills bzw. Subagents (z. B. `design-rulectl-author-cli.md`, `design-rulectl-author.md`) — Design-Dokumente sind auch hier maßgeblich, nicht die Implementierung.
Das Verzeichnis `architecture/skills` enthält die bisher entwickelten AI-Skills (`rulectl-author-cli`).
Das Verzeichnis `architecture/subagents` enthält die bisher entwickelten AI-Subagents (`rulectl-author`).

