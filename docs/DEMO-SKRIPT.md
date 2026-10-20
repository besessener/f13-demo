# Demo-Skript: Montag, 09.11.2026 (10–12 Minuten)

Klick-für-Klick-Ablauf der Vorführung. Alle Befehle in PowerShell im Repo-Ordner
`C:\Projekte\f13-demo`.

> ⚠️ Während der ganzen Vorführung gilt: **niemals `docker compose down -v`** (löscht die
> Modelle). Und: den Reiter **Transkription nicht anklicken**, dafür gibt es kein Backend.
> Die Onlinesuche ebenfalls nicht aktivieren.

## Überblick

| Zeit | Teil | Was gezeigt wird |
| --- | --- | --- |
| 0:00–1:00 | 1. Einstieg | Was ist F13, warum lokal, Architekturskizze |
| 1:00–3:00 | 2. Chat | Ablehnungsbescheid in Leichter Sprache |
| 3:00–5:00 | 3. Zusammenfassung | VwV PokéHaltung als PDF → Stichpunkte |
| 5:00–9:00 | 4. Recherche (RAG) | Testfragen mit Quellen, danach Gegenprobe ohne RAG |
| 9:00–10:00 | 5. Souveränität | WLAN aus, noch eine Frage |
| 10:00–12:00 | 6. Grenzen und Fazit | Abschlussfolie |

## Fensteraufbau

| Fenster | Inhalt |
| --- | --- |
| 1 Browser | Ein Fenster, ein Tab: <http://localhost:9999>, Zoom 125 % |
| 2 PowerShell „Gegenprobe“ | Fertige Ausgabe von `docker compose run --rm testfragen` |
| 3 PowerShell „Betrieb“ | Für Notfälle: `ps`, `logs`, `restart` (nicht zeigen) |
| 4 Explorer | `C:\Projekte\f13-demo\demo-data` für Drag-and-drop |
| 5 Folien | Architekturskizze (aus [ARCHITEKTUR.md](ARCHITEKTUR.md)) und Abschlussfolie |
| 6 Videoplayer | Aufzeichnung der Generalprobe, pausiert am Anfang |

## Spickzettel: erwartete Antworten

Quelle: [`demo-data/rag/testfragen.md`](../demo-data/rag/testfragen.md) (12 Fragen; hier nur
die, die in der Vorführung vorkommen). Bei Abweichungen gilt testfragen.md.

| Nr. | Frage | Erwartete Kernaussage | Fundstelle |
| --- | --- | --- | --- |
| 1 | „Darf ich mein Glurak mit ins Büro bringen?“ | Nur mit schriftlicher Brandschutzfreigabe der/des Brandschutzbeauftragten; Antrag mit Formblatt BS-17 mindestens 10 Arbeitstage vorher; gilt 6 Monate für einen Raum | VwV PokéHaltung § 3 |
| 2 | „Was kostet eine Arenalizenz und wie lange dauert das Verfahren?“ | 2.500 Pokédollar; Entscheidung innerhalb von 6 Wochen, mit Ortsbesichtigung höchstens 10 Wochen | ArenaLizO § 6 und § 7 |
| 3 | „Welche Pokémon dürfen nicht in den Serverraum?“ | Elektro-Pokémon wie Pikachu, Raichu, Magnetilo, auch im Pokéball, ohne Ausnahme | VwV PokéHaltung § 7 |
| 4 | „Wer darf Meisterbälle ausgeben?“ | Nur die/der Meisterballbeauftragte in Referat Z 2, Gegenzeichnung durch die Abteilungsleitung Z (Vier-Augen-Prinzip), Formblatt MB-1 | Dienstanweisung Pokéball-Inventur § 7 |
| 6 | „Darf Simsala bei meinem Mitarbeitergespräch dabei sein?“ (Souveränität) | Nein, Psycho-Pokémon dürfen nicht an Personalgesprächen teilnehmen, auch nicht mit Zustimmung | VwV PokéHaltung § 9 |

