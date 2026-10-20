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

### `questctl` (existiert bereits)

Tool um offene Fragen zu managen, z. B. Rückfragen an einen Kunden während der Anforderungsklärung. Spezifiziert in `architecture/docs/scripts/design-questctl.md`, implementiert in `architecture/scripts/questctl.py`. Fast identisch zu `taskctl`, aber: die verwalteten Objekte sind Fragen statt Aufgaben; statt einer Phase gibt es eine optionale, store-weit einheitliche Group/Subgroup-Gliederung; Blocker/Reviews blockieren nicht die Bearbeitung anderer Fragen (mehrere Fragen können parallel bearbeitet werden); ein `answer`-Befehl trägt die Antwort in eine eigene, nur so beschreibbare Sektion ein.

### `specctl` (existiert bereits)

Diese Tool dient zum Managen der Spezifikation. Spezifiziert in `architecture/docs/scripts/design-specctl.md`, implementiert in `architecture/scripts/specctl.py`.

Das Ziel hier ist:

- Dokumente wie `architecture/docs/scripts/design.md` durch User und KI zu managen.
- Das Dokument menschenlesbar zu halten, während es auch für KI geeignet ist.
- Eine Verbindung mit `adrctl` herzustellen. Zumindest Querverweise zwischen beiden Tools soll es geben. `adrctl` als Tool um die Historie des Designdokuments zu managen wäre wünschenswert.
- Es muss flexibel sein, um unterschiedliche Gliederungstiefen managen zu können.

## Skills und Subagents

Aufbauend auf den Skripten entstehen Skills und Subagents, die diese für die KI direkt nutzbar machen — jeweils als Paar: ein Subagent für eine eigenständige Teilaufgabe, plus ein schlankes, wrappendes Skill, das dem Subagent den CLI-Kontrakt des jeweiligen Skripts vermittelt (der Subagent bedient das Skript nie direkt aus eigenem Wissen heraus). Alle sind generisch gehalten — nutzbar in beliebigen Projekten, die die Skripte einsetzen, nicht nur in diesem Repository.

Rund um `rulectl` sind zwei Subagents vorgesehen:

- **`rulectl-author`** (existiert bereits, mit Skill `rulectl-author-cli`): zerlegt ein Dokument mit Qualitätsrichtlinien in einzelne Rules, ordnet sie passenden Metagruppen zu und legt sie in `rulectl` an. Spezifiziert in `architecture/docs/subagents/design-rulectl-author.md` und `architecture/docs/skills/design-rulectl-author-cli.md`.
- **`rulectl-checker`** (existiert bereits, mit Skill `rulectl-checker-cli`): prüft eine Codebasis gegen bestehende Rules, indem eine per `rulectl tasklist` erzeugte Taskliste abgearbeitet wird (Ergebnis je Task: konform, Verstoß — eskaliert zur User-Review — oder nicht prüfbar). Reiner Prüfer, ändert nie selbst Code. Spezifiziert in `architecture/docs/subagents/design-rulectl-checker.md` und `architecture/docs/skills/design-rulectl-checker-cli.md`.

Rund um `questctl` sind drei Subagents vorgesehen — Beispiel-Workflow: Sales erhält Kundenanforderungen; `questctl-author` zerlegt sie in eine Fragenliste, die an den Kunden geht; `questctl-checker` ordnet die zurückkommenden Kundenantworten den Fragen zu; nach mehreren Iterationen entsteht eine Spezifikation, gegen die `questctl-researcher` prüft, ob und wie alle ursprünglichen Anforderungen erfüllt wurden:

- **`questctl-author`** (existiert bereits, mit Skill `questctl-author-cli`): zerlegt ein Dokument — oder ein ganzes Verzeichnis von Dokumenten — in einzelne Fragen und bildet dafür zunächst eine rein inhaltlich (nicht struktur-)basierte Group/Subgroup-Taxonomie, die einmalig mit dem User bestätigt wird, bevor irgendetwas angelegt wird. Geht ansonsten vor wie `rulectl-author`. Spezifiziert in `architecture/docs/subagents/design-questctl-author.md` und `architecture/docs/skills/design-questctl-author-cli.md`.
- **`questctl-checker`** (existiert bereits, mit Skill `questctl-checker-cli`): ordnet eine Quelle von Antworten (z. B. eine Kunden-E-Mail) den passenden Fragen im Fragenkatalog zu und trägt sie wortwörtlich als Antwort ein — beantwortet dabei selbst nie eine Frage. Arbeitet den offenen Fragenkatalog sequentiell ab, außer der User verlangt explizit ein paralleles Vorgehen für eine benannte Gruppe. Spezifiziert in `architecture/docs/subagents/design-questctl-checker.md` und `architecture/docs/skills/design-questctl-checker-cli.md`.
- **`questctl-researcher`** (existiert bereits, mit Skill `questctl-researcher-cli`): erstellt eigenständig Antworten auf offene Fragen anhand einer gegebenen Datenbasis, mit derselben Sequentiell/Parallel-Vorgabe wie `questctl-checker` und einer Beweis-Schwelle, die eine erfundene Antwort verbietet (dann bleibt die Frage offen bzw. wird blockiert). Spezifiziert in `architecture/docs/subagents/design-questctl-researcher.md` und `architecture/docs/skills/design-questctl-researcher-cli.md`.

