# Optimierungs-Backlog: Agents, Skills und Agent-Evals

Aufgeschobene Optimierungen an `architecture/agents/` und
`architecture/skills/` sowie die dafür nötige Validierung durch Agent-Evals.
Wann und wie ein Eintrag angegangen wird, regelt
[`CLAUDE.md`](CLAUDE.md), Abschnitt "Backlogs". Ein Eintrag ist keine
Freigabe zur Umsetzung.

Leitlinie für alle Einträge: Verständlichkeit hat Vorrang vor weniger
geladenen Tokens; Regeln werden nicht gestrichen oder abgeschwächt, nur um
Definitionen zu kürzen. Architekturentscheidungen, die ausdrücklich
aufgeschoben werden, kommen als neuer Eintrag hierher. Jede Änderung an
`agents/` oder `skills/` braucht eine neue `version` in
`.claude-plugin/plugin.json` (CI-Job `plugin-version`).

Weiterentwicklungen der CLI-Tools stehen in
[`backlog-features.md`](backlog-features.md).

## Potenzielle Regeländerungen

### B1: Verifikationsaufrufe reduzieren

- **Auslöser**: Die Verifikationsschritte von `rulectl-author` oder
  `questctl-author` (bzw. `rulectl-author-cli`/`questctl-author-cli`) werden
  ohnehin geändert, oder ein Optimierungslauf will dort Aufrufe einsparen.
- **Nutzen**: Weniger CLI-Aufrufe und kürzere Läufe der Author-Agents.
- **Aufwand**: mittel — Änderung des Prüfvertrags, setzt Fehler- und
  Nebenläufigkeitsszenarien aus B4 voraus.
- **Kontext und Quellen**:
  - Heute werden Duplikat-Repräsentanten unmittelbar nach dem Erstellen und
    erneut am Laufende gelesen; im bisherigen Optimierungslauf wurden beide
    Prüfzeitpunkte bewusst erhalten.
  - Aufgeschoben, weil das Entfernen eines Prüfschritts die
    Ausführungssemantik ändert.
  - `agents/rulectl-author.md`, `agents/questctl-author.md`, ihre Skills und
    Design-Dokumente unter `docs/subagents/` und `docs/skills/`.
- **Offene Designfragen**:
  1. Welcher Prüfzeitpunkt ist verzichtbar, ohne unzutreffende
     Duplikatzuordnungen oder nachträglich verschwundene Objekte zu
     übersehen? — Empfehlung: offen; erst nach den B4-Szenarien zu
     Duplikat-Fallback und Schreibfehlern entscheiden.
- **Vorgehen**:
  1. Fehler- und Nebenläufigkeitsszenarien festlegen (ggf. B4 zuerst).
  2. Geänderten Prüfvertrag mit dem User entscheiden; Design-Dokumente
     anpassen, dann Agent- und Skill-Dateien.
  3. Betroffene Eval-Szenarien in beiden Fassungen laufen lassen.
- **Fertig, wenn**: Der neue Prüfvertrag ist in Design und Runtime-Text
  konsistent beschrieben, die Evals zeigen keine Regression gegenüber der
  bisherigen Fassung, die Testsuite ist grün.
- **Abschluss**: siehe [`CLAUDE.md`](CLAUDE.md), "Backlogs"; Plugin-Version
  erhöhen.

### B2: Fachliche Vereinfachungen getrennt bewerten

- **Auslöser**: Bei einer redaktionellen Prüfung oder einem
  Optimierungslauf von Agent-/Skill-Definitionen fällt eine konkrete
  fachliche Vereinfachung auf (Freigaben, Wiederaufnahme,
  Duplikatbehandlung, Fehlerfortsetzung, Berichtspflichten).
- **Nutzen**: Einfachere Rollenverträge, wo die heutige Regel mehr leistet
  als nötig.
- **Aufwand**: klein für das Erfassen; die Umsetzung hängt vom einzelnen
  Fund ab.
