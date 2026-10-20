# Messwerte

Vorlage zum Ausfüllen. Alle Werte stammen vom Demo-Rechner (Windows 11, 8 GB RAM, keine
GPU, Rancher Desktop mit `.wslconfig` memory=5GB, swap=4GB). Alle Befehle in PowerShell im
Repo-Ordner.

| Angabe | Wert |
| --- | --- |
| Rechner (Modell, CPU) | |
| Rancher-Desktop-Version | |
| Ollama-Version (`OLLAMA_VERSION`) | |
| Datum der Messungen | |

## 1. Modellvergleich

### Ablauf

Für den Vergleich muss F13 nicht laufen; es reicht der Ollama-Container.

```powershell
docker compose up -d ollama
# Modell laden (Tags vorher auf ollama.com/library prüfen):
docker compose exec ollama ollama pull llama3.2:3b
docker compose exec ollama ollama pull gemma4        # E2B-Variante; genauen Tag prüfen
docker compose exec ollama ollama pull qwen3.5:2b

# Pro Modell und Prompt: Antwort und Geschwindigkeit
docker compose exec ollama ollama run llama3.2:3b --verbose "<Prompt>"
# → in der Ausgabe „eval rate: … tokens/s“ ablesen

# RAM des geladenen Modells
docker compose exec ollama ollama ps
docker stats --no-stream
```

