# Agent- und Skill-Definitionen pflegen

Diese Designvorgaben gelten für die Entwicklung der Definitionen. Sie sind
keine zusätzliche Runtime-Datei, die ein installierter Agent laden muss.
Die fachlichen Verträge stehen weiterhin in `subagents/design-*.md`, die
CLI-Verträge in `skills/design-*-cli.md`. Der
[Regelabgleich](optimizing-rule-comparison.md) ordnet die einzelnen Regeln zu.

## Verantwortung und eigenständige Rollen

Ein Agent enthält seine Eingaben, Vertrauensgrenzen, fachliche Reihenfolge,
Entscheidungen, Freigaben und Berichtsanforderungen. Der zugehörige Skill
enthält den vollständigen CLI-Vertrag: erlaubte Operationen, Syntax, technische
Statusübergänge, Fehlerbehandlung und Store-Verifikation.

Jede Rolle lädt zu Laufbeginn ihre ausdrücklich benannten Skills, bevor sie
eine CLI aufruft. Author und Worker werden separat eingesetzt und benötigen
nicht die Anweisungen der anderen Rolle. `specctl-adr-author` verwendet wie
bisher zwei Skills. CLI-Rezepte bleiben in Skills; zentrale Grenzen dürfen im
Agent wiederholt werden. Unbekannte CLI-Operationen sind Skill-Lücken und keine
Erlaubnis, eigene Aufrufe zu erfinden.

## Verständlichkeit und Auswahl

Descriptions nennen konkrete Einsatzfälle und die nächstliegenden Rollen,
für die sie nicht zuständig sind. Sie dienen der Auswahl durch den Aufrufer;
Änderungen daran können das Routing beeinflussen, auch wenn der Body dieselben
Regeln enthält. Eine bestimmte Formulierung garantiert kein korrektes Routing.

Schreibe vollständige Sätze, wenn Fragmente offenlassen, wer handelt, wann ein
Schritt erfolgt oder ob ein Fehler den Task, das Thema oder den Lauf beendet.
Listen und Tabellen sind für echte Alternativen und Zustandszuordnungen geeignet.
Eine Kürzungsquote hat keinen Vorrang vor eindeutigen Anweisungen.

Entscheidungsrelevante Begründungen stehen auch in der Runtime-Definition:
insbesondere bei ungewöhnlichen Claim-Zeitpunkten, Vertrauensgrenzen,
Freigaben, mehrfachen Prüfungen und nichttransaktionalen Änderungen. Sie sollen
den Geltungsbereich der bestehenden Regel erklären, keine Ausnahmen schaffen.
Ausführliche Historie, Alternativen und Zukunftsplanung bleiben in den Designs.

## Änderungen prüfen

Ein statischer Regelabgleich prüft Eingaben, Reihenfolge, Freigaben,
CLI-Fläche, Fehlerfolgen, Verifikation und Berichte. Die vorhandene Testsuite
prüft CLI- und Store-Verhalten. Beides beweist keine unveränderte Befolgung der
Anweisungen durch ein Modell und keine unveränderte automatische Rollenauswahl.

Vor weiteren starken Kürzungen werden vergleichende Agent-Läufe nach dem
[Eval-Plan](evals/agent-instruction-comparison.md) durchgeführt. Verglichen
werden Rollenwahl, tatsächliches Skill-Laden, Aktionen und Stopps sowie der
resultierende Store. Ergebnisse werden mit Modell, Konfiguration und vollständigen
Traces protokolliert. Wortzahlen bleiben eine Größenangabe; sie sind weder eine
Tokenmessung noch ein Qualitätsnachweis.

Aufgeschobene Regeländerungen und offene Validierung stehen im
[Backlog](backlog-optimizing.md). Zusätzliche gemeinsame Runtime-Referenzen sind
weiterhin aufgeschoben; diese Seite führt keinen neuen Lademechanismus ein.
