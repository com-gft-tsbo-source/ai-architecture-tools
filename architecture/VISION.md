# Vision

Ziel ist, eine Reihe von Skripten, Skills und Subagents zu entwickeln, um:

- Softwarespezifikationen zu festzuhalten. Der Agent soll in Interaktion mit dem User die vorhandenen Tools nutzen, um dessen Spezifikation kooperativ zu erstellen.
- Änderungen an der Spezifikation zu tracken. Dazu sollen die Änderungen nachvollziehbar protokolliert werden.
- Qualitätsregeln zu definieren.
- Tasklisten zu managen

## Skripte

### `taskctl` (existiert bereits)

Diese Tool managed Aufgabenlisten. Diese können von KI und Usern gemeinsam genutzt werden. User nutzen diese hauptsächlich um den Arbeitsstand der KI zu prüfen und Feedback zu geben (reviews).

Das Tool soll folgendes leisten:

- Ermöglicht der KI komplexe Aufgaben in kleinere Unteraufgaben zu zerteilen und diese sequentiell abzuarbeiten.
- Tracken des Vortschritts der Arbeit durch Tracken des Zustands der Aufgaben und führen einer Historie.
- Aufgabenübergabe zwischen User und KI zu ermöglichen. Z.B. für Aufgaben, die einen User-Review benötigen.
- Wiederaufnahme der Arbeit durch die KI nach Unterbrechungen.

### `rulectl` (existiert bereits)

Tool um Qualitätsrichtlinien festzulegen. Diese Richtlinien sollen leicht durch die KI nutzbar und prüfbar sein. Die Richtlinien können für verschiedene Aspekte eines Projekts untergliedert werden: Qualitätsrichtlinen für idiomatischen Code, Richtlinien für Architektur, Richtlinien für APIs, ...

Um das Prüfen der Qualitätsrichtlinien zu unterstützen, kann das Tool seine Richtlinien nach `taskctl` exportieren um diese dann sequentiell mit Logging zu prüfen.

### `adrctl` (existiert bereits)

Tool um ADRs zu managen. Dies soll von der KI genutzt werden, um getroffene Entscheidungen zu dokumentieren. Auch kann der User hier Änderunge eintragen, die von der KI umgesetzt werden sollen.

Auch diese Tool unterstüzt einen export nach `taskctl` um die Umsetzung von Änderungen zu tracken.

### `specctl` (existiert nicht)

Diese Tool dient zum Managen der Spezifikation. Diese Tool ist nicht implementiert und auch nicht dokumentiert.

Das Ziel hier ist:

- Dokumente wie `architecture/doc/design.md` durch User und KI zu managen.
- Das Dokument menschenlesbar zu halten, während es auch für KI geeignet ist.
- Eine Verbindung mit `adrctl` herzustellen. Zumindest Querverweise zwischen beiden Tools soll es geben. `adrctl` als Tool um die Historie des Designdokuments zu managen wäre wünschenswert.
- Es muss flexibel sein, um unterschiedliche Gliederungstiefen managen zu können.

