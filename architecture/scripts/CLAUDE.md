# scripts/ — Python-CLI-Tools (taskctl.py, questctl.py, rulectl.py, adrctl.py, specctl.py)

Agentische CLI-Tools für Taskmanagement (`taskctl.py`), offene Fragen
(`questctl.py`), Code-Qualitäts-Regeln (`rulectl.py`), Architecture Decision
Records (`adrctl.py`) und Spezifikationsdokumente (`specctl.py`). Objektmodell,
Dateiformat und CLI-Kontrakt sind spezifiziert in:

- `architecture/docs/scripts/design.md` — allgemeines Objektmodell, CLI-Kontrakt,
  Locking, Index-Dateien (gilt für alle fünf Tools als Basis; specctl weicht an
  mehreren dort explizit vermerkten Stellen ab).
- `architecture/docs/scripts/design-taskctl.md`, `design-questctl.md`,
  `design-rulectl.md`, `design-adrctl.md`, `design-specctl.md` —
  tool-spezifische Ergänzungen.

Bei Widersprüchen zwischen vorhandenem Code und diesen Dokumenten sind die
Design-Dokumente maßgeblich — nicht der Code.

## Aktueller Implementierungsstand

Kernmodell, Locking, Index-Dateien, Reorder sowie `taskctl.py`, `rulectl.py`,
`adrctl.py` sind implementiert und laufen End-to-End — sowohl Directory-Mode
als auch Single-File-Mode. `reindex` baut `.index.json` neu und erkennt/behebt
Inkonsistenzen aktiv (verwaiste `.tmp`-Dateien werden entfernt, doppelte
Nummern innerhalb einer Metagroup werden gemeldet). `add-<metagroup-type>`
vergibt die Sortnummer automatisch (`max+1`), wenn keine explizit angegeben
wird; `add --<metagroup-type>` akzeptiert zur Referenz auf existierende Pfade
pro Segment Nummer, Name oder `Nummer-Name` (spezifiziert in `design.md`, CLI
Contract; Begründung in `design-decisions.md`, Abschnitt "Amendments").