Reserve, falls Zeit bleibt oder eine Frage hakt: Nr. 5 Relaxo (höchstens 15 Minuten im Flur,
dann Ruheraum 0.12, VwV § 5) und Nr. 8 Widerspruch (21 Kalendertage, ArenaLizO § 10). Nr. 8
passt gut zum Chat-Teil: Dort durfte das Modell keine Frist nennen.

Gemessene Antwortzeiten aus der Generalprobe ([MESSWERTE.md](MESSWERTE.md)):
Chat ___ s, Zusammenfassung ___ s, Recherche pro Frage ___ s.

## Checkliste 30 Minuten vorher

- [ ] Netzteil angeschlossen, Energiemodus „Beste Leistung“
- [ ] „Nicht stören“ an, Windows-Updates pausiert (am Vortag)
- [ ] Rancher Desktop läuft (Fenster nur minimieren, nicht beenden)
- [ ] Alte Zustände zurücksetzen: `docker compose restart chat summary rag`
- [ ] `start.cmd` doppelklicken. Es startet alles, prüft (jede Zeile ✔), wärmt vor und öffnet den Browser.
- [ ] Zusätzlich `docker compose ps`: alle Dienste `running`/`healthy`
- [ ] Fenster 2: `docker compose run --rm testfragen` laufen lassen, bis alle Antworten da
      sind (alle Fragen nacheinander auf der CPU, das dauert mehrere Minuten; daher früh
      starten); zu Frage 1 scrollen. (Umlaute kaputt? Vorher
      `[Console]::OutputEncoding = [Text.Encoding]::UTF8`.)
- [ ] `docker stats --no-stream`: RAM plausibel (Vergleich mit [MESSWERTE.md](MESSWERTE.md))
- [ ] Browser: nur ein Tab <http://localhost:9999>, Zoom 125 % (Strg + Plus), alte
      Chatverläufe in der Oberfläche gelöscht
- [ ] Im Chat ist das Modell „Llama 3.2 3B (lokal)“ ausgewählt
- [ ] Explorer, Folien und Videoplayer (Fenster 4–6) offen
- [ ] Spickzettel mit testfragen.md abgeglichen
- [ ] Wird per Teams geteilt? Wenn möglich lieber per HDMI/Beamer; Teams braucht viel RAM.

## Checkliste 5 Minuten vorher

- [ ] `docker compose run --rm pruefen`: jede Zeile ✔
- [ ] `docker compose run --rm warmup` (geht schnell, wenn die Modelle noch geladen sind)
- [ ] **WLAN bleibt bis nach dem Warm-up an.** Ausgeschaltet wird es erst live in Teil 5.
- [ ] LAN-Kabel abziehen (sonst ist „WLAN aus“ kein Beweis)
- [ ] Teams, Outlook und alle anderen Programme schließen; nur Fenster 1–6 bleiben offen
- [ ] Browser-Zoom noch einmal prüfen: 125 %
- [ ] Browser in den Vordergrund, Reiter Chat geöffnet

---

## Teil 1: Einstieg (1 Minute)

**Zeigen:** Folie mit der Architekturskizze.

**Sagen:**
> „F13 ist die Open-Source-KI-Assistenz des Landes Baden-Württemberg, seit Juli 2025 unter
> MPL-2.0 auf openCode. Ich habe sie komplett auf diesem Laptop aufgebaut: 8 GB RAM, keine
> GPU, keine Cloud. Links Windows mit Browser, rechts die Container in Rancher Desktop. Das
> Herzstück ist der Core, ein API-Gateway, das die Anfragen an Chat, Zusammenfassung und
> Recherche verteilt. Das Sprachmodell ist Llama 3.2 mit 3 Milliarden Parametern und läuft
> über Ollama ebenfalls hier im Container. Kein Byte verlässt den Rechner.“

**Klicken:** Zum Browser wechseln.

**Falls es hakt:** Die Skizze ist auch in `docs/ARCHITEKTUR.md` (im Editor öffnen).

## Teil 2: Chat (2 Minuten)

