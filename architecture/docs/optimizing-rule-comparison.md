# Regelabgleich: kompakte Agents und Skills

Stand: 2026-10-20. Vergleichsbasis: Commit `e476614` vor der redaktionellen
Verdichtung. Die 9 Agent-Rollen, ihre Tool-Berechtigungen, Namen und 10 Skills
bleiben erhalten. Es werden keine CLI-Skripte oder Tests verändert.

## Bestätigter Rahmen

Verhalten erhalten; Verständlichkeit vor weniger geladenen Tokens. Keine
Kürzungsquote als Ziel. Jedes Rollenpaar bleibt separat nutzbar; kein Author
setzt Worker-Anweisungen voraus und umgekehrt. `specctl-adr-author` lädt wie
bisher ausdrücklich zwei Skills. Keine gemeinsame Runtime-Referenz und kein
neuer Lademechanismus. Full-spec-Pfade bleiben Entwicklerhinweise.

Agents enthalten Eingaben/Vertrauensgrenzen, fachliche Reihenfolge,
Entscheidungen, zentrale Freigabegrenzen und Berichtsanforderungen. Skills
enthalten den vollständigen CLI-Vertrag, technische Übergänge, Fehlerbehandlung
und Store-Verifikation. Kritische Grenzen dürfen zur Klarheit wiederholt sein.
Begründungen, Historie und Zukunftsplanung bleiben in den Design-Dokumenten.

## Historischer Umfang des Commits 0034def

Whitespace-getrennte Wörter, einschließlich Frontmatter, Beispiele und Code;
keine Modell-Tokenmessung. Gemessen werden ausschließlich die 19 Runtime-
Definitionen, nicht die zusätzlichen Design-/Abgleich-/Backlog-Dokumente.
Die folgende Tabelle beschreibt die damalige Kürzung von e476614 nach 0034def;
sie ist keine aktuelle Messung der inzwischen überarbeiteten Dateien.
Zeilen sind kein eigenständiges Qualitätsmaß.

| Definition | Zeilen vorher → nachher | Wörter vorher → nachher |
|---|---:|---:|
| [questctl-author](../agents/questctl-author.md) | 323 → 84 | 2652 → 666 |
| [questctl-checker](../agents/questctl-checker.md) | 181 → 53 | 1570 → 394 |
| [questctl-researcher](../agents/questctl-researcher.md) | 189 → 53 | 1563 → 411 |
| [rulectl-author](../agents/rulectl-author.md) | 248 → 74 | 2182 → 553 |
| [rulectl-checker](../agents/rulectl-checker.md) | 242 → 59 | 2187 → 440 |
| [specctl-adr-author](../agents/specctl-adr-author.md) | 172 → 78 | 1472 → 575 |
| [specctl-author](../agents/specctl-author.md) | 99 → 37 | 842 → 257 |
| [taskctl-author](../agents/taskctl-author.md) | 240 → 90 | 1990 → 721 |
| [taskctl-worker](../agents/taskctl-worker.md) | 193 → 75 | 1567 → 560 |
| [adrctl-author-cli](../skills/adrctl-author-cli/SKILL.md) | 179 → 80 | 1033 → 450 |
| [questctl-author-cli](../skills/questctl-author-cli/SKILL.md) | 137 → 71 | 941 → 375 |
| [questctl-checker-cli](../skills/questctl-checker-cli/SKILL.md) | 100 → 97 | 627 → 539 |
| [questctl-researcher-cli](../skills/questctl-researcher-cli/SKILL.md) | 100 → 97 | 648 → 551 |
| [rulectl-author-cli](../skills/rulectl-author-cli/SKILL.md) | 99 → 60 | 631 → 331 |
| [rulectl-checker-cli](../skills/rulectl-checker-cli/SKILL.md) | 138 → 64 | 995 → 368 |
| [specctl-author-cli](../skills/specctl-author-cli/SKILL.md) | 173 → 78 | 1074 → 474 |
| [specctl-editor-cli](../skills/specctl-editor-cli/SKILL.md) | 151 → 68 | 971 → 408 |
| [taskctl-author-cli](../skills/taskctl-author-cli/SKILL.md) | 126 → 62 | 719 → 313 |
| [taskctl-worker-cli](../skills/taskctl-worker-cli/SKILL.md) | 163 → 84 | 936 → 471 |
| **Gesamt** | **3253 → 1364** | **24600 → 8857** |

## Erhaltene fachliche Regeln nach Rollenpaar