- **Kontext und Quellen**:
  - Sammelauftrag, keine Empfehlung für eine bestimmte Regeländerung.
  - Im bisherigen Optimierungslauf wurden Regeln weder gestrichen noch
    abgeschwächt.
- **Vorgehen**:
  1. Den konkreten Fund mit Beleg (Datei, Regel) und Auswirkung als eigenen
     neuen Eintrag `B<n>` in diesem Backlog anlegen — nicht direkt umsetzen.
  2. Der neue Eintrag folgt danach den normalen Backlog-Regeln.
- **Fertig, wenn**: B2 bleibt als Daueraufgabe bestehen; es gibt keinen
  Abschluss.
- **Abschluss**: entfällt.

## Aufgeschobene Architektur- und Validierungsarbeit

### B3: Gemeinsame Runtime-Referenzen untersuchen

- **Auslöser**: Eine CLI-Änderung erfordert, denselben Kontrakttext in drei
  oder mehr Skills nachzuziehen, oder ein neues Agent-Skill-Paar wird
  angelegt.
- **Nutzen**: Möglicherweise weniger Pflegeaufwand und geladene Tokens durch
  einen gemeinsamen CLI-Kern.
- **Aufwand**: groß — neuer Lademechanismus, Berechtigungsprüfung und
  Messung.
- **Kontext und Quellen**:
  - Heute sind alle Agent-Skill-Paare eigenständig. Author und Worker werden
    üblicherweise getrennt genutzt; eine Rolle darf keinen Skill einer
    anderen Rolle laden müssen, um ihren Vertrag zu kennen.
  - Die bestehenden `Full spec: architecture/docs/...`-Pfade sind laut
    `docs/scripts/design-decisions.md` Entwicklerhinweise, keine
    verlässlichen Runtime-Referenzen für installierte Plugins.
  - `docs/agent-skill-guidelines.md`.
- **Offene Designfragen**:
  1. Spart ein gemeinsamer CLI-Kern tatsächlich Tokens und Pflegeaufwand
     gegenüber kompakten, eigenständigen Skills? — Empfehlung: erst messen,
     dann entscheiden; ohne messbaren Vorteil eigenständig bleiben.
- **Vorgehen**:
  1. Einen expliziten, installationsunabhängigen Ladeweg definieren.
  2. Tool-Berechtigungen prüfen.
  3. Ladeaufwand für beide Varianten messen; Ergebnis mit dem User
     entscheiden.
- **Fertig, wenn**: Entscheidung mit Messung dokumentiert; bei Umsetzung
  zusätzlich Evals ohne Regression und grüne Testsuite.
- **Abschluss**: siehe [`CLAUDE.md`](CLAUDE.md), "Backlogs".

### B4: Fehlerfall-Szenarien für die Agent-Evals ergänzen

- **Auslöser**: Bevor Agent- oder Skill-Definitionen das nächste Mal
  substanziell gekürzt oder umgeschrieben werden; oder bevor B1, B6 oder B7
  umgesetzt wird.
- **Nutzen**: Belegt, dass Agents auch in Fehlerfällen unverändert handeln —
  die bisherigen Evals decken nur reguläre Abläufe ab.
- **Aufwand**: mittel bis groß — Fixtures und Erwartungen je Szenario, dazu
  echte Claude-Code-Läufe (verursachen API-Kosten).
- **Kontext und Quellen**:
  - Eval-Plan: [`evals/agent-instruction-comparison.md`](evals/agent-instruction-comparison.md)
    (E1–E6, "Auswertung und Freigabe"); Ergebnisse:
    [`evals/results-2026-10-20.md`](evals/results-2026-10-20.md) —
    E1 und E3–E6 ausgeführt, ohne beobachtete Regression; E2 über die
    E1-Fixtures abgedeckt.
  - Harness (im Repo-Root, nicht unter `docs/`): `evals/agent_evals.py`
    (Fixtures `fx_<szenario>`, Befehle `run` und `report`), Tests in
    `evals/test_agent_evals.py`, Rohdaten unter `evals/results/`.
  - Statische Validierung (Regelabgleich, CLI-Testsuite) belegt keine
    unveränderte Befolgung der Anweisungen durch ein Modell.
  - Offene Szenarien: unbeantwortete erste Frage mit beantwortbarer
    Folgefrage; Fehler beim Claim oder Schreiben; fehlende
    Taxonomie-Freigabe; fehlgeschlagener Duplikat-Repräsentant (B6);
    teilweise ersetzte ADR; verpflichtende User-Review; gewöhnliche
    Agent-Aufgabe gegenüber markiertem rulectl-Export.