Nach dem Vergleich nicht benötigte Modelle wieder löschen, z. B.
`docker compose exec ollama ollama rm qwen3.5:2b`. Ein Modellwechsel in F13 braucht
Änderungen an drei Stellen, siehe [README](../README.md#modell-wechseln).

### Test-Prompts

| Nr. | Prompt |
| --- | --- |
| P1 | `Schreibe einen kurzen Ablehnungsbescheid in Leichter Sprache für einen Antrag auf eine Arenalizenz. Grund: Es fehlen Orden. Nenne keine Fristen und keine Beträge.` |
| P2 | `Formuliere diese E-Mail höflich und förmlich um: "Ihr Antrag ist unvollständig, schicken Sie den Rest bis Freitag."` |
| P3 | `Fasse in drei Stichpunkten zusammen: <einen Absatz aus demo-data/rag/ einfügen>` |
| P4 | `Beantworte die Frage nur mit dem folgenden Text. Wenn die Antwort nicht im Text steht, sag das. Text: <§ 3 der VwV PokéHaltung einfügen> Frage: Darf ich mein Glurak mit ins Büro bringen?` |
| P5 | `Korrigiere Rechtschreibung und Grammatik: <einen Satz mit Fehlern einfügen>` |

### Ergebnis

Bewertung 1 = schlecht, 5 = sehr gut. Deutsch: Grammatik, Wortwahl, Ton. Quellentreue: nur
P4 (bleibt beim Text, erfindet nichts).

| Modell | Tag | Tokens/s (Mittel P1–P5) | Deutsch 1–5 | Quellentreue 1–5 | RAM laut `ollama ps` | RAM laut `docker stats` (ollama) | Bemerkung |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Llama 3.2 3B | `llama3.2:3b` | | | | | | |
| Gemma 4 E2B | `gemma4` (Tag prüfen) | | | | | | |
| Qwen 3.5 2B | `qwen3.5:2b` | | | | | | |
| Granite Embedding 278M | `granite-embedding:278m` | – | – | – | | | Embedding |

**Entscheidung Modell:** ______________________ (Begründung: ______________________)

## 2. RAM-Messung

### Pro Container

Messen, wenn der ganze Stack läuft, `warmup` gelaufen ist und gerade eine Recherche-Anfrage
bearbeitet wird (Spitzenlast):

```powershell
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.CPUPerc}}"
```

| Container | `mem_limit` | Leerlauf (nach `warmup`) | Spitze (Recherche läuft) |
| --- | --- | --- | --- |
| ollama | 3500 MB | | |
| elasticsearch | 1200 MB | | |
| rag | 900 MB | | |
| parser | 900 MB | | |
| summary | 500 MB | | |
| chat | 500 MB | | |
| core | 256 MB | | |
| feedback | 256 MB | | |
| feedback-db | 256 MB | | |
| frontend | 200 MB | | |
| opa | 128 MB | | |
| **Summe Container** | | | |

Wurde ein Container wegen Speichermangel beendet?

```powershell
docker inspect --format "{{.Name}} OOMKilled={{.State.OOMKilled}} Neustarts={{.RestartCount}}" $(docker compose ps -q)
```

Ergebnis: ______________________

### Windows gesamt

| Messpunkt | Wie | Leerlauf | Spitze |
| --- | --- | --- | --- |
| RAM belegt gesamt | Task-Manager → Leistung → Arbeitsspeicher „In Verwendung“ | | |
| VM von Rancher Desktop | Task-Manager → Details → `vmmemWSL` (bzw. `vmmem`) | | |
| Browser | Task-Manager → Prozesse | | |
| Rancher-Desktop-Oberfläche | Task-Manager → Prozesse | | |
| Zugesicherter Speicher (inkl. Auslagerung) | Task-Manager → Leistung → Arbeitsspeicher „Zugesichert“ | | |

Alternativ in PowerShell (belegter RAM in GB):

```powershell
Get-CimInstance Win32_OperatingSystem | Select-Object @{n='Belegt_GB';e={[math]::Round(($_.TotalVisibleMemorySize-$_.FreePhysicalMemory)/1MB,2)}}
```

## 3. Antwortzeiten

| Vorgang | Wie messen | Zeit |
| --- | --- | --- |
| Start bis alles ✔ | Stoppuhr ab `docker compose up -d` bis `docker compose run --rm pruefen` grün ist | |
| Warm-up | Ausgabe von `docker compose run --rm warmup` | |
| Chat (Prompt aus DEMO-SKRIPT Teil 2) | Stoppuhr: bis zum ersten Wort / bis zum Ende | / |
| Zusammenfassung `vwv_pokehaltung.pdf` | Stoppuhr ab Upload bis Ergebnis | |
| Recherche: Upload der 6 PDFs + Frage 1 | Stoppuhr | |
| Recherche: jede weitere Frage | Stoppuhr | |

## 4. RAG-Trefferquote

Fragen und erwartete Antworten stehen in
[`demo-data/rag/testfragen.md`](../demo-data/rag/testfragen.md). Jede Frage **3-mal**
stellen, weil kleine Modelle schwanken.

- **Mit RAG:** im Reiter Recherche, Datei-Modus, alle 6 PDFs hochgeladen.
- **Ohne RAG (Gegenprobe):** `docker compose run --rm testfragen` (fragt Ollama direkt, ohne
  Dokumente).

„Richtig“ heißt: Kernaussage stimmt mit dem Antwortschlüssel überein. Bei der Kontrollfrage 12
heißt „richtig“: Das Modell sagt, dass die Quellen dazu nichts enthalten, und erfindet keinen
Betrag. „Quelle“ heißt: Die
richtige Fundstelle wird angezeigt bzw. genannt.

| Nr. | Frage (kurz) | Mit RAG: richtig (x/3) | Mit RAG: Quelle korrekt (x/3) | Zeit pro Antwort | Ohne RAG: richtig (x/3) | Ohne RAG: Verhalten (rät / weiß nicht / falsch) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Glurak ins Büro | | | | | |
| 2 | Arenalizenz: Kosten, Dauer | | | | | |
| 3 | Serverraum | | | | | |
| 4 | Meisterbälle | | | | | |
| 5 | Relaxo im Flur | | | | | |
| 6 | Simsala beim Mitarbeitergespräch | | | | | |
| 7 | Altbernstein wiederbeleben | | | | | |
| 8 | Widerspruch Arenalizenz | | | | | |
| 9 | Pokéball verschwunden | | | | | |
| 10 | Assistenz-Pikachu im Serverraum | | | | | |
| 11 | Glurak: Attacken und Büro | | | | | |
| 12 | Pokémon-Steuer (Kontrollfrage) | | | | | |
| | **Trefferquote** | **__ %** | **__ %** | | **__ %** | |

Trefferquote = Summe richtig ÷ (Anzahl Fragen × 3).

Auffälligkeiten (falsche Abschnitte gefunden, erfundene Paragraphen, abgeschnittene Antworten):

- …

## 5. Go/No-Go am Fr, 23.10.2026

**Frage:** Laufen Chat und Embeddings gleichzeitig stabil auf 8 GB?

Test: Ollama mit beiden Modellen laden und abwechselnd bzw. direkt nacheinander Chat und
Embedding anfragen.

```powershell
docker compose up -d ollama
docker compose run --rm modelle-laden
docker compose run --rm warmup
docker compose exec ollama ollama ps      # beide Modelle geladen?
docker stats --no-stream
```

Die Schwellen sind Vorschläge; vor dem Test festlegen und dann nicht mehr ändern.

| Kriterium | Schwelle | Gemessen | Erfüllt? |
| --- | --- | --- | --- |
| LLM und Embedding gleichzeitig geladen (`ollama ps`) | beide | | |
| Kein OOM-Kill, kein Neustart von ollama | 0 | | |
| Windows-RAM „In Verwendung“ bei Spitze | < 90 % | | |
| Geschwindigkeit LLM | ≥ ___ Tokens/s | | |
| Windows bleibt bedienbar (Browser, Taskleiste) | ja | | |

**Entscheidung:** ☐ Go ☐ No-Go → Rückfallstufe: ______

Rückfallstufen laut [PLAN.md](PLAN.md) §3, in dieser Reihenfolge:

1. Kleineres Modell (Gemma 4 E2B)
2. Summary-Dienst weglassen und die Zusammenfassung über den Chat zeigen
3. Für die Vorführung einen Rechner mit 16 GB ausleihen

Begründung und Datum: ______________________