Die Verweise nennen die neuen Runtime-Abschnitte; die ausführlichen bisherigen
Regeln und Begründungen bleiben im jeweiligen `docs/subagents/design-*.md`
und `docs/skills/design-*-cli.md` erhalten. Bei der Prüfung werden Agent und
zugehöriger Skill gemeinsam betrachtet, niemals unterschiedliche Rollen.

| Paar | Bisherige Regeln | Neue Zuordnung |
|---|---|---|
| rulectl-author / rulectl-author-cli | Genau eine Datei/Text/URL; Fetch-Fallback und Abbruch; Daten≠Anweisungen; strukturelle Worklist und atomare Kandidaten; Language-Gate; gleiche Pfade; Source/Procedure/Tool/Weight nur nach Vorgabe; active; vollständiger Report. | Agent: Inputs and trust, Workflow, Rule content, Report and boundaries. Skill: Commands, Errors and limits, Conventions. |
| questctl-author / questctl-author-cli | Eine Quelle einschließlich rekursivem Verzeichnis; Prompt führt, Gruppierung nur inhaltlich; pro Dokument/Einheit/Kandidat rückverfolgbar; Tiefen 0/1/2; synthetische Gruppen nur bei festgelegter Tiefe 2; komplette einmalig bestätigte Taxonomie; offene Questions ohne Review/Answer. | Agent: Inputs and trust, Workflow (Tiefen-Tabelle und Gate), Content and report. Skill: Conventions and depth detection, Commands, Errors and limits. |
| rulectl-checker / rulectl-checker-cli | Reiner Prüfer; Code untrusted; Definitionseigene leere Tool-Allowlist mit vollständigen Profilen; jeder aktive in-scope Check pro Lauf; feste Export-IDs; Claim vor Prüfung; Branch aus assignee-type; Plan vor Urteil; ausreichende Coverage; X/R/B und unverarbeitete Fälle. | Agent: Inputs and trust, Tool allow-list, Workflow. Skill: Refresh and claim, Record and verify. Keine list/next-Ausweitung. |
| questctl-checker / questctl-checker-cli | Vollständiges rekursives Lesen des Antwortverzeichnisses; nur Attribution, wörtlich inkl. Fehlern; mehrere Auszüge und Mehrfachzuordnung; klare/unsichere/fehlende Matches; keine eigene Antwort oder erneute Prüfung geschlossener Fragen. | Agent: Inputs and boundaries, Workflow, Report. Skill: Snapshot and claims, Record the outcome, Errors and verification. |
| questctl-researcher / questctl-researcher-cli | Begrenzte Datenbasis ohne Live-Recherche; Forschungsplan vor Evidenzlektüre; immer Recherchetrace; Synthese nur durch Belege; ausreichend belegt/thin evidence/keine Evidenz; Unsicherheit im Antworttext; keine erneute Prüfung beantworteter Fragen. | Agent: Inputs and boundaries, Workflow, Report. Skill: Snapshot and claims, Record the outcome, Errors and verification. |
| specctl-author / specctl-author-cli | User-Prompt statt externer Quellen; vollständiger Auftrag; ausschließlich Draft; fehlende Vorfahren frei; keine Schreib-/Löschfreigabe; Initialisierung nur auf dokumentierten Fehler; Title nicht erfinden, Preamble nur geliefert; Erstell-/Löschprüfung. | Agent: Inputs and boundaries, Workflow. Skill: Conventions and initialization, Create and edit, Structure/deletion/reads, Errors. |
| specctl-adr-author / specctl-editor-cli + adrctl-author-cli | Tatsächlichen Status/Link lesen; Themen bilden; eine akzeptierte ADR pro Thema inkl. gemischter Sections; deterministische Primärsection; alle Links vor Promotion/Edit prüfen; Fehler stoppen abhängige Schritte; Domain-/Korrektur-Gates mit Wiederaufruf; kein Session-Shortcut; nur veraltete ADR-Felder korrigieren; alte ADR bei verbleibenden Verweisen erhalten. | Agent: Scope and decisions, Workflow per topic, Correction gate, Report. Editor-Skill: Linked writes, Verification/retirement/errors. ADR-Skill: Creation and linkage, Retirement and correction, Errors. |
| taskctl-author / taskctl-author-cli | Alle Quellen vor Planung, Abbruch bei einer fehlenden Quelle; Prompt bestimmt Scope/Details/Erweiterung/Kürzung; synthetisierte eigenständige Tasks; neue Stores mit Phases, bestehende flache bleiben flach; Ausführungsreihenfolge; Duplikate nur gleiche Phase; konkrete IDs für Zweipass-Löschung; remote nur explizit, separat und review=user; origin bleibt leer. | Agent: Inputs and sources, Planning and writing, Deletion, Content and assignments, Verification and report. Skill: Commands, Errors and limits. |
| taskctl-worker / taskctl-worker-cli | Einzelner Task standardmäßig; Schleife nur explizit; globale Queue ohne Scope-Bypass; Resume via History; keine rulectl-Exporte ausführen, Herkunft ausschließlich origin; alte Marker durch Re-Export; lokale Arbeit/Evidenz; Reviews erhalten; konkrete spätere History-Freigabe vor Remote-Aktion und erneute Review danach; keine Agent/MCP-Tools. | Agent: Inputs/selection/trust, Work and outcomes, Remote-action gate, Report. Skill: Select/claim/resume/stop, Record an outcome, Verification and errors. |