- **Vorgehen**:
  1. Je Szenario reproduzierbare Eingaben, Modell- und Tool-Konfiguration,
     erwartete Aktionen, Abbruchbedingungen und Bewertung festlegen und im
     Eval-Plan als E7 ff. ergänzen.
  2. Fixtures in `evals/agent_evals.py` ergänzen, Harness-Tests erweitern.
  3. Author- und Worker-Rollen jeweils separat ausführen; Läufe gegen die
     aktuelle Fassung durchführen und auswerten.
  4. Ergebnisse als neues `docs/evals/results-<datum>.md` dokumentieren,
     Rohdaten unter `evals/results/<datum>/` (Repo-Root).
- **Fertig, wenn**: Alle offenen Szenarien sind im Plan beschrieben,
  implementiert, ausgeführt und ausgewertet; Regressionen sind behoben oder
  als eigene Einträge erfasst; `evals/test_agent_evals.py` ist grün.
- **Abschluss**: siehe [`CLAUDE.md`](CLAUDE.md), "Backlogs"; Verweise auf B4
  in `evals/agent-instruction-comparison.md` und `agent-skill-guidelines.md`
  nachziehen.

## Konkrete Funde aus dem Regelabgleich

### B6: Ergebniszuordnung nach fehlgeschlagenem Duplikat-Repräsentanten

- **Auslöser**: Die Duplikatbehandlung von `rulectl-author` oder
  `questctl-author` wird geändert, oder das zugehörige B4-Szenario wird
  gebaut.
- **Nutzen**: Eindeutiger Bericht, wenn ein erster Kandidat scheitert und
  ein späterer Vertreter derselben Duplikatgruppe gespeichert wird.
- **Aufwand**: klein bis mittel — Vertragstext in zwei Agents/Skills plus
  Eval-Szenario.
- **Kontext und Quellen**:
  - Der bisherige Vertrag beschreibt den Fallback und verlangt genau ein
    Ergebnis pro Kandidat, legt aber die Ergebniszuordnung für den zuerst
    fehlgeschlagenen Kandidaten nach erfolgreichem Fallback nicht
    vollständig fest.
  - Im bisherigen Lauf wurde bewusst keine neue Zuordnung erfunden.
- **Offene Designfragen**:
  1. Wie werden Versuchshistorie und abschließende Duplikatrepräsentation
     berichtet? — Empfehlung: der fehlgeschlagene Kandidat erhält sein
     eigenes Fehlerergebnis und verweist auf den erfolgreichen Vertreter;
     endgültig erst mit dem User entscheiden.
- **Vorgehen**:
  1. Designfrage mit dem User klären; Design-Dokumente anpassen.
  2. Agent- und Skill-Text nachziehen.
  3. Szenario im Agent-Eval ergänzen (siehe B4) und ausführen.
- **Fertig, wenn**: Die Zuordnung ist in Design und Runtime-Text
  festgelegt, das Eval-Szenario bestätigt sie, die Testsuite ist grün.
- **Abschluss**: siehe [`CLAUDE.md`](CLAUDE.md), "Backlogs"; Plugin-Version
  erhöhen; Szenario-Hinweis in B4 entfernen.

### B7: Recovery des Workers bei fehlgeschlagenen Review-Schreibschritten

- **Auslöser**: Die Review- oder History-Schritte von `taskctl-worker`
  werden geändert, oder ein fehlgeschlagener Review-Schreibschritt wird in
  einem echten Lauf beobachtet.