**Klicken:** Reiter **Chat**. Modell „Llama 3.2 3B (lokal)“ ist ausgewählt.

**Eingeben:**

```text
Schreibe einen Ablehnungsbescheid in Leichter Sprache.

Situation: Herr Ash Ketchum aus Alabastia hat eine Arenalizenz beantragt. Der Antrag wird abgelehnt. Der Grund: Er hat erst 5 von 8 Orden.

Der Bescheid soll enthalten:
- was entschieden wurde
- warum
- was Herr Ketchum jetzt tun kann
- dass er Widerspruch einlegen kann

Regeln: kurze Sätze, ein Gedanke pro Satz, keine Fachwörter, Anrede mit „Sie“. Nenne keine Fristen und keine Beträge.
```

**Sagen, während die Antwort läuft:**
> „Das ist ein typischer Verwaltungsfall: ein Bescheid, aber verständlich für alle. Die
> Antwort kommt Wort für Wort, weil das Modell auf der CPU rechnet. Auf einem Server mit GPU
> wäre das ein Bruchteil der Zeit.“

**Erwartet:** Ein kurzer Brief mit einfachen Sätzen: Entscheidung (Antrag abgelehnt), Grund
(zu wenige Orden), nächster Schritt (weitere Orden sammeln, neu beantragen), Hinweis auf
Widerspruch. Kleinere sprachliche Schwächen sind bei einem 3B-Modell normal.

**Sagen danach:**
> „Was das Modell nicht weiß: wie die Regeln für Arenalizenzen genau lauten. Dafür gibt es
> gleich die Recherche.“

**Falls es hakt:**
- Nach 30 s noch kein Text: in Fenster 3 `docker compose logs --tail 50 chat` ansehen,
  währenddessen weiterreden.
- Modellliste leer: Seite neu laden (F5).
- Fehlermeldung: `docker compose restart chat`, 30 s warten, erneut senden. Klappt es nicht,
  den Abschnitt aus der Aufzeichnung zeigen.

## Teil 3: Zusammenfassung (2 Minuten)

**Klicken:** Reiter **Zusammenfassung**. Aus dem Explorer
`demo-data\summary\vwv_pokehaltung.pdf` in das Upload-Feld ziehen.

**Eingeben (nur falls die Oberfläche ein Feld für Hinweise oder Fokus anbietet):**

```text
Kurzfassung in 5 Stichpunkten für Mitarbeitende
```

**Sagen, während es läuft:**
> „Das ist die erfundene Verwaltungsvorschrift über die Haltung von Pokémon in
> Dienstgebäuden. Der Parser macht aus dem PDF Text, dann fasst das Modell Abschnitt für
> Abschnitt zusammen und führt die Teile zusammen. Das nennt sich Map-Reduce und funktioniert
> auch bei Dokumenten, die nicht in einem Stück ins Modell passen.“

**Erwartet:** Stichpunkte mit den Kernregeln, z. B. Brandschutzfreigabe für Feuer-Pokémon
(§ 3), Relaxo höchstens 15 Minuten im Flur, Fluchtwege frei (§ 5), Elektro-Pokémon nicht in den
Serverraum (§ 7), Psycho-Pokémon nicht bei Personalgesprächen (§ 9).

**Falls es hakt:**
- Dauert es länger als 2 Minuten: weiterreden und dann zu Teil 4 wechseln, sobald das
  Ergebnis da ist. Nicht parallel eine zweite Anfrage starten (Ollama arbeitet nur eine
  Anfrage gleichzeitig ab).
- Fehler beim Upload: `docker compose logs --tail 50 summary` und `… parser` in Fenster 3.
- Rückfall: Im Reiter Chat den Text aus `demo-data\rag\01_vwv_pokehaltung.md` einfügen,
  davor „Fasse diesen Text in 5 Stichpunkten zusammen:“. Oder den Abschnitt aus der
  Aufzeichnung zeigen.

## Teil 4: Recherche mit RAG (4 Minuten)

