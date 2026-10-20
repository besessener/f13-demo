# F13-Demo: lokale KI-Assistenz mit Pokémon-Wissensbasis

Dieses Repo startet [F13](https://gitlab.opencode.de/f13), die Open-Source-KI-Assistenz des
Landes Baden-Württemberg, vollständig lokal auf einem Windows-Laptop mit 8 GB RAM. Ein kleines
Sprachmodell läuft über Ollama im Container, und F13 zeigt damit Chat, Zusammenfassung und
Recherche (RAG). Für die Recherche gibt es eine erfundene Wissensbasis des „Landesamts für
Pokémon-Angelegenheiten Kanto“, damit sich beweisen lässt, dass die Antworten wirklich aus den
Dokumenten stammen.

> **Stand:** Der Stack wird bei jedem Push von GitHub Actions mit einem Mini-Modell gegen die
> echten F13-Images getestet ([Stack-Test](../../actions/workflows/stack-test.yml)). Offene
> Annahmen und wie man sie prüft: [docs/VERIFIZIEREN.md](docs/VERIFIZIEREN.md).

## Voraussetzungen

| Was | Details |
| --- | --- |
| Rechner | Windows 11, 8 GB RAM, keine GPU nötig |
| Rancher Desktop | **Preferences → Container Engine: `dockerd (moby)`** (nicht containerd). **Kubernetes: aus.** |
| Speicherlimit | `%UserProfile%\.wslconfig` anlegen (siehe unten), danach `wsl --shutdown` und Rancher Desktop neu starten |
| Git | Git für Windows |
| Netz | Nur für die Einrichtung (Images, Modelle, Frontend-Build). Die Demo selbst läuft offline. |

**Nicht nötig:** keine eigene WSL-Distribution (Ubuntu o. Ä.), kein `make`, keine Bash und
**keine PowerShell-Skripte**. Gestartet wird mit `start.cmd`, einer Batch-Datei, die die
PowerShell-Ausführungsrichtlinie nicht betrifft. Alles Weitere läuft über `docker compose`. Rancher Desktop bringt seine eigene, versteckte WSL2-VM mit, in der wir nie direkt
arbeiten.

`.wslconfig` (z. B. mit `notepad $env:USERPROFILE\.wslconfig`):

```ini
[wsl2]
memory=5GB
swap=4GB
```

```powershell
wsl --shutdown
# danach Rancher Desktop neu starten
docker run --rm hello-world
docker compose version
```

Die restlichen ca. 3 GB bleiben für Windows, die Rancher-Desktop-Oberfläche und den Browser.

## Schnellstart

1. Repo klonen (PowerShell):
   ```powershell
   git clone https://github.com/besessener/f13-demo.git C:\Projekte\f13-demo
   ```
2. Im Explorer `C:\Projekte\f13-demo\start.cmd` **doppelklicken** (oder in PowerShell
   `.\start.cmd`).

`start.cmd` erledigt alles und öffnet am Ende den Browser auf **<http://localhost:9999>**:

| Schritt | Was passiert |
| --- | --- |
| 1 | Prüft, ob Rancher Desktop läuft |
| 2 | `docker compose up -d --wait`: lädt Images, baut beim ersten Mal das Frontend aus dem Git-Tag, lädt fehlende Modelle (Einmal-Container `modelle-laden`) und wartet, bis alle Dienste bereit sind |
| 3 | `docker compose run --rm pruefen`: prüft jeden Dienst (✔/✘) |
| 4 | `docker compose run --rm warmup`: lädt die Modelle in den Speicher, damit die erste Antwort schnell kommt |

**Beim ersten Mal** braucht es Internet und Geduld: mehrere GB Images plus ca. 2,6 GB
Modelle. **Danach** startet alles auch offline, weil `modelle-laden` vorhandene Modelle
nicht neu lädt.

Beenden: `stopp.cmd` doppelklicken. Modelle und Daten bleiben erhalten.

Falls ein Image nicht gefunden wird: `docker compose run --rm versionen` zeigt die
verfügbaren F13-Tags. Den Wert dann in `.env` korrigieren.

## Alle Befehle

Immer im Repo-Ordner ausführen (`cd C:\Projekte\f13-demo`).

| Aufgabe | Befehl |
| --- | --- |
| Alles starten (empfohlen) | `start.cmd` (Doppelklick) |
| Nur die Container starten | `docker compose up -d --wait` |
| Status und Health | `docker compose ps` |
| Logs eines Dienstes | `docker compose logs -f --tail 100 chat` (statt `chat` auch `core`, `summary`, `rag`, `parser`, `ollama` …) |
| Alles prüfen | `docker compose run --rm pruefen` |
| Warm-up vor der Vorführung | `docker compose run --rm warmup` |
| Modelle laden (einmalig) | `docker compose run --rm modelle-laden` |
| Image-Tags im Registry nachsehen | `docker compose run --rm versionen` |
| Gegenprobe ohne RAG | `docker compose run --rm testfragen` |
| Echte Anfragen an Chat, Summary, RAG | `docker compose run --rm smoke-test` |
| API-Beschreibungen der F13-Dienste | `docker compose run --rm api-doku` (→ `ausgabe/openapi/`) |
| Zurücksetzen | `docker compose restart chat summary rag` |
| RAM pro Container | `docker stats --no-stream` |
| Stoppen | `stopp.cmd` oder `docker compose down` |

> ## ⚠️ NIEMALS `docker compose down -v`
>
> `-v` löscht alle Volumes: die heruntergeladenen **Modelle** (mehrere GB, neu laden dauert),
> den Elasticsearch-Index und die Feedback-Datenbank. Zum Stoppen immer nur
> `docker compose down`, zum Zurücksetzen `docker compose restart chat summary rag`.

Die Werkzeuge (`pruefen`, `warmup`, `versionen`, `testfragen`, `smoke-test`, `api-doku`) sind
kleine Python-Container im Compose-Profil `werkzeuge`. Sie starten nicht mit `up`, sondern nur
mit `run --rm`. Ausnahme: `modelle-laden` läuft bei jedem `up` automatisch als
Einmal-Container vor Chat, Summary und RAG.

## Automatischer Test (GitHub Actions)

Der Workflow [`.github/workflows/stack-test.yml`](.github/workflows/stack-test.yml) läuft
bei jedem Push auf `main`, bei Pull Requests und von Hand (Actions → Stack-Test → Run
workflow):

1. **Statische Prüfungen:** Compose-Datei, Python, YAML, APISIX-`#END`, OPA-Richtlinie,
   Zeilenenden
2. **Stack mit Mini-Modell:**
   - ersetzt `llama3.2:3b` durch `qwen2.5:0.5b`
   - baut das Frontend, startet den kompletten Stack und führt `pruefen` und `smoke-test`
     aus
   - sichert die OpenAPI-Beschreibungen

Logs, RAM pro Container und OpenAPI-Dateien hängen als Artefakt **stack-ausgabe** am Lauf.
Der Runner hat 16 GB RAM, die RAM-Werte sind trotzdem ein guter Hinweis für den 8-GB-Laptop.

## Konfiguration (`.env`)

| Variable | Bedeutung |
| --- | --- |
| `FRONTEND_PORT`, `CORE_PORT` | Ports auf dem Host (9999 und 8000), nur an `127.0.0.1` gebunden |
| `F13_*_VERSION` | Tags der F13-Images (Frontend, Chat, Feedback, Summary, RAG, Parser) |
| `OLLAMA_VERSION`, `APISIX_VERSION`, `OPA_VERSION`, `ELASTICSEARCH_VERSION`, `POSTGRES_VERSION`, `WERKZEUG_PYTHON_VERSION` | Tags der übrigen Images |
| `LLM_MODELL`, `EMBEDDING_MODELL` | Ollama-Modelle, die `modelle-laden` und `warmup` verwenden |

## Modell wechseln

Die YAML-Configs von F13 können `.env` nicht lesen. Ein Modellwechsel braucht deshalb
Änderungen an **drei Stellen**:

| # | Datei | Was ändern |
| --- | --- | --- |
| 1 | `.env` | `LLM_MODELL` (bzw. `EMBEDDING_MODELL`) |
| 2 | `config/f13/llm_models.yml` | `model` und `label` in den Abschnitten `chat`, `summary`, `rag` (bzw. `embedding`) |
| 3 | `config/chat/llm_models.yml` | `model` und `label` |

Die IDs `llama_lokal` und `granite_lokal` bleiben gleich, dann muss `general.yml` nicht
angefasst werden. `context_length` darf 4096 nicht überschreiten (`OLLAMA_CONTEXT_LENGTH`).
Danach:

```powershell
docker compose run --rm modelle-laden
docker compose up -d --force-recreate chat summary rag
docker compose run --rm warmup
```

`--force-recreate` statt `restart`, damit die Container die geänderten, einzeln gemounteten
Dateien sicher neu einlesen.

## Fehlerbehebung

| Problem | Was tun |
| --- | --- |
| **RAM reicht nicht** (alles hängt, Container starten neu) | `docker stats --no-stream` zeigt, wer wie viel braucht. Im Task-Manager (Leistung → Arbeitsspeicher, Details → `vmmemWSL`) die Gesamtlast ansehen. Teams, Outlook und alle anderen Programme schließen, im Browser nur einen Tab offen lassen. Prüfen, ob `.wslconfig` wirkt (nach Änderung immer `wsl --shutdown`). |
| **Erste Antwort sehr langsam** | Das Modell wird erst beim ersten Aufruf geladen. Vorher `docker compose run --rm warmup` ausführen. Auf der CPU sind auch danach einige Sekunden bis zur ersten Antwort normal. |
| **`docker compose build frontend` schlägt fehl** | Der Build holt den Code von `gitlab.opencode.de`. Netz prüfen: `Invoke-WebRequest https://gitlab.opencode.de -UseBasicParsing`. Im Firmennetz ggf. Proxy in Rancher Desktop eintragen. Den Build ausführen, bevor der Rest des Stacks läuft (braucht RAM). |
| **Ein Image lässt sich nicht laden** (`manifest unknown`, `not found`) | `docker compose run --rm versionen` zeigt die vorhandenen Pfade und Tags. Falschen Tag in `.env` korrigieren. Ist der Pfad selbst falsch, die `image:`-Zeile in `docker-compose.yml` anpassen. |
| **Container meldet YAML-Fehler, APISIX startet nicht, Python meldet `\r`** | Windows-Zeilenenden (CRLF). `.gitattributes` erzwingt LF, aber ein Editor kann CRLF zurückschreiben. Prüfen: `git ls-files --eol config werkzeuge`. Betroffene Datei im Editor auf **LF** umstellen (VS Code: unten rechts „CRLF“ → „LF“). Besonders heikel: `config/secrets/feedback_db.secret` (kein Zeilenende am Schluss) und `config/core/apisix-guest.yaml` (letzte Zeile `#END`). |
| **Umlaute in PowerShell kaputt** | `[Console]::OutputEncoding = [Text.Encoding]::UTF8` in der Sitzung ausführen. |
| **<http://localhost:9999> nicht erreichbar**, obwohl `docker compose ps` alles als laufend zeigt | Rancher Desktop neu starten. Hilft das nicht, ist die Bindung an `127.0.0.1` das Problem; der Kommentar beim Dienst `frontend` in `docker-compose.yml` beschreibt die Abhilfe (dann ist der Port aber im Netz sichtbar). |
| **`pruefen` meldet ✘** | 1–2 Minuten warten (Elasticsearch und Chat brauchen beim Start), dann `docker compose ps` und die Logs des betroffenen Dienstes ansehen. |

## Dokumentation

| Datei | Inhalt |
| --- | --- |
| [docs/ARCHITEKTUR.md](docs/ARCHITEKTUR.md) | Wie der Stack aufgebaut ist und wie Anfragen fließen |
| [docs/DEMO-SKRIPT.md](docs/DEMO-SKRIPT.md) | Klick-für-Klick-Ablauf der Vorführung am 09.11.2026 |
| [docs/MESSWERTE.md](docs/MESSWERTE.md) | Vorlage für Modellvergleich, RAM-Messung und RAG-Trefferquote |
| [docs/VERIFIZIEREN.md](docs/VERIFIZIEREN.md) | Ungeprüfte Annahmen und wie man sie prüft |
| [docs/PLAN.md](docs/PLAN.md) | Ursprünglicher Plan |
| [demo-data/rag/testfragen.md](demo-data/rag/testfragen.md) | Testfragen mit Antwortschlüssel |

## Hinweise

- **Pokémon-Inhalte sind frei erfunden** und nur für den internen Gebrauch. Alle Texte sind
  selbst geschrieben; es gibt keine offiziellen Logos oder Bilder. Nicht veröffentlichen.
- F13 steht unter der MPL-2.0. Die angepasste `config/core/apisix-guest.yaml` behält ihren
  Lizenzkopf. Eigene Dateien dieses Repos: siehe [LICENSE](LICENSE).
- Kein Branding: Das Frontend v3.0.1 bietet keine Branding-Konfiguration, daher bleibt das
  Standard-Design.