Rund um `taskctl` sind zwei Subagents vorgesehen — anders als bei `rulectl`/`questctl` exportiert kein anderes Tool eine begrenzte Taskliste nach `taskctl`; die beiden Subagents legen Tasks direkt an bzw. arbeiten sie direkt ab:

- **`taskctl-author`** (existiert bereits, mit Skill `taskctl-author-cli`): erarbeitet aus einer Reihe von Dokumenten (Design-Dokumente o. Ä.) und gemäß dem Prompt des Users eine Taskliste — ermittelt zuerst die notwendigen Phasen und verteilt dann die Tasks darin, prompt-getrieben (nicht struktur-atomisierend wie `rulectl-author`/`questctl-author`). Kann auf explizite Anfrage eine vorhandene Taskliste erweitern oder (mit vorgeschalteter Bestätigung, da unumkehrbar) verkleinern. Spezifiziert in `architecture/docs/subagents/design-taskctl-author.md` und `architecture/docs/skills/design-taskctl-author-cli.md`.
- **`taskctl-worker`** (existiert bereits, mit Skill `taskctl-worker-cli`): arbeitet eine von `taskctl-author` (oder von Hand) angelegte Taskliste gemäß dem Prompt des Users ab — findet den nächsten Task per `next`, führt die beschriebene Arbeit aus und trägt Fortschritt/Ergebnis über `annotate`/`set-status` ein, inkl. Eskalation an User- oder Subagent-Review. Standardmäßig nur der nächste Task pro Aufruf, danach Ende; nur auf explizite Anweisung im Prompt auch schleifend bis zur Erschöpfung bzw. bis zu einer blockierenden Review. Von `rulectl tasklist` exportierte Prüf-Tasks bearbeitet er nicht (die gehören `rulectl-checker`), und nach außen wirkende Aktionen (Push, Deploy, Senden) führt er nur auf ausdrückliche Anweisung aus. Spezifiziert in `architecture/docs/subagents/design-taskctl-worker.md` und `architecture/docs/skills/design-taskctl-worker-cli.md`.

Rund um `specctl` und `adrctl` sind gemeinsam zwei Subagents vorgesehen, aufgeteilt nach Lebenszyklus-Phase des Dokuments (nicht nach Tool) — solange eine `specctl`-Section im Status `draft` ist, wird ausschließlich mit `specctl` gearbeitet; ab `stable` läuft jede Änderung über eine sie autorisierende `adrctl`-ADR:

- **`specctl-author`** (existiert bereits, mit Skill `specctl-author-cli`): baut und restrukturiert `draft`-Inhalt eines `specctl`-Dokuments kooperativ, Zug um Zug nach Anweisung des Users — anlegen, ändern, verschieben, umbenennen, löschen, alles ungegated, solange die betroffene Section `draft` ist. Initialisiert bei Bedarf selbst einen neuen Store (`init`). Rührt nie an `adrctl` und ändert nie den Status einer Section. Spezifiziert in `architecture/docs/subagents/design-specctl-author.md` und `architecture/docs/skills/design-specctl-author-cli.md`.
- **`specctl-adr-author`** (existiert bereits, mit Skills `specctl-editor-cli` und `adrctl-author-cli` — der erste Subagent dieser Familie, dessen Workflow zwei Tools über zwei Skills umspannt): übernimmt eine Section erstmals von `draft` nach `stable` sowie jede spätere Änderung an bereits `stable`n Sections — legt nie selbst neue Sections an. Jede Themenänderung wird zuerst per `adrctl` mit einer (bei `--set-status accepted` direkt akzeptierten) ADR autorisiert, danach erst per `specctl` in die Section geschrieben; pro zusammenhängendem Thema genau eine ADR, bei mehreren betroffenen Sections eine primäre über `--spec-ref` plus manuelles `specctl set-adr` für die übrigen. Erkennt der User-Prompt eine bloße Korrektur an bereits von einer ADR abgedecktem Inhalt (statt einer neuen Entscheidung), wird die bestehende ADR erst nach expliziter, per Deferred-Report eingeholter Bestätigung des Users wiederverwendet und inhaltlich nachgeführt statt eine neue, die alte ablösende ADR zu erzeugen — wie jedes Gate dieser Tool-Familie blockiert das nicht im laufenden Run, sondern wird beim nächsten Aufruf mit der Antwort im Prompt aufgelöst. Der Übergang nach `deprecated` sowie ein Rework `stable`→`draft` bleiben ausschließlich manuelle, User-geführte CLI-Aufrufe außerhalb dieses Workflows. Spezifiziert in `architecture/docs/subagents/design-specctl-adr-author.md`, `architecture/docs/skills/design-specctl-editor-cli.md` und `architecture/docs/skills/design-adrctl-author-cli.md`.