**Klicken:** Reiter **Recherche**. Falls es eine Auswahl zwischen Datei und Datenbank gibt:
**Datei**. Im Explorer `demo-data\rag\` öffnen, ins Suchfeld `*.pdf` tippen, Strg + A
(6 PDFs von `01_vwv_pokehaltung.pdf` bis `06_dienstanweisung_inventur.pdf`, keine
Markdown-Dateien) und alles in das Upload-Feld ziehen. Tipp: Diese
Explorer-Ansicht schon vorher vorbereiten.

**Sagen:**
> „Jetzt die eigentliche Probe. Das sind sechs Dokumente einer erfundenen Behörde, des
> Landesamts für Pokémon-Angelegenheiten Kanto. Die Regeln habe ich mir ausgedacht. Das
> Modell kann sie also nicht aus dem Training kennen. Wenn es richtig antwortet, kommt das
> Wissen aus den Dokumenten.“

**Eingeben, nacheinander** (Wortlaut aus `testfragen.md`):

| Reihenfolge | Frage | Pflicht? |
| --- | --- | --- |
| 1 | `Darf ich mein Glurak mit ins Büro bringen?` | Pflicht |
| 2 | `Welche Pokémon dürfen nicht in den Serverraum?` (Testfrage 3) | Pflicht |
| 3 | `Was kostet eine Arenalizenz und wie lange dauert das Verfahren?` (Testfrage 2) | wenn Zeit |
| 4 | `Wer darf Meisterbälle ausgeben?` (Testfrage 4) | wenn Zeit |

Ob Fragen 3 und 4 live gestellt werden, entscheide ich nach der gemessenen Zeit pro Frage aus
der Generalprobe. Die zwei Pflichtfragen haben die eindeutigsten Antworten.

**Bei jeder Antwort zeigen:** die Quellenangabe (Dokument, Abschnitt). Mit dem Spickzettel
vergleichen.

**Sagen, während es läuft:**
> „Die PDFs werden in kurze Abschnitte zerlegt, jeder Abschnitt bekommt einen Vektor von
> einem Embedding-Modell. Zur Frage werden die drei ähnlichsten Abschnitte gesucht, und nur
> diese bekommt das Sprachmodell zu sehen, mit der Anweisung, nur daraus zu antworten.“

**Erwartet:** siehe Spickzettel. Glurak: nur mit schriftlicher Brandschutzfreigabe
(Formblatt BS-17, 10 Arbeitstage vorher), § 3. Serverraum: Elektro-Pokémon wie Pikachu, auch
im Pokéball, § 7. Ein 3B-Modell nennt evtl. nicht jedes Detail; entscheidend ist die
Kernaussage mit Fundstelle.

### Gegenprobe ohne RAG

**Klicken:** Zu Fenster 2 („Gegenprobe“) wechseln, Antwort auf Frage 1 zeigen.

**Sagen:**
> „Das ist dasselbe Modell mit derselben Frage, aber ohne die Dokumente. Das habe ich vorhin
> mit einem kleinen Werkzeug direkt gegen Ollama laufen lassen. Ohne Quellen rät das Modell
> oder sagt, dass es das nicht weiß. Von einer Brandschutzfreigabe nach § 3 steht da
> nichts. Genau das ist der Unterschied, den RAG macht.“

**Falls es hakt:**
- Upload hängt oder Fehler: `docker compose logs --tail 50 rag` in Fenster 3. Häufigste
  Ursache wäre der Parser: `docker compose logs --tail 50 parser`.
- Antwort falsch oder ohne Quelle: offen ansprechen („kleines Modell, das ist eine der
  Grenzen“), nächste Pflichtfrage stellen.
- Alles hängt: `docker compose restart rag`, bis dahin die Gegenprobe in Fenster 2 erklären.
  Sonst den Abschnitt aus der Aufzeichnung zeigen.

## Teil 5: Souveränität (1 Minute)

**Klicken:** Win + A (Schnelleinstellungen) → **WLAN-Kachel aus**. Das durchgestrichene
WLAN-Symbol in der Taskleiste zeigen. Zurück zum Browser, Reiter **Recherche** (die PDFs sind
noch hochgeladen).

**Eingeben:**

```text
Darf Simsala bei meinem Mitarbeitergespräch dabei sein?
```

**Sagen:**
> „Das WLAN ist aus. Kein Internet, keine Cloud. Und F13 antwortet trotzdem, weil Modell,
> Dokumente und alle Dienste auf diesem Laptop laufen. Die Ports sind außerdem nur lokal
> erreichbar, nicht aus dem Netz.“

**Erwartet:** Nein, Psycho-Pokémon dürfen nicht an Personalgesprächen teilnehmen, VwV PokéHaltung § 9 (Testfrage 6).

**Falls es hakt:**
- Müssen die PDFs neu hochgeladen werden, das tun; sie liegen ja lokal.
- Dauert es zu lange: stattdessen im Reiter Chat eine kurze Frage stellen, z. B.
  `Erkläre in zwei Sätzen, was ein Bescheid ist.`
- WLAN erst **nach** der Vorführung wieder einschalten.

## Teil 6: Grenzen und Fazit (2 Minuten)

**Zeigen:** Abschlussfolie.

**Gesprächspunkte für die Folie:**

| Grenzen der Demo | Was der Produktivbetrieb bräuchte |
| --- | --- |
| Langsam: CPU statt GPU, Antworten in Sekunden bis Minuten (Messwerte: ___ Tokens/s) | Server mit GPU, z. B. im Rechenzentrum |
| 3B-Modell: einfaches Deutsch, Fehler möglich, auch mit RAG | Größeres Modell, das auf der GPU läuft |
| 4096 Tokens Kontext, nur kurze Dokumente | Größerer Kontext für lange Akten |
| Ein Nutzer, eine Anfrage zur Zeit | Mehrere parallele Anfragen, Lastverteilung |
| Gastmodus ohne Login | Anmeldung über Keycloak, Rollen und Rechte (OPA) |
| Recherche im Datei-Modus: Dokumente pro Sitzung hochladen | Datenbank-Modus mit dauerhaft indexierter Wissensbasis (Elasticsearch) |
| Keine Transkription | Transkriptionsdienst ergänzen |
| Teile der Konfiguration sind noch ungeprüfte Annahmen | Abgleich mit der offiziellen Doku, Betrieb mit Monitoring, Backups und Updates |

**Sagen:**
> „Fazit: F13 lässt sich mit Bordmitteln komplett lokal betreiben, sogar auf einem
> 8-GB-Laptop. Für echte Arbeit braucht es eine GPU und ein größeres Modell, aber die
> Architektur bleibt dieselbe: Frontend, Core und Fachdienste. Das Repo mit Anleitung für 15
> Minuten Einrichtung gebe ich gern weiter.“

Nach der Vorführung: WLAN wieder einschalten.

---

## Notfall

| Lage | Was tun |
| --- | --- |
| Oberfläche hängt, Backend läuft | Fenster 3: `docker compose run --rm vorfuehrung` zeigt Chat, Zusammenfassung und Recherche (mit Gegenprobe) direkt im Terminal |
| Ein Dienst antwortet nicht | Fenster 3: `docker compose ps`, `docker compose logs --tail 50 <dienst>`, `docker compose restart <dienst>`, danach `docker compose run --rm warmup` |
| Alles ist sehr langsam | `docker stats --no-stream`; prüfen, ob doch noch Programme offen sind |
| Nichts geht mehr | **Aufzeichnung zeigen** (Fenster 6) und live dazu erzählen |

**Die Aufzeichnung als Rückfall:** Bei der Generalprobe (04./05.11.) den kompletten Ablauf
aufnehmen, z. B. mit dem Snipping Tool (Bildschirmaufnahme) oder der Xbox Game Bar
(Win + Alt + R). Die Datei liegt **außerhalb des Repos**, z. B.
`C:\Projekte\f13-demo-aufzeichnung.mp4`, mit einer Kopie auf einem USB-Stick. Vor der Demo im
Videoplayer öffnen und am Anfang pausieren.