- **Nutzen**: Wiederaufnahme ohne doppelte Ausführung externer Aktionen.
- **Aufwand**: mittel — Fehlerfälle unterscheiden, Wiederaufnahmeregeln
  definieren, Eval-Szenarien.
- **Kontext und Quellen**:
  - `taskctl-worker` bewahrt die bisherige History-Freigabe und meldet
    Schreibfehler; eine vollständige Recovery-Strategie für
    fehlgeschlagene Pending-/Ergebnis-Reviews ist nicht spezifiziert.
  - Im bisherigen Lauf wurden keine neuen Retries eingeführt.
  - `agents/taskctl-worker.md`, `docs/subagents/design-taskctl-worker.md`,
    `skills/taskctl-worker-cli/`; `design-decisions.md`, "Amendments
    (2026-10-19, local-first: one gated path for remote actions)".
- **Offene Designfragen**:
  1. Wie wird nach einem Fehler vor bzw. nach einer genehmigten externen
     Aktion wieder aufgenommen? — Empfehlung: Fehler vor der Aktion →
     Review-Schritt wiederholen; Fehler nach der Aktion → nie erneut
     ausführen, sondern als Blocker mit Hinweis an den User melden.
- **Vorgehen**:
  1. Fehlerfälle vor und nach einer genehmigten externen Aktion
     unterscheiden und Regeln mit dem User entscheiden.
  2. Design-Dokument, dann Agent- und Skill-Text anpassen.
  3. Fehlerszenarien im Agent-Eval ergänzen (siehe B4) und ausführen.
- **Fertig, wenn**: Recovery-Regeln sind spezifiziert, umgesetzt und durch
  Evals belegt; die Testsuite ist grün.
- **Abschluss**: siehe [`CLAUDE.md`](CLAUDE.md), "Backlogs"; Plugin-Version
  erhöhen.

### B8: Rollenwahl bei Stores mit rulectl-Exporten

- **Auslöser**: Die Description von `rulectl-checker` oder der Bericht von
  `taskctl-worker` wird geändert, oder E6 wird erneut ausgeführt.
- **Nutzen**: Bei „Arbeite die offenen Tasks ab“ startet der eigentliche
  Prüflauf, statt dass der Worker den Export nur blockiert.
- **Aufwand**: klein — Description- oder Berichtstext, dann E6 wiederholen.
- **Kontext und Quellen**:
  - Eval E6: Bei „Arbeite die offenen Tasks in <root> ab“ wählt der
    Aufrufer in beiden Fassungen meist `taskctl-worker` (je 2/3 Läufe). Der
    Worker blockiert den Export korrekt, aber der Prüflauf unterbleibt.
  - Der Auftrag verrät nicht, dass der Store Prüf-Tasks enthält; die Rolle
    ist nur durch Inspektion des Stores erkennbar.
  - [`evals/results-2026-10-20.md`](evals/results-2026-10-20.md), "E6 im
    Einzelnen".
- **Offene Designfragen**:
  1. Soll die Description von `rulectl-checker` Auslöser wie „exportierte
     Prüf-Tasks abarbeiten“ nennen, oder soll der Worker-Bericht den
     Aufrufer ausdrücklich zum Start von `rulectl-checker` auffordern? —
     Empfehlung: beides prüfen, zuerst die Berichtsaufforderung, da sie die
     Rollenwahl nicht verschiebt; endgültig mit dem User entscheiden.
- **Vorgehen**:
  1. Designfrage mit dem User klären; Design-Dokumente anpassen.
  2. Agent-Text ändern.
  3. E6 in beiden Fassungen wiederholen und auswerten.
- **Fertig, wenn**: E6 zeigt, dass der Prüflauf zustande kommt, ohne
  Regression in E1; die Testsuite ist grün.
- **Abschluss**: siehe [`CLAUDE.md`](CLAUDE.md), "Backlogs"; Plugin-Version
  erhöhen.