## Technischer Abgleich der zehn Skills

| Skill | Erhaltener CLI-Vertrag |
|---|---|
| rulectl-author-cli | add-language/context/category, add, list/show/show-metagroups; gleiche info-/content-Korrekturen neuer Rules; Vorfahren vor Nachfahren; einmaliger Collision-Retry, sonst Itemfehler fortsetzen. |
| questctl-author-cli | list + show-metagroups bestimmen Tiefe; add-group/subgroup + add mit passenden Depth-Flags; gleiche Source/Description-Korrekturen; Tiefenkonflikt neu lesen/reconciliieren, nicht erzwingen. |
| taskctl-author-cli | add-phase/add; list/show/show-metagroups; Description/Review/Assignee/Source-Korrekturen; group-phase/reorder/delete; allgemeine Initialwert-Option genannt, im Author-Workflow nicht verwendet. Kein annotate/next/standalone set-status. |
| rulectl-checker-cli | rulectl tasklist-JSON als Snapshot inklusive Status/Review-Reset; taskctl claim/annotate/info-review/set-status/show; keine fremden IDs; Fehlclaim ohne weitere Bearbeitung, Itemfehler fortsetzen; finale Klassifikation aus echtem Store. |
| questctl-checker-cli | next-all einmal; offene Reihenfolge; sequential claim nach Match, Batch nur expliziter Scope; vor Prüfung show/Statuscheck; Answer nur nach Claim, User-Review vor R, kein Match offen bzw. B; Fehler-/Abbruch-/Endprüfregeln. |
| questctl-researcher-cli | Eigener vollständiger Vertrag ohne Checker-Skill-Abhängigkeit; gleiche Snapshot/Claim/Fehlermechanik, Annotation bei jedem Rechercheergebnis; Syntheseantwort und Thin-Evidence-Review. |
| specctl-author-cli | init/set-title/set-preamble, add aller fünf Ebenen, gleiche Add-Optionen, Content/rename/reorder/move/delete/list/show; IDs statt Signaturen beim Schreiben; Level-Skipping und Parent-Pfad/Levelwechsel bei move; keine Status-/ADR-Schreibrechte. |
| specctl-editor-cli | list/show; set-status nur stable, Content mit optionaler ADR, set-adr nur geprüfte IDs; kein Struktur-CRUD; fehlende/ungültige ADR unterscheiden; unvalidiertes/ungeloggtes set-adr und ignoriertes --adr auf Draft weiter benannt; ungefilterte Restverweise. |
| adrctl-author-cli | Domain/Component, accepted add, list/show/show-metagroups; info-spec-ref mit Single-Value/Propagation/Teilpersistenz; info-superseded-by + superseded nur nach erfolgreichem Ersatz ohne Restverweise; selektive Content-Korrektur; keine neuen Statusoperationen. |
| taskctl-worker-cli | next/show/history-Option, claim/annotate/info-review/set-status; zuletzt selektierte ID als Invariante; all_done normal, B/R/C stoppen; fehlgeschlagener Claim stoppt ohne weitere Mutation; Export-Blockierung als Ausnahme; bestehende Reviews nur auf expliziten User-Auftrag reduzieren. |

## Explizit erhaltene Prüf- und Fehlergrenzen

- Rule-/Question-Author: unmittelbare Verifikation des lokalen Repräsentanten
  UND separate finale Verifikation aller geglaubten Erstellungen. Fallback
  bleibt vor dem finalen Audit; keine eingesparten CLI-Aufrufe.
- Rule-Checker: initialer Exportfehler stoppt vor Task-Schreibzugriffen;
  nach Snapshot alle IDs besuchen, fehlgeschlagenen Claim nicht bearbeiten.
