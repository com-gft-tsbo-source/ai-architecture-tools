# Aufgeschobene Optimierungen für Agents und Skills

Dieses Backlog sammelt Kandidaten für einen späteren Optimierungslauf.
Ein Eintrag ist keine Freigabe zur Umsetzung. Im aktuellen Lauf bleibt das
Verhalten erhalten; Verständlichkeit hat Vorrang vor weniger geladenen Tokens.
Architekturentscheidungen aus der laufenden Klärung werden hier ergänzt,
wenn sie ausdrücklich aufgeschoben werden.

## Potenzielle Regeländerungen

### B1: Verifikationsaufrufe reduzieren

- Betroffen: `rulectl-author` und `questctl-author` sowie ihre CLI-Skills.
- Heute: Duplikat-Repräsentanten werden unmittelbar nach dem Erstellen und
  erneut am Laufende gelesen.
- Später prüfen: Lassen sich Aufrufe einsparen, ohne unzutreffende
  Duplikatzuordnungen oder nachträglich verschwundene Objekte zu übersehen?
- Aufgeschoben, weil das Entfernen eines Prüfschritts die Ausführungssemantik
  ändert. Im aktuellen Lauf werden beide Prüfzeitpunkte erhalten.
- Vor Umsetzung nötig: Fehler- und Nebenläufigkeitsszenarien festlegen und
  den geänderten Prüfvertrag ausdrücklich entscheiden.

### B2: Fachliche Vereinfachungen getrennt bewerten

- Kandidaten: Freigaben, Wiederaufnahme, Duplikatbehandlung, Fehlerfortsetzung
  und Berichtspflichten, soweit sich bei der redaktionellen Prüfung konkrete
  Vereinfachungen ergeben.
- Dies ist ein Sammelauftrag, noch keine Empfehlung für eine bestimmte
  Regeländerung. Konkrete Funde erhalten eigene Einträge mit Beleg und
  Auswirkungen.
- Im aktuellen Lauf werden Regeln weder gestrichen noch abgeschwächt,
  um kürzere Definitionen zu erreichen.

## Aufgeschobene Architektur- und Validierungsarbeit

### B3: Gemeinsame Runtime-Referenzen untersuchen

- Im aktuellen Lauf bleiben alle vorhandenen Agent-Skill-Paare eigenständig.
  Author und Worker werden üblicherweise getrennt genutzt; eine Rolle darf
  keinen Skill einer anderen Rolle laden müssen, um ihren Vertrag zu kennen.
- Später prüfen: Spart ein gemeinsamer CLI-Kern tatsächlich geladene Tokens
  und Pflegeaufwand gegenüber kompakten, eigenständigen Skills?
- Vor Umsetzung nötig: einen expliziten, installationsunabhängigen Ladeweg
  definieren, Tool-Berechtigungen prüfen und Ladeaufwand messen.
- Die bestehenden `Full spec: architecture/docs/...`-Pfade sind laut
  `architecture/docs/scripts/design-decisions.md` Entwicklerhinweise, keine
  verlässlichen Runtime-Referenzen für installierte Plugins.

### B4: Tatsächliche Agent-Läufe vor und nach Kürzungen vergleichen

- Vor weiteren starken Kürzungen erforderlich: vergleichende echte Agent-Läufe.
  [Der vorbereitete Eval-Plan](evals/agent-instruction-comparison.md) enthält
  feste Eingaben, getrennte Routing-/Workflow-Prüfungen und Auswertungskriterien.
  E1 und E3–E6 sind ausgeführt, ohne beobachtete Regression
  ([Ergebnisse](evals/results-2026-10-20.md)). Offen: die Fehlerfälle unten.
- Aktuelle Validierung: dokumentierter Abgleich der bisherigen Regeln gegen
  die kompakten Definitionen sowie die bestehende Testsuite. Das belegt keine
  unveränderte Befolgung der Anweisungen durch ein Modell.
- Spätere Szenarien: unbeantwortete erste Frage mit beantwortbarer Folgefrage;
  Fehler beim Claim oder Schreiben; fehlende Taxonomie-Freigabe; fehlgeschlagener
  Duplikat-Repräsentant; teilweise ersetzte ADR; verpflichtende User-Review;
  gewöhnliche Agent-Aufgabe gegenüber markiertem rulectl-Export.
- Vor Umsetzung nötig: reproduzierbare Eingaben, Modell- und Tool-Konfiguration,
  erwartete Aktionen und Abbruchbedingungen sowie Bewertung der Ergebnisse
  festlegen. Author- und Worker-Rollen jeweils separat ausführen.

## Konkrete Funde aus dem Regelabgleich

### B5: Allgemeine CLI-Fläche und Rollenvertrag deutlicher abgrenzen

- `taskctl-author-cli` beschreibt initiales `--set-status` für Imports,
  während der zugehörige Author neu geplante Tasks immer offen lässt.
  `specctl-author-cli` nennt den verfügbaren Add-Parameter ebenfalls,
  verlangt im Draft-Workflow aber ausdrücklich, ihn nicht zu verwenden.
- Beide bisherigen Einschränkungen bleiben erhalten. Später entscheiden,
  ob rollenspezifische Skills solche ungenutzten CLI-Varianten überhaupt
  beschreiben sollen oder ob Imports einen eigenen Vertrag brauchen.

### B6: Ergebniszuordnung nach fehlgeschlagenem Duplikat-Repräsentanten

- Bei `rulectl-author` und `questctl-author` kann ein erster Kandidat beim
  Erstellen scheitern, während ein späterer Vertreter derselben lokalen
  Duplikatgruppe erfolgreich gespeichert wird.
- Der bisherige Vertrag beschreibt den Fallback und verlangt genau ein
  Ergebnis pro Kandidat, legt aber die Ergebniszuordnung für den zuerst
  fehlgeschlagenen Kandidaten nach erfolgreichem Fallback nicht vollständig fest.
- Im aktuellen Lauf keine neue Zuordnung erfinden. Später entscheiden,
  wie Versuchshistorie und abschließende Duplikatrepräsentation berichtet
  werden; im Agent-Eval ein entsprechendes Szenario aufnehmen.

### B7: Recovery des Workers bei fehlgeschlagenen Review-Schreibschritten

- `taskctl-worker` bewahrt die bisherige History-Freigabe und meldet
  Schreibfehler. Eine vollständige Recovery-Strategie für fehlgeschlagene
  Pending-/Ergebnis-Reviews ist bislang nicht spezifiziert.
- Später Fehlerfälle vor und nach einer genehmigten externen Aktion
  unterscheiden und Regeln für Wiederaufnahme ohne doppelte Ausführung
  definieren. Im aktuellen Lauf werden keine neuen Retries eingeführt.

### B8: Rollenwahl bei Stores mit rulectl-Exporten

- Eval E6: Bei „Arbeite die offenen Tasks in <root> ab“ wählt der Aufrufer
  in beiden Fassungen meist `taskctl-worker` (je 2/3 Läufe). Der Worker
  blockiert den Export korrekt, aber der eigentliche Prüflauf unterbleibt.
- Der Auftrag verrät nicht, dass der Store Prüf-Tasks enthält; die Rolle ist
  nur durch Inspektion des Stores erkennbar.
- Später entscheiden, ob die Description von `rulectl-checker` Auslöser wie
  „exportierte Prüf-Tasks abarbeiten“ nennen soll oder ob der Worker-Bericht
  den Aufrufer ausdrücklich zum Start von `rulectl-checker` auffordert.
  Danach E6 wiederholen.
