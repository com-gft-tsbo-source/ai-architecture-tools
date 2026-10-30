# docs/ — Design-Dokumente und Backlogs

Design-Dokumente sind maßgeblich, nicht die Implementierung (siehe
Root-`CLAUDE.md`). Dieser Abschnitt regelt zusätzlich die Backlogs.

## Backlogs

Gilt für jede Datei `architecture/docs/backlog-*.md`, derzeit:

- `backlog-features.md` — Weiterentwicklung der CLI-Tools (`F<n>`).
- `backlog-optimizing.md` — Agent-/Skill-Optimierungen und Agent-Evals
  (`B<n>`); noch nicht auf das Eintragsformat unten umgestellt.

Ein Backlog-Eintrag ist **keine Freigabe zur Umsetzung**.

### Wann ein Eintrag angesprochen wird

- Nur wenn sein **Auslöser** in der laufenden Arbeit inhaltlich greift.
  Ein Eintrag ohne Auslöser wird nie von sich aus angesprochen.
- Sessionstart, Aufräumarbeiten oder "es passt gerade" sind kein Auslöser.

### Vor jeder Planung oder Umsetzung: den User fragen

Greift ein Auslöser, **zuerst fragen, dann erst handeln**:

- Gefragt wird nur nach dem betroffenen Eintrag, mit ID, Titel, einem Satz
  Nutzen und einem Satz Aufwand aus dem Eintrag — so, dass der User ohne
  Nachlesen entscheiden kann. Greifen mehrere Auslöser gleichzeitig, jeden
  Eintrag einzeln aufführen.
- Bis zur Antwort für diesen Eintrag **nichts** tun: keine gezielte
  Recherche oder Exploration, kein Plan-Mode, keine Task-Datei, keine
  Code- oder Doku-Änderung. Erlaubt ist nur, zu erkennen, dass der Auslöser
  greift. Die eigentliche Aufgabe der Session läuft unabhängig davon weiter.
- Ein **ausdrücklicher Auftrag** des Users, einen Eintrag umzusetzen
  ("setz F1 um"), gilt als Zustimmung — dann nicht erneut fragen.

### Ablehnung gilt für die laufende Session

- Ein "Nein" gilt **pro Eintrag** und **bis zum Ende der aktuellen Session**:
  denselben Eintrag in dieser Session nicht erneut ansprechen, auch wenn
  sein Auslöser wieder greift. Andere Einträge bleiben davon unberührt.
- Die Ablehnung wird **nicht gespeichert** — keine Datei, kein Memory, kein
  Backlog-Vermerk. Eine neue Session fragt wieder.
- Wird der Kontext zusammengefasst, die abgelehnten Eintrags-IDs
  ausdrücklich in die Zusammenfassung übernehmen, damit nach der
  Kompaktierung nicht erneut gefragt wird.

### Umsetzung und Abschluss

- Vorgehen und Abnahmekriterien stehen im Eintrag ("Vorgehen",
  "Fertig, wenn"); offene Designfragen eines Eintrags vor der
  Implementierung mit dem User klären und zuerst das Design-Dokument
  anpassen.
- Konventionen aus `architecture/scripts/CLAUDE.md` gelten unverändert
  (Tests, `lib/`-Wiederverwendung, Plugin-Version bei Änderungen an
  `agents/`, `skills/`, `bin/`).
- Nach Abschluss: Umsetzung als Amendment in
  `docs/scripts/design-decisions.md` dokumentieren (inkl. Zeile im
  "Amendment index"), den Eintrag aus dem Backlog **löschen** und alle im
  Eintrag unter "Abschluss" genannten Stellen nachziehen. Ein leerer
  Backlog bleibt mit dem Hinweis "Keine offenen Punkte." bestehen.
- Teilweise umgesetzt oder abgebrochen: den Eintrag auf den Reststand
  aktualisieren statt ihn zu löschen.

### Eintragsformat

```markdown
## <ID>: <Titel>

- **Auslöser**: wann der Eintrag ansteht (konkreter Bedarf oder Arbeit an
  benannten Dateien/Funktionen)
- **Nutzen**: ein Satz
- **Aufwand**: klein / mittel / groß, mit einem Satz Begründung
- **Kontext und Quellen**: maßgebliche Design-Abschnitte, Code-Stellen,
  Seiteneffekte
- **Offene Designfragen** (optional): je Frage eine Empfehlung, keine
  Festlegung
- **Vorgehen**: nummerierte Schritte
- **Fertig, wenn**: prüfbare Abnahmekriterien
- **Abschluss**: was nach der Umsetzung zusätzlich nachzuziehen ist
```

IDs werden nie wiederverwendet; das Präfix ist je Backlog fest
(`F` = Features, `B` = Optimierung).