- Question-Checker/Researcher: einmalige Arbeitsmenge, jede ID höchstens einmal;
  offene unbeantwortete Fragen blockieren den weiteren Durchlauf nicht.
  Erfolgloser Claim erlaubt keine weitere Mutation. Ein Schreibfehler nach
  Claim versucht B; scheitert auch das, keine weiteren IDs bearbeiten.
- Task-Worker: fehlgeschlagener Claim erlaubt weder Annotation/Outcome noch
  Wechsel zum nächsten Task. Keine neuen automatischen Recovery-Versuche.
- ADR-Workflow: vorhandene Themenverifikation UND separate Endverifikation
  bleiben erhalten. Teilfehler berechtigen nicht zur Ablösung alter ADRs.
- Skill-Aufruf zu Laufbeginn, explizite Roots, Parser-/Exit-Konventionen,
  Allowlisten, unveränderte Tool-Berechtigungen und ausgeschlossene
  Operationen bleiben für jedes Paar erhalten.

## Prüfung und Grenzen

Der statische Vorher-nachher-Abgleich aller 19 Definitionen umfasst Namen,
Descriptions/Routing, Tools, Eingaben, Quellenumfang, Vertrauen, Reihenfolge,
Entscheidungen/Gates, Status, CLI-Fläche, Fehler, Verifikation und Berichte.
Dabei gefundene Auslassungen bei Verzeichnisabdeckung und Quellenfehlern
wurden wiederhergestellt; CLI-Add-Option und Workflow-Einschränkung werden
beide weiter genannt. Die bestehenden Design-Dokumente behalten ausführliche
Regeln und Begründungen. Die gemeinsame Runtime-Zuordnung ist inzwischen in
[den zentralen Designvorgaben](agent-skill-guidelines.md) beschrieben, statt
als wiederholter Abschnitt in jedem einzelnen Design.

Die bestehende CLI-/Plugin-Testsuite wurde erfolgreich ausgeführt: 555 Tests
mit `python3 -m unittest discover -s architecture/scripts/tests -t architecture/scripts`.
Namen und Tool-Berechtigungen aller 19 Definitionen, vorhandene Rollen-Skills,
Full-spec-Verweise und Dokumentlinks wurden zusätzlich statisch geprüft. Das ist
keine Modell-Evaluation: unveränderte Befolgung kompakterer Anweisungen lässt
sich daraus nicht beweisen. Weitere Architektur-/Regeländerungen und echte
Agent-Evals stehen im [Backlog](backlog-optimizing.md).

## Nachprüfung der Verständlichkeit auf optimization

Die anschließende Überarbeitung präzisiert Descriptions für alle neun Agents
und zehn Skills, ersetzt mehrdeutige Satzfragmente und ergänzt die Gründe für
kritische Regeln direkt in den Runtime-Definitionen. Der CLI-Vertrag bleibt in
Skills; Namen, Tool-Berechtigungen, Rollenpaare, Freigaben, Statusregeln und
Prüfzeitpunkte werden nicht geändert. Die Fehlerbehebungen aus e476614 bleiben
bestehen. Es wird keine zusätzliche gemeinsame Runtime-Datei geladen.

Die zusätzliche Implementierungssektion der Vision und die 19 wiederholten
Runtime-allocation-Blöcke sind entfernt. Workflow-Details bleiben in den Designs
und design-decisions; allgemeine Designvorgaben stehen zentral. Das Backlog
liegt nun neben diesem Dokument. Die historische Größenangabe oben belegt
keine Tokenersparnis und keine gleichwertige Modellbefolgung.

[Vergleichende Agent-Evals](evals/agent-instruction-comparison.md) sind vorbereitet,
aber nicht ausgeführt. Sie prüfen insbesondere Routing, tatsächliches Skill-Laden,
Fragenbearbeitung, Herkunft/Review, Remote-Freigaben und partielle ADR-Ablösung.
Weitere starke Kürzungen warten auf ausgewertete Läufe.

Validierung dieser Nachprüfung: alle 555 Tests der bestehenden Suite bestehen.
Namen, Tool-Berechtigungen und die CLI-Rezeptblöcke aller 19 Runtime-Dateien
wurden gegen 0034def unverändert geprüft. Die in den Skills genannten Flags
bleiben gleich; das bisherige „Never force“ des Rule-Checkers benennt nun
explizit das verbotene `--force`. Lokale Dokumentlinks wurden geprüft.
Diese statischen Ergebnisse sind keine ausgewerteten Agent-Evals.