**`--root` ist projektweit gemeinsam** (`design.md`, "File and Directory
Parameters"; `design-decisions.md`, "Amendments (2026-08-19, shared-root
resolution)"): alle vier Tools nehmen denselben `--root`-Pfad entgegen und
lösen ihn über `lib/store.py`s `resolve_root(given_path, name, default_mode)`
zu ihrem eigenen `<name>.md`/`<name>` innerhalb des gemeinsamen Verzeichnisses
auf (`ToolSpec.root_name`/`default_mode`: `tasks`/Directory, `rules`/Directory,
`adrs`/Directory, `spec`/Single-File). Das macht `adrctl`s künftige
`spec-ref`-Verknüpfung zu `specctl` eindeutig auflösbar, ohne einen separat
konfigurierten Pfad. Multi-Root Read-Only-Merge (`--root` mehrfach) ist dafür
ersatzlos entfallen — kein Tool hatte dafür einen echten Anwendungsfall.
`lib/spec_store.py` nutzt `resolve_root` identisch (`_ROOT_NAME = "spec"`).

`specctl.py` ist implementiert (`init`, `set-title`, `set-preamble`, Add je
Ebene, Status inkl. ADR-Pflicht ab `stable`, `set-adr`, `set-description`,
`rename`, `reorder`, `move-to-<Ebene>`, `delete`, `show`, `list`, `history`,
`render`) — **sowohl Single-File- als auch Directory-Mode**
(`design-specctl.md`, "Object Format"). Es nutzt bewusst *nicht*
`lib/cliapp.py` und `lib/objectfile.py`/`lib/singlefile.py`/`lib/store.py`:
deren generisches Objektformat (Signature-Heading, `## Meta`-Bulletliste,
`> `-Zitatblöcke, Metagroup getrennt vom Objekt) passt nicht zu specctls
leichtgewichtigem Format und kollabiertem Metagroup-=-Objekt-Modell —
eigene Module `lib/spec_model.py`, `lib/spec_comment.py`,
`lib/spec_document.py`, `lib/spec_store.py`, `lib/spec_render.py`.
Wiederverwendet werden die tatsächlich generischen Bausteine:
`lib/locking.py`, `lib/atomicio.py`, `lib/clock.py`, `lib/numbering.py`,
`lib/history.py`, `lib/text.py` (`escape_signature_text`, `slugify` —
Letzteres seit specctl auch von `lib/store.py` genutzt statt eines eigenen
privaten Duplikats), `lib/metagroup.py` (`resolve_segment`,
`assign_leaf_name`) sowie `lib/store.py`s `resolve_root` (siehe oben) und
`lib/abbrev.py`, das dafür um die 4-/5-Ebenen-Breiten aus `design-specctl.md`
("Object Type") generalisiert wurde, ohne das Verhalten für die anderen drei
Tools zu ändern (deren Breiten summierten schon vorher zu 6).

specctls Directory-Mode weicht vom allgemeinen Modell ab: **jede Section ist
ein Verzeichnis** (`<nr>-<type>-<id>-<slug>/`, nicht nur Blätter), mit einer
`_content.md` für Heading+Kommentar+Description; kein `.index.md`/
`.index.json` (das Object Type steckt bereits pro Section in `_content.md`,
ein Index wäre reine Duplikation); die Dokument-Präambel liegt optional in
`_preamble.md` im Wurzelverzeichnis. Ein Schreibvorgang leert und baut den
gesamten Baum aus der In-Memory-Liste neu auf (wie das komplette Neu-Schreiben
der Datei im Single-File-Mode) — nicht atomar über mehrere Dateien hinweg,
dieselbe bereits im allgemeinen Modell akzeptierte Einschränkung bei einer
unterbrochenen Reorder-Kaskade. Beide Modi konvertieren in dieselbe flache,
präorder `list[SpecSection]`-Repräsentation, sodass sämtliche CRUD-Methoden
(`add`, `set_status`, `rename`, `reorder`, `move`, ...) modusunabhängig
bleiben — nur `_read`/`_write` verzweigen.

`move-to-<metagroup-type>` (das allgemeine Modell nennt es
`group-<metagroup-type>`, design.md: "Changing an object's metagroup ...
re-derives everything downstream") verschiebt eine Section zu einem neuen
Elternpfad — bei specctl trifft das den **gesamten verschobenen Teilbaum**,
nicht nur die Section selbst: jedes Nachkommen-Object-Type wird aus seinem
eigenen vollständigen Vorfahren-Namenspfad abgeleitet, der sich durch die
Verschiebung ändert, muss also neu abgeleitet werden (nicht nur gepatcht wie
bei `rename`/`reorder`). Abgelehnt werden Verschiebungen in den eigenen
Teilbaum (Zyklus), zum aktuellen Elternpfad (No-op, `reorder` verwenden) und
solche, die für die Section selbst oder einen Nachkommen die 5-Ebenen-Grenze
überschreiten würden.

Ein Spec-vs-Implementierung-Abgleich (2026-08-19) deckte mehrere in
`design.md` bereits dokumentierte, aber nie verdrahtete Operationen auf; die
folgenden wurden daraufhin nachgezogen (`design-decisions.md`, "Amendments
(2026-08-19, closing spec/implementation gaps)"):
- **`delete <id>`** bei allen vier Tools. Bei taskctl/rulectl/adrctl eine
  einfache Entfernung (Objekt ist immer Metagroup-Blatt, keine Kinder
  möglich); bei specctl lehnt `delete` eine Section mit Kind-Sections ab,
  außer `--force-delete` löscht den gesamten Teilbaum. Hinterlässt wie jede
  Löschung eine dauerhafte Nummernlücke, wird nirgends nachträglich geloggt.
- **`set-<user-content-block> <id> <value>`** bei taskctl/rulectl/adrctl
  (z. B. `set-description`, rulectls `set-procedure`, adrctls
  `set-motivation`/`set-rationale`) — dieselbe `<verb>-<type>`-Form wie bei
  Metagroups/Metainfo, jetzt auch für Content-Blöcke. specctl hatte
  `set-description` bereits.
- **`list`-Filter** bei allen vier Tools: `--<metagroup-type> <path>`
  (taskctl/rulectl/adrctl) bzw. `--under <path>` (specctl) — inklusive aller
  Nachfahren, nicht nur exakter Treffer; `--<metainfo-type> <value>`
  (taskctl/rulectl/adrctl) bzw. `--adr <id>` (specctl) — exakter Treffer.
  Höchstens ein Metagroup-Filter pro Aufruf, Metainfo-Filter kombinieren
  sich (AND).
- **`MetainfoSpec.choices` wird jetzt durchgesetzt** (`lib/store.py`,
  `_validate_metainfo_choice`, greift bei `add` und `info-<metainfo-type>`)
  — vorher war das Feld deklariert (z. B. taskctls `review`), aber nie
  geprüft; ein ungültiger Wert wurde still akzeptiert und fiel bei taskctl
  sogar still auf den 3-Schritt-Pfad zurück statt zu scheitern.

**Drei getrennte Verb-Präfixe statt eines gemeinsamen `set-`** für die drei
objektbezogenen Update-Achsen (`design-decisions.md`, "Amendments
(2026-08-19, three-verb command namespace + Change metagroup)"): `group-<Metagroup-Typ>`
(Change metagroup), `info-<Metainfo-Typ>` (Metainfo, vormals
`set-<Metainfo-Typ>` — betrifft auch adrctls `info-spec-ref`/
`info-superseded-by`), `set-<Content-Block>` (Change content, unverändert).
Fest im generischen Engine-Code verankert (`lib/cliapp.py`), nicht als
konfigurierbares `ToolSpec`-Feld — macht die drei Namensräume kollisionsfrei,
ohne pro Tool wählbare Präfixe (die kein Tool je gebraucht hat). Damit ist
**Change metagroup** (`group-<metagroup-type> <id> <path>`) jetzt für
taskctl/rulectl/adrctl implementiert (`lib/store.py`s `set_metagroup`):
weist einem Objekt einen anderen, bereits existierenden Metagroup-Pfad zu,
leitet Nummer/Object-Type/Speicherort neu ab (wie `add`), lehnt No-op
(aktueller Pfad) mit Verweis auf `reorder` ab. Da ein Objekt im generischen
Modell immer ein Metagroup-Blatt ist (nie ein Pfadknoten mit eigenen
Kindern), ist — anders als bei specctls `move` — keine
Object-Type-Neuableitungskaskade nötig.

Beim Implementieren zusätzlich behoben: `_dir_resolve_path`/
`_sf_resolve_path` (genutzt von `add`, `group-<metagroup-type>`,
`resolve_metagroup_path`) fingen `lib/metagroup.py`s `MetagroupError` bisher
nicht ab — ein unauflösbarer Metagroup-Pfad (z. B. `add --component
Nonexistent/thing`) stürzte mit unbehandeltem Traceback ab statt sauber mit
`StoreError`/Exit 1 zu scheitern. Jetzt gefangen und als `StoreError`
weitergereicht.

Noch offen aus dem Spec-vs-Implementierung-Abgleich (siehe `design.md`,
"Metagroup Operations"): Metagroup-**Rename** für taskctl/rulectl/adrctl —
im Contract dokumentiert, noch nicht implementiert. specctl deckt das
implizit über sein eigenes `rename` ab.

Ein Korrektheits-Review (2026-08-20, `design-decisions.md`, "Amendments
(2026-08-20, correctness review: ID uniqueness, atomic writes, ADR
validation)") deckte fünf Probleme auf, alle behoben:
- **Object-ID-Eindeutigkeit** wird jetzt bei `add` geprüft — sowohl
  `lib/store.py` (taskctl/rulectl/adrctl) als auch `lib/spec_store.py`
  (specctl); vorher wurde nur die Syntax geprüft, eine Kollision mit einer
  bereits existierenden ID wurde still akzeptiert.
- **Directory-Mode-Objektschreibvorgänge in `lib/store.py` sind jetzt
  atomar** (`atomicio.atomic_write_text`, `.tmp` + `os.replace`) an allen
  fünf bisher direkten `path.write_text(...)`-Stellen (`add`,
  `set_metagroup`, `_dir_reorder` x2, `_persist`) — `lib/spec_store.py` war
  bereits durchgehend atomar.
- **`set_metagroup`s Schreibreihenfolge** ist jetzt konsistent mit
  `_dir_reorder`: neue Datei zuerst (atomar) schreiben, dann erst die alte
  löschen — vorher umgekehrt, was bei einem Fehler zwischen beiden Schritten
  das Objekt an keinem Ort mehr existieren ließ.
- **`OpenQuestions`** (specctl) ist jetzt über die CLI erreichbar:
  `add-<Ebene> ... --open-questions` und `set-open-questions` — vorher nur
  im Modell vorhanden, nie exponiert.
- **specctls ADR-Validierung prüft jetzt echte Existenz** im adrctl-Store
  (`lib/adr_lookup.py`, `SpecStore._require_valid_adr`) statt nur
  Nichtleerheit — dafür wurde `adrctl.py`s `ToolSpec` nach `lib/adrctl_spec.py`
  extrahiert (einzige Quelle der Wahrheit, keine Duplikation). Geprüft wird
  nur Existenz, bewusst nicht Status oder Rückverweis über `spec-ref` (siehe
  Amendment für die Begründung).

Ein Folge-Review (2026-08-20, `design-decisions.md`, "Amendments
(2026-08-20, adr_lookup follow-up fixes)") deckte zwei weitere Probleme in
`lib/adr_lookup.py` auf, beide behoben, sowie zwei Dokumentationsfehler:
- **`check_adr_exists` legt bei einem fehlschlagenden Check kein `adrs/`
  mehr an**: vorher wurde für jeden Aufruf ein normaler `Store` konstruiert,
  dessen `__post_init__` im Directory-Mode unbedingt `mkdir(...,
  exist_ok=True)` ausführt — auch bei einer rein validierenden Anfrage gegen
  einen noch gar nicht existierenden adrctl-Store. Jetzt wird die Existenz
  zuerst über `resolve_root` (reine Pfadlogik, kein Dateisystemzugriff)
  geprüft; ein `Store` wird erst konstruiert, wenn der Zielort tatsächlich
  existiert.
- **`check_adr_exists` hält jetzt den adrctl-Store-Lock** während des
  `store.get(adr_id)`-Aufrufs — vorher lief die Prüfung ganz ohne Lock, ein
  gleichzeitiges `adrctl`-Schreiben konnte dazwischenlaufen. Das schließt nur
  die "gar kein Lock"-Lücke; keine cross-store-Atomarität mit dem
  nachfolgenden specctl-Schreibvorgang — die adrctl↔specctl-Verknüpfung
  bleibt bewusst nicht-transaktional (siehe bestehendes Amendment).
- **`add --set-status stable|deprecated` ist bewusst von der
  ADR-Pflicht ausgenommen** (design-specctl.md, "Status") — die
  Wahl eines initialen Status bei `add` ist eine "initial-value choice, not
  a transition", derselbe Freibrief, den `design.md` ("Object Status")
  bereits für `--force` gewährt; kein Code-Fix, nur die Ausnahme explizit
  dokumentiert.
- **Widersprüchlicher History-Text korrigiert** (design-specctl.md,
  "Metainfo"): der `adr`-Eintrag behauptete, manuelles `set-adr` und
  automatisches `receive_adr_link` würden "identisch" geloggt — tatsächlich
  loggt nur der automatische Pfad einen `M`-History-Eintrag, `set-adr` nie.

**specctl hat jetzt eine explizite `init`-Lebenszyklus-Operation**
(`design-decisions.md`, "Amendments (2026-08-20, specctl `init` lifecycle)"):
Titel (`# <title>`) und Preamble waren zuvor opake, nie vom Tool berührte
Textblöcke ohne CLI-Zugriff; jetzt sind beide echte, vom Tool verwaltete
Felder. `init <title> [--preamble <value>]` legt das Dokument an; jede
andere schreibende Operation prüft jetzt, ob das Dokument bereits
initialisiert wurde, und scheitert sonst (`SpecStore._require_initialized`)
— anders als `taskctl`/`rulectl`/`adrctl`, die weiterhin bei der ersten
`add` still einen leeren Store anlegen (dort gibt es kein Titel/Preamble-
Konzept, das eine explizite Init rechtfertigen würde). `set-title`/
`set-preamble` ändern beide nachträglich. Im Directory-Mode ersetzt eine
neue Pflichtdatei `_title.md` (immer geschrieben) die bisherige
Existenzprüfung über das Verzeichnis selbst — `SpecStore.__post_init__`
legt das Verzeichnis ohnehin unbedingt an (dasselbe Problem, das
`lib/adr_lookup.py`s `check_adr_exists`-Fix am selben Tag schon für den
adrctl-Store gelöst hat), das Verzeichnis existiert also auch unabhängig davon, ob `init` schon
lief. Eine neue Preamble-Validierung (`lib/spec_document.py`s
`validate_preamble`) lehnt Preamble-Text ab, der selbst wie eine
Section-Überschrift aussieht (`##` bis `######`) — sonst würde `set-preamble`
das Dokument beim nächsten Lesen stillschweigend korrumpieren können.

**`rulectl tasklist` ist jetzt implementiert** (`design-decisions.md`,
"Amendments (2026-08-21, rulectl `tasklist`)"): exportiert alle
`active`-Regeln in den taskctl-Store, gruppiert nach eindeutigem
Language/Context/Category-Pfad zu je einer Phase (`lib/tasklist.py`, analog
zu `lib/adr_lookup.py`/`lib/spec_link.py` — rulectl.py importiert taskctl.py
nie als Ganzes). Der Phasen-Name ist der flach zusammengesetzte Pfad
(`::`-getrennt, Sortpräfixe entfernt) — `/` ist als Trenner reserviert.
Task-IDs sind dieselben wie die Quelle-Regel (Object-IDs sind nur pro Store
eindeutig, daher gefahrlos wiederverwendbar); ein erneuter `tasklist`-Lauf
aktualisiert eine bestehende Task statt sie zu duplizieren (nur tatsächlich
geänderte Felder werden neu geschrieben), setzt ihren Status zwangsweise
auf offen zurück (`--force`-Pfad von `set_status`) und protokolliert das
per `T`-Eintrag über `Store.annotate`. Die Feldableitung folgt der Regel
`checkable`: `llm` → `assignee-type=agent`, Description bettet den vollen
Regeltext ein; sonst → `assignee-type=tool`, `assignee-name` aus der
`tool`-Metainfo, Description führt weiterhin mit einer kurzen
Tool-Anweisung, bettet seit `design-decisions.md`, "Amendments
(2026-08-21, rulectl `tasklist` review-reset + tool-task context)" aber
zusätzlich Description/Procedure/`source` der Regel ein — sonst hätte ein
Subagent bei einem Tool-Task nur Toolname und Rule-ID, keinen Text, gegen
den er ein Toolergebnis fachlich beurteilen könnte. Dasselbe Amendment
lässt `tasklist` beim Re-Export jetzt auch die `review`-Metainfo zwangsweise
auf `none` zurücksetzen, sofern sie davon abweicht — sonst bliebe ein
zuvor auf `R` eskalierter Task nach dem Status-Reset weiterhin auf dem
`review=user`-Pfad und ein frischer Compliant-Befund (`[~]→[X]`) würde
trotz frischem Re-Export weiterhin über `[R]` geführt oder ohne `--force`
abgelehnt. `taskctl.py`s
`ToolSpec`-Konstruktion (inkl. `validate_transition`/`object_type_from_phase`)
wurde dafür nach `lib/taskctl_spec.py` extrahiert (dieselbe Begründung wie
`lib/adrctl_spec.py`). **adrctls `tasklist`-Stub wurde ersatzlos entfernt**,
nicht implementiert — ADRs werden ausschließlich vom Agenten geprüft (siehe
design-adrctl.md), sodass `tasklist`s Tool-vs-Agent-Feldableitung dort keine
Grundlage hat. Der generische `deferred_operations`/`register_deferred`-
Mechanismus (`lib/cliapp.py`, `lib/toolspec.py`) wurde komplett entfernt, da
er nach dieser Änderung von keinem Tool mehr genutzt wird.

**`questctl.py` ist jetzt implementiert** (`design-questctl.md`;
`design-decisions.md`, "Amendments (2026-08-22, questctl/taskctl
implementation)"), zusammen mit einer Erweiterung des generischen Modells um
**variable Metagroup-Tiefe** — `ToolSpec.variable_depth`, genutzt von
`taskctl.py` (0 oder 1: Phase optional) und `questctl.py` (0, 1 oder 2:
Group/Subgroup optional). Die Tiefe ist eine Store-weite Eigenschaft, nie pro
Objekt, und wird nicht als eigener Marker persistiert, sondern aus dem
vorhandenen Inhalt abgeleitet (`Store._established_depth()`) — analog zu
`resolve_root`s eigenem Directory-vs-File-Inferenzprinzip: das erste
erfolgreiche `add` legt die Tiefe fest, ebenso ein `add-<Typ>` auf der
jeweils **tiefsten** deklarierten Ebene eines Tools (bei taskctl also schon
`add-phase` selbst, da Phase zugleich einzige und tiefste Ebene ist; bei
questctl erst `add-subgroup`, nicht das bloße `add-group`). Einmal
festgelegt, akzeptiert `add-<Typ>` weiterhin jede Tiefe **bis einschließlich**
der festgelegten (`Store._check_metagroup_creation_depth`), während ein
neues Objekt exakt diese Tiefe treffen muss
(`Store._check_object_depth`) — beides über `--root`/Store-Grenzen hinweg
konsistent implementiert, kein Tool-Sonderfall. Depth-0-Objekte liegen im
Directory-Mode direkt im Store-Root, das sich dafür selbst als
Metagroup-Verzeichnis registriert (`lib/metagroup.py`s
`dir_ensure_root_registered`, wiederverwendet `index.write_abbrev`
unverändert); ihr Object Type ist die um eine 0-Ebenen-Zeile erweiterte
generische Ableitung aus `lib/abbrev.py` (`______`, keine neue
Sonderkonstante).

questctls `answer`-Befehl (Antworttext + Pflicht-`--message`) schreibt eine
eigene `### Answer`-Sektion und loggt dafür `T` statt `M` — über eine neue,
generische `Store.annotate_content()`-Methode (Content-Schreiben +
`T`-Eintrag in einem Schritt) plus `ToolSpec.no_generic_setter`, das
`lib/cliapp.py` an den drei Stellen greift, an denen sonst automatisch ein
generisches `set-answer`/`--answer` entstünde (Inline-Flag auf `add`,
`set-<Block>`-Subcommand, `add`-Dispatch). `next`/`next-all` unterscheiden
über eine neue `NoWorkAvailable(StoreError)`-Exception (trägt einen
`reason`-String, bei `--json` als eigenes Feld statt der reinen stderr-Zeile)
drei "nichts verfügbar"-Fälle: `in_progress` (irgendwo `[~]` — sperrt neue
Arbeit store-weit, nicht nur für `next-all`), `all_answered`, oder
`awaiting_interaction`. questctls Status-Maschine importiert
`validate_transition` und die Status-Konstanten direkt aus
`lib/taskctl_spec.py` (kein drittes gemeinsames Modul, da bisher nur diese
zwei Tools sie teilen). `lib/cliapp.py`s `_print_result` zeigt `next`-Resultate
jetzt inkl. History (vorher nur `short_line`, obwohl design-taskctl.md das
schon vor dieser Änderung versprach — ein bestehender, jetzt behobener
Spec-vs-Implementierung-Gap, keine Verhaltensänderung durch die Neuerung
selbst). `taskctl.py` selbst brauchte keine Code-Änderung — alles läuft über
`lib/taskctl_spec.py` und das gemeinsame `lib/`-Modell.

524 Unit-/Integrationstests insgesamt unter `tests/`
(`python -m unittest discover -s architecture/scripts/tests -t architecture/scripts`),
davon rund 170 specctl-spezifisch (Single-File- und Directory-Mode, inkl.
`move`, `init`/`set-title`/`set-preamble` und die Init-Pflicht für jede
andere schreibende Operation), rund 20 Tests für `rulectl tasklist`
(Store- und CLI-Ebene: Feldableitung inkl. eingebettetem Rule-Kontext bei
Tool-Tasks, Phasen-Gruppierung, Re-Export-Idempotenz inkl. Status- und
`review`-Reset und `annotate`, Scoping-Flags), mehrere Tests für `resolve_root` (Kollision, Default-Modus,
`.md`-/Name-Override, Multi-Tool-Koexistenz unter einem `--root`), 17 Tests
für die `spec-ref`-Verknüpfung (`receive_adr_link`, `lib/spec_link.py`, den
generischen `after_dispatch`-Hook, End-to-End über `adrctl`/`specctl`:
`add --spec-ref`, `set-status`-Re-Propagation, retroaktives `info-spec-ref`,
fehlendes Ziel), rund 27 Tests für `delete`, `set-<user-content-block>`,
`list`-Filter und die `choices`-Validierung, rund 9 Tests für
`group-<metagroup-type>` (Store- und CLI-Ebene, No-op-Ablehnung, unbekannter
Pfad) und die `info-`-Umbenennung, rund 15 Tests für das erste
Korrektheits-Review: ID-Kollision (Store- und SpecStore-Ebene), das
simulierte Schreib-Fehlschlagszenario für `set_metagroup` (alte Datei
überlebt), `lib/adr_lookup.py`, und OpenQuestions über die CLI (inkl.
ADR-Gating), sowie 2 weitere Tests aus dem Folge-Review: kein `adrs/` bei
fehlschlagendem Check, Lock während des Checks gehalten, sowie 60 weitere
Tests aus der `questctl`/variablen-Tiefe-Einführung: 0-Ebenen-Ableitung
(`lib/abbrev.py`), Root-Registrierung (`lib/metagroup.py`),
Tiefen-Etablierung/-Ablehnung in Directory- und Single-File-Mode inkl.
Persistenz über Store-Neuladen sowie `annotate_content` (`lib/store.py`),
Phase-lose taskctl-Läufe End-to-End, und `questctl.py` End-to-End (alle drei
Tiefen, `answer`/kein `set-answer`, die drei `next`/`next-all`-Gründe,
wiederverwendete Status-Maschine).

Ein `/grill-me`-Durchgang (2026-08-25, `design-decisions.md`, "Amendments
(2026-08-25, taskctl `NoWorkAvailable` + taskctl-author-cli/taskctl-worker-cli
design)") deckte einen kleinen, gezielten `taskctl.py`-Änderungsbedarf auf:
`_handle_next` wirft jetzt `lib/store.py`s bereits vorhandenes
`NoWorkAvailable("all_done", "no open tasks")` statt eines nackten
`StoreError` — damit liefert `--json next` bei erschöpfter Liste
strukturiertes `{"reason": "all_done", ...}` statt einer reinen
stderr-Zeile, was ein schleifender `taskctl-worker`-Lauf braucht, um
"fertig" zuverlässig von einem echten Fehler zu unterscheiden. Reversiert
zwei frühere, zum jeweiligen Zeitpunkt richtige Entscheidungen ("taskctl
braucht das nicht" — siehe die beiden Amendments vom 2026-08-22), jetzt
weil erstmals ein Aufrufer diese Unterscheidung tatsächlich braucht.
Die beiden Skills `taskctl-author-cli` (Tasks/Phasen anlegen und
erweitern) und `taskctl-worker-cli` (Tasks abarbeiten, Status je nach
Arbeit ändern) sind jetzt als
`architecture/skills/taskctl-{author,worker}-cli/SKILL.md` angelegt,
zusammen mit ihren Design-Dokumenten unter `architecture/docs/skills/`.
Anders als bei `rulectl`/`questctl` existieren die zugehörigen Subagents
(`taskctl-author`, `taskctl-worker`) und deren Design-Dokumente noch
nicht — die Skills sind bewusst als workflow-unabhängige
CLI-Kontrakt-Referenzen geschrieben, siehe das Amendment für die
vollständige Befehls-Aufteilung.

Noch offen:
- Metagroup-Rename für taskctl/rulectl/adrctl (siehe oben) — im Contract
  dokumentiert, noch nicht implementiert.
- Aus dem `questctl-author`/`-checker`/`-researcher`-Designpass
  (`design-decisions.md`, "Amendments (2026-08-22, questctl-author/-checker/
  -researcher design)"): die zwei kleinen Erweiterungen an `questctl` selbst
  — `source`-Metainfo (`lib/questctl_spec.py`s `MetainfoSpec`-Tupel) und ein
  optionaler `--group`/`--subgroup`-Scope-Filter auf `next`/`next-all`
  (`questctl.py`s `_configure_parser`/`_handle_next`/`_handle_next_all`,
  analog zu `list`s Filter in `lib/cliapp.py`s `dispatch()`, aber mit dem
  `[~]`-Gate weiterhin ungescoped geprüft — `_no_work_reason` nimmt jetzt
  sowohl die volle als auch die gescopte Record-Liste entgegen) — sind
  implementiert, inkl. 9 neuer Tests (`TestSourceMetainfo`,
  `TestNextScopeFilter`) unter `tests/test_questctl.py`. Alle drei Skills
  (`questctl-author-cli`, `questctl-checker-cli`, `questctl-researcher-cli`)
  sind jetzt als `architecture/skills/questctl-{author,checker,researcher}-cli/
  SKILL.md` angelegt (jedes Recipe aller drei Skills gegen die echte CLI
  verifiziert, inkl. der `info-review`-vor-`R`-Mechanik und des
  Parallel-Modus' `[~]→B`-Sonderfalls bei fehlendem Match bzw. fehlender
  Evidenz). Noch offen: nur noch die drei Subagents selbst
  (`architecture/subagents/questctl-author.md` usw.) — Design-Dokumente
  existieren bereits (`design-questctl-author.md`, `design-questctl-checker.md`,
  `design-questctl-researcher.md` unter `architecture/docs/subagents/`),
  aber noch keine tatsächlichen Dateien — anders als `rulectl-author`/
  `rulectl-checker`, die beide Ebenen bereits haben.
- specctl: die bidirektionale adrctl-Verknüpfung ist implementiert —
  `spec-ref=<id>`-Metainfo bei adrctl (einwertig, `design-decisions.md`,
  "Amendments (2026-08-19, spec-ref single-valued)"), `lib/spec_link.py`,
  Auto-Propagation nach `adrctl add`/`set-status`/`info-spec-ref` über
  `lib/cliapp.py`s `after_dispatch`-Hook in `SpecStore.receive_adr_link`
  (loggt einen `M`-History-Eintrag, anders als das weiterhin manuelle
  `set-adr`). Keine Transaktionalität über beide Stores hinweg: schlägt die
  Propagation fehl (z. B. unbekannte `spec-ref`), bleibt die ADR trotzdem
  persistiert, `adrctl` beendet sich mit Exit 1.
- `resolve_root`-Lücke, beim Testen entdeckt, noch nicht entschieden: Zeigt
  `--root` auf ein **existierendes Verzeichnis eines anderen Tools** (z. B.
  `adrctl --root ./project/tasks`, wobei `tasks/` bereits taskctl gehört),
  wird dieses Verzeichnis unverändert als *gemeinsames* Verzeichnis behandelt
  (`design.md`: "path exists and is a directory → path itself") — adrctl
  legt dann `./project/tasks/adrs/` an, verschachtelt unter dem fremden
  Tool-Verzeichnis, statt dessen Elternverzeichnis als geteiltes Verzeichnis
  zu erkennen. Nur der `.md`-Datei-Fall und der exakte Name-Match-Fall (beide
  bestätigt) lösen das Elternverzeichnis auf; für ein fremdes, bereits
  existierendes Tool-*Verzeichnis* gibt es noch keine analoge Regel.
- Locking wurde nur innerhalb eines Prozesses (Threads) getestet, nicht
  über echte Multi-Prozess-Konkurrenz.

## Tech-Stack

- Python 3.10, ausschließlich Standardbibliothek — keine externen Pakete.

## Geteilter Code

- Funktionalität, die mehrere Tools nutzen, gehört in ein eigenes Modul
  unter `architecture/scripts/lib/`, nicht mehrfach implementieren.
- Ein CLI-Skript importiert ein anderes CLI-Skript nie direkt (z. B. lädt
  `rulectl.py` nicht `taskctl.py` als Ganzes) — nur
  `lib/`-Module werden tool-übergreifend importiert.
- Neuer geteilter Code: erst prüfen, ob er wirklich generisch ist (kein
  Tool-Sonderfall), bevor er nach `lib/` wandert.

## Konsistenz zwischen den Tools

- Exit-Codes: `0` = ok, `1` = Fehler.
- Fehlermeldungen → stderr, reguläre Ausgabe → stdout.
- CLI-Struktur (Subcommands, `--json`-Flag, `--root` als einzelner,
  projektweit gemeinsamer Pfad, Positionsargumente ans Ende) einheitlich über
  alle fünf Tools halten, auch wenn ein Tool das jeweilige Feature (noch)
  nicht braucht — das gilt für specctl trotz eigener CLI-Implementierung
  (kein `lib/cliapp.py`) genauso.
- Bei einer Änderung an einem Tool prüfen, ob dieselbe Änderung auch bei
  den anderen Sinn ergibt (z. B. neue CLI-Option, Statuslogik).

## Struktur

```
architecture/scripts/
├── CLAUDE.md
├── taskctl.py         # CLI: Taskliste (0/1-Ebenen Phase, variable_depth)
├── questctl.py        # CLI: offene Fragen (0/1/2-Ebenen Group/Subgroup, variable_depth)
├── rulectl.py         # CLI: Code-Qualitäts-Regeln
├── adrctl.py          # CLI: ADRs
├── specctl.py         # CLI: Spezifikationsdokumente (eigene CLI, kein lib/cliapp.py)
└── lib/
    ├── ...                # geteilt zwischen allen fünf Tools (Locking, Atomic-IO,
    │                      # Numbering, History, Text, Abbrev, Clock, ...)
    ├── model.py, objectfile.py, singlefile.py, store.py, toolspec.py, index.py, render.py
    │                      # generisches Objektformat: taskctl/questctl/rulectl/adrctl
    ├── taskctl_spec.py    # taskctls ToolSpec (aus taskctl.py extrahiert) -- validate_transition/
    │                      # Status-Konstanten hier, da lib/questctl_spec.py sie direkt importiert
    ├── questctl_spec.py   # questctls ToolSpec -- reuses taskctl_spec.py's status machine verbatim
    ├── adrctl_spec.py     # adrctls ToolSpec (aus adrctl.py extrahiert, einzige Quelle der
    │                      # Wahrheit -- ermöglicht lib/adr_lookup.py, ohne adrctl.py zu importieren)
    ├── adr_lookup.py      # specctl -> adrctl: prüft Existenz einer ADR-ID im adrctl-Store
    │                      # (SpecStore._require_valid_adr) -- eigenes Modul statt in
    │                      # spec_link.py, um einen Zirkelimport mit spec_store.py zu vermeiden
    ├── spec_link.py       # adrctl -> specctl: automatische spec-ref-Propagation
    └── spec_model.py, spec_comment.py, spec_document.py, spec_store.py, spec_render.py
                           # specctl-eigenes, leichtgewichtiges Format (design-specctl.md)
```
