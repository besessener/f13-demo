# Verifizieren: ungeprüfte Annahmen (Phase 1)

Der Stack wurde **ohne Zugriff auf `gitlab.opencode.de`** zusammengestellt und **noch nie
gegen die echten F13-Images getestet**. Diese Liste prüfe ich in Phase 1 (Mi 21.10.) auf
meinem Rechner, wo openCode erreichbar ist. Im Repo sind die betroffenen Stellen mit
`ANNAHME (ungeprüft)` markiert.

Zu jeder Annahme: was angenommen wird, wo es steht, wie ich es prüfe und was ich tue, wenn
es falsch ist. Ergebnis jeweils im Kästchen abhaken und kurz notieren.

## Stand: In der CI geprüft

Der Workflow „Stack-Test“ startet den Stack mit den echten F13-Images auf einem GitHub-Runner.
Damit sind diese Punkte geklärt:

| Annahme | Ergebnis |
| --- | --- |
| Image-Pfade und Tags (chat v3.0.0, summary v4.1.0, rag v3.1.1, parser v2.1.5, feedback v1.0.1) | ✔ existieren, Pull ohne Anmeldung |
| Frontend v3.0.1 | ✔ baut aus dem Repo `frontend` (nicht `f13-frontend`) |
| Konfigurationspfade `/<dienst>/configs/` | ✔ werden gelesen |
| Chat-Anfrageformat (`/chat/completion`) | ✔ Antwort über Core |
| Summary-Anfrageformat (`/summary/text`, `/summary/file`) | ✔ laut OpenAPI, `/summary/text` liefert eine Zusammenfassung |
| RAG ohne Reranker | ✘ RAG verlangt `reranking`. Gelöst mit dem Dienst `reranker`. |
| Frontend ohne Transkription | ✘ nginx erwartet `tusd`. Gelöst mit einem Netzwerk-Alias. |
| Summary ohne Token-Grenze | ✘ lief endlos. `max_tokens: 800` in `config/f13/llm_models.yml` hat allein nicht gereicht (siehe „Endlose Antworten kleiner Modelle“). Ob Summary den Wert überhaupt auswertet, ist offen. |
| APISIX-Standard-Timeout | ✘ 60 s zu kurz. Gelöst mit 900 s für chat, summary, rag. |
| RAG im Dateimodus (`/rag/file`) | ✔ Antwort mit Quellen (Datei und Seite). Die Pipeline des Images erwartet die ID `test_model_mock`; die ist als Alias vorhanden. |
| Endlose Antworten kleiner Modelle | ✘ Ein Summary-Abschnitt hing 15 Minuten. Gelöst mit `f13-sprachmodell` (`num_predict` = `LLM_MAX_TOKENS`). |

Die Abschnitte unten sind die ursprüngliche Checkliste. Offen sind noch zwei Punkte: der
Datenbankmodus von RAG (Befüllen von Elasticsearch) und die Antwortqualität mit
`llama3.2:3b` auf dem Laptop. Die CI nutzt ein 0,5B-Modell, das zwar die richtigen Quellen
bekommt, aber oft falsch antwortet.

## Übersicht

| Nr. | Thema | Wichtig für | Erledigt |
| --- | --- | --- | --- |
| A1 | Image-Pfade und Tags von summary, rag, parser | Start | ☐ |
| A2 | F13-Images anonym ladbar | Start | ☐ |
| A3 | Tags der Drittimages und Ollama-Modelle existieren | Start | ☐ |
| B1 | Config-Pfade `/<dienst>/configs/` | Start | ☐ |
| B2 | Schlüssel in `general.yml` / `llm_models.yml` passen | Start | ☐ |
| B3 | Vorhandene `prompt_maps` je Image | Chat, Summary, RAG | ☐ |
| B4 | Bedeutung von `api.timeout` | Chat, Summary | ☐ |
| C1 | RAG läuft ohne Reranker | RAG | ☐ |
| C2 | Elasticsearch-Version passt zum RAG-Dienst | RAG | ☐ |
| C3 | Eingabeformat der OPA-Abfrage | Chat | ☐ |
| C4 | Gastmodus ohne Keycloak | alle | ☐ |
| C5 | Granite-Embedding: 512 Tokens vs. `split_length` | RAG | ☐ |
| D1 | Frontend v3.0.1 baut aus dem Git-Kontext | Start | ☐ |
| D2 | `API_URL` wirkt zur Laufzeit | Start | ☐ |
| D3 | Recherche: Datei-Upload (Datei-Modus); Datenbank-Modus | RAG | ☐ |
| D4 | Datei-Modus verarbeitet Dateien pro Frage neu | Demo-Zeitplan | ☐ |
| D5 | Oberfläche und Ports funktionieren offline und nur auf `127.0.0.1` | Souveränität | ☐ |

## Hilfsbefehle: in ein Image schauen, ohne es zu starten

```powershell
# Arbeitsverzeichnis, Startbefehl, Umgebungsvariablen
docker image inspect registry.opencode.de/f13/microservices/summary:v4.1.0 --format "{{.Config.WorkingDir}} | {{.Config.Entrypoint}} {{.Config.Cmd}} | {{.Config.Env}}"

# Verzeichnis ansehen
docker run --rm --platform linux/amd64 --entrypoint ls registry.opencode.de/f13/microservices/summary:v4.1.0 -la /summary/configs

# Datei suchen
docker run --rm --platform linux/amd64 --entrypoint find registry.opencode.de/f13/microservices/summary:v4.1.0 / -name "prompt_maps*" -not -path "/proc/*"

# Startlogs eines Dienstes
docker compose logs --tail 100 summary
```

Gibt es im Image kein `ls`/`find`, hilft die README bzw. das `Dockerfile` im jeweiligen Repo
auf `gitlab.opencode.de/f13/microservices/…`.

---

## A. Images

### A1 Image-Pfade und Tags von summary, rag, parser

- **Annahme:** `registry.opencode.de/f13/microservices/summary:v4.1.0`, `…/rag:latest`,
  `…/parser:v2.1.5`. Tags für chat (`v3.0.0`) und feedback (`v1.0.1`) gelten als bekannt,
  werden aber mitgeprüft.
- **Wo:** `.env` (`F13_*_VERSION`), `docker-compose.yml` (`image:`).
- **Prüfen:** `docker compose run --rm versionen`. Zeigt je Dienst Pfade und Tags aus dem
  openCode-Registry.
- **Falls falsch:** Tag in `.env` korrigieren; anderer Pfad → `image:` in
  `docker-compose.yml`. `rag:latest` durch einen festen Tag ersetzen, sobald einer bekannt
  ist. Gibt es für einen Dienst gar kein Image: im Repo nachsehen, ob es aus dem Git-Kontext
  baubar ist (wie beim Frontend).

### A2 F13-Images anonym ladbar

- **Annahme:** `registry.opencode.de` erlaubt anonymes Pullen.
- **Prüfen:** `docker compose pull --ignore-buildable`. Fehler `unauthorized` / `denied`?
- **Falls falsch:** Bei openCode anmelden und `docker login registry.opencode.de` mit einem
  Token mit Leserecht auf das Registry.

### A3 Tags der Drittimages und der Modelle

- **Annahme:** `ollama/ollama:0.40.6`, `apache/apisix:3.15.0-ubuntu`,
  `openpolicyagent/opa:1.18.1-debug`, `elasticsearch:8.19.23`, `postgres:18-alpine`,
  `python:3.15-alpine` existieren; Ollama-Modelle `llama3.2:3b` und
  `granite-embedding:278m` ebenso.
- **Prüfen:** `docker compose pull --ignore-buildable`, dann
  `docker compose run --rm modelle-laden`.
- **Falls falsch:** Nächsten passenden Tag auf Docker Hub bzw. ollama.com/library wählen und in
  `.env` eintragen (Modelle: auch die drei Stellen aus der README, „Modell wechseln“).

## B. Konfiguration

### B1 Config-Pfade `/<dienst>/configs/`

- **Annahme:** summary, rag und parser lesen ihre Configs wie chat und feedback aus
  `/summary/configs/`, `/rag/configs/`, `/parser/configs/` (`general.yml`,
  `llm_models.yml`).
- **Wo:** `docker-compose.yml` (Volumes), `config/f13/*.yml`.
- **Prüfen:** Mit den Hilfsbefehlen oben `ls -la /<dienst>/configs` im Image. Liegen dort
  Beispieldateien, ist der Pfad richtig. Außerdem Startlogs: Meldungen wie „config not found“
  oder Standardwerte statt unserer Modelle.
- **Falls falsch:** Mount-Ziele in `docker-compose.yml` auf den echten Pfad ändern. Liegen im
  Ordner weitere Dateien (z. B. `prompt_maps.yml`), weiter **einzelne Dateien** mounten,
  nicht den Ordner.

### B2 Schlüssel in `general.yml` und `llm_models.yml`

- **Annahme:** summary, rag, parser und feedback akzeptieren die gemeinsame `general.yml` und
  `llm_models.yml` im Format von core v3.0.0 (inkl. `embedding`, `document_splitter_config`,
  `max_chunks_to_use`).
- **Prüfen:** Startlogs aller vier Dienste nach Validierungsfehlern durchsehen
  (`docker compose logs summary rag parser feedback | Select-String -Pattern "error|validation"`).
  Beispiel-Configs im Image oder Repo vergleichen.
- **Falls falsch:** Schlüssel nach Beispiel-Config anpassen. Braucht ein Dienst eine eigene
  Variante, eine eigene Datei unter `config/<dienst>/` anlegen.

### B3 Vorhandene `prompt_maps` je Image

- **Annahme:** Diese Prompt-Maps sind im jeweiligen Image enthalten: chat
  `base_assistant`, summary `map_reduce_summarizer`, rag `base_answer_generator`.
- **Wo:** `prompt_map` in `config/chat/llm_models.yml` und `config/f13/llm_models.yml`.
- **Prüfen:** `prompt_maps*` im Image suchen (Hilfsbefehle oben) und mit `cat` ansehen:
  Welche Namen gibt es, sind die Prompts deutsch? Startlogs auf „KeyError“ o. Ä. prüfen.
- **Falls falsch:** Namen in `llm_models.yml` korrigieren. Eigene Prompts nur als eigene
  `prompt_maps.yml` mounten; im Chat ist als geschweifte Klammer nur `{current_date}`
  erlaubt (Python `str.format`).

### B4 Bedeutung von `api.timeout`

- **Annahme:** `timeout` in `llm_models.yml` ist in **Sekunden** und gilt für die ganze
  Anfrage an Ollama (chat 600, summary 900; `llm_api_timeout: 600` in `general.yml`).
- **Prüfen:** Schema bzw. Beispiel-Config im chat-Repo lesen. Praxistest: lange Antwort im
  Chat anfordern (z. B. „Schreibe 800 Wörter über …“) und messen, ob sie vollständig ankommt;
  Chat-Logs auf `Timeout` prüfen.
- **Falls falsch:** Bei Millisekunden die Werte ×1000; bei Lese-Timeout pro Token sind kleinere
  Werte unkritisch. Bei Abbrüchen Wert erhöhen oder `max_new_tokens` senken.

## C. Dienste

### C1 RAG läuft ohne Reranker

- **Annahme:** Ohne Abschnitt `reranking` in `llm_models.yml` startet und antwortet RAG.
- **Wo:** `config/f13/llm_models.yml` (Abschnitt bewusst weggelassen).
- **Prüfen:** `docker compose logs rag` beim Start; `docker compose run --rm pruefen`
  (`/rag/llms`); eine Frage im Reiter Recherche.
- **Falls falsch:** In Doku/Beispiel-Config nach einer Option zum Abschalten suchen. Sonst
  einen Reranker eintragen, der über eine OpenAI-kompatible API erreichbar ist; das kostet
  RAM und gehört in die Go/No-Go-Rechnung ([MESSWERTE.md](MESSWERTE.md)).

### C2 Elasticsearch-Version passt zum RAG-Dienst

- **Annahme:** RAG arbeitet mit `elasticsearch:8.19.23`.
- **Prüfen:** Im rag-Repo die Compose-Datei/README auf die dort genutzte ES-Version prüfen.
  Version des Python-Clients im Image:
  `docker run --rm --platform linux/amd64 --entrypoint pip <rag-image> show elasticsearch`.
  RAG-Logs auf Verbindungs- oder Header-Fehler prüfen.
- **Falls falsch:** `ELASTICSEARCH_VERSION` in `.env` auf die passende Hauptversion setzen
  (Faustregel: Client-Hauptversion = Server-Hauptversion). Danach `es-daten` neu anlegen
  (nur dieses Volume: `docker volume rm f13-demo_es-daten` bei gestopptem Stack; **nie**
  `down -v`).

### C3 Eingabeformat der OPA-Abfrage

- **Annahme:** Chat fragt OPA mit `input.tools`, `input.user.roles` und
  `input.user.authenticated` im Paket `f13.tools.permissions` ab. OPA wird nur für die
  Werkzeugfreigabe im agentischen Chat gefragt, nicht bei jeder einfachen Chat-Anfrage
  (so beschrieben in [ARCHITEKTUR.md](ARCHITEKTUR.md)).
- **Wo:** `config/opa/policies/permissions.rego`.
- **Prüfen:** Chat starten und eine Anfrage stellen, dann `docker compose logs opa`. Die
  Decision-Logs (`decision_logs.console=true`) zeigen Pfad und tatsächliche Eingabe. Zum
  Vergleich die Beispiel-Policy im chat- oder core-Repo.
- **Falls falsch:** Paketnamen und Feldnamen in `permissions.rego` anpassen. OPA lädt die
  Datei dank `--watch` ohne Neustart.

### C4 Gastmodus ohne Keycloak

- **Annahme:** Mit `guest_mode: true` (Core-`general.yml`) und `KEYCLOAK_DISABLED=true`
  (Frontend) wird Keycloak nie angesprochen; die Platzhalter-URL `http://keycloak:8080`
  stört nicht.
- **Prüfen:** Oberfläche öffnen: kein Login, keine Weiterleitung. Logs aller Dienste auf
  Verbindungsfehler zu `keycloak` prüfen.
- **Falls falsch:** In der Doku nach weiteren Gast-Schaltern suchen. Keycloak nur als letzte
  Möglichkeit ergänzen (RAM).

### C5 Granite-Embedding: 512 Tokens vs. `split_length`

- **Annahme:** `split_length: 180` und `split_overlap: 30` zählen **Wörter** (Haystack-Standard
  `split_by: word`). 180 Wörter × 1,5–2 Tokens ≈ 270–360 Tokens, also unter der Grenze von
  512 Tokens des Modells.
- **Wo:** `config/f13/llm_models.yml`, `document_splitter_config`.
- **Prüfen:** Im rag-Repo nachsehen, welches `split_by` gilt. RAG- und Ollama-Logs beim
  Hochladen auf Warnungen zu Länge oder Kürzung prüfen. Inhaltlich: Kommen Fakten vom Ende
  längerer Paragraphen in den Antworten an?
- **Falls falsch:** Bei `split_by: sentence` o. Ä. Werte deutlich senken (z. B. wenige Sätze);
  bei Zeichen/Token entsprechend umrechnen. Im Zweifel `split_length` verkleinern.

## D. Frontend und Demo-Pfad

### D1 Frontend v3.0.1 baut aus dem Git-Kontext

- **Annahme:** `docker compose build frontend` baut direkt aus
  `https://gitlab.opencode.de/f13/microservices/frontend.git#v3.0.1` (Dockerfile im
  Wurzelverzeichnis, keine Build-Argumente nötig), und das Image lauscht auf 9999.
- **Prüfen:** Build ausführen; `docker compose logs frontend` nach dem Start;
  `docker compose run --rm pruefen`.
- **Falls falsch:** Dockerfile-Pfad oder Build-Argumente in `docker-compose.yml` (`build:`)
  ergänzen. Bei Speichermangel im Build: den Build bei gestopptem Stack ausführen.

### D2 `API_URL` wirkt zur Laufzeit

- **Annahme:** `API_URL` (und `KEYCLOAK_DISABLED`) werden beim Containerstart gelesen, nicht
  beim Build fest eingebaut.
- **Prüfen:** Oberfläche öffnen, F12 → Netzwerk: Gehen die API-Aufrufe an
  `http://localhost:8000/…`? CORS-Fehler in der Konsole?
- **Falls falsch:** Die Werte als `build.args` in `docker-compose.yml` mitgeben und
  `docker compose build frontend` erneut ausführen.

### D3 Recherche: Datei-Modus und Datenbank-Modus

- **Annahme:** Der Reiter **Recherche** erlaubt das Hochladen von Dateien und fragt dann
  `/rag/file` (Datei-Modus). Das ist der Hauptweg der Demo. Der Datenbank-Modus
  (`/rag/database`, `/rag/sources`) braucht einen befüllten Elasticsearch-Index; wie der
  befüllt wird, ist unbekannt.
- **Prüfen:** In der Oberfläche: Gibt es Upload und ggf. eine Auswahl Datei/Datenbank? F12 →
  Netzwerk: Welche Route wird aufgerufen? Im rag-Repo nach der Befüllung des Index suchen
  (Endpunkt, Skript oder eigener Job).
- **Falls falsch:** Kein Upload in der Recherche → Datenbank-Modus wird Pflicht; das wäre eine
  Aufgabe für Phase 6 und ein Risiko für den Zeitplan. Der Datenbank-Modus ist sonst
  **optional**; nur einbauen, wenn die Befüllung dokumentiert und günstig ist.

### D4 Datei-Modus verarbeitet Dateien pro Frage neu

- **Annahme:** Im Datei-Modus werden die PDFs bei jeder Frage erneut geparst und eingebettet.
- **Prüfen:** Zwei Fragen nacheinander stellen und die Zeiten messen; in `docker compose logs
  parser` sehen, ob bei jeder Frage geparst wird. Werte in [MESSWERTE.md](MESSWERTE.md).
- **Falls zutreffend und zu langsam:** Im Demo-Skript nur die zwei Pflichtfragen live stellen;
  ggf. nur die nötigen PDFs hochladen (z. B. nur `01_vwv_pokehaltung.pdf`) und das offen
  sagen.

### D5 Offline und nur auf `127.0.0.1`

- **Annahme:** Die Oberfläche lädt keine externen Ressourcen (Schriften, CDN), und die
  Port-Weiterleitung von Rancher Desktop funktioniert mit `127.0.0.1:` und ohne Netz.
- **Prüfen:** In der Generalprobe WLAN aus (und LAN-Kabel ab), Seite neu laden (Strg + F5),
  eine Frage stellen. F12 → Netzwerk: Anfragen an fremde Hosts? Außerdem prüfen, dass die
  Funktion „Onlinesuche“ ohne MCP-Server nichts kaputt macht.
- **Falls falsch:** Fehlende externe Ressourcen hinnehmen, wenn nur die Optik leidet, und es
  ansprechen. Ist `http://localhost:9999` mit `127.0.0.1:`-Bindung nicht erreichbar, steht in
  `docker-compose.yml` beschrieben, wie man die Bindung entfernt. Dann ist der Dienst aber im
  Netz sichtbar: in der Demo nicht behaupten, die Ports seien nur lokal, und die
  Windows-Firewall prüfen.

---

## Weitere Annahmen aus der Implementierung

Diese Punkte stammen aus dem Bau von Stack, Werkzeugen und Wissensbasis. Was oben schon
behandelt ist, steht hier nicht noch einmal.

| Nr | Annahme | Wo | Prüfen | Falls falsch |
| --- | --- | --- | --- | --- |
| W1 | Die F13-Python-Images enthalten `python` und lauschen auf Port 8000. Der Healthcheck prüft nur, ob der Port offen ist. | `docker-compose.yml`, `x-f13-dienst` | `docker compose ps`: Sind chat, summary, rag, parser und feedback „healthy“? | Healthcheck anpassen oder entfernen. Nichts hängt davon ab, weil core nur `service_started` voraussetzt. |
| W2 | `split_length`/`split_overlap` zählen **Wörter** (Haystack-Standard `split_by: word`). | `config/f13/llm_models.yml` | RAG-Logs: Warnungen zum Token-Limit von granite-embedding (512)? | `split_length` verkleinern, z. B. 120 |
| W3 | Die `/llms`-Endpunkte liefern eine Liste mit `label`. | `werkzeuge/pruefen.py` | `docker compose run --rm pruefen` | Betrifft nur die Anzeige, nicht die Bewertung ✔/✘ |
| W4 | Das Frontend hat keinen Healthcheck, weil unbekannt ist, welche Werkzeuge das Image enthält. | `docker-compose.yml` | `pruefen` prüft es von außen | – |
| W5 | Ports, die an `127.0.0.1:` gebunden sind, erreicht man unter Rancher Desktop (Windows) über `http://localhost`. | `docker-compose.yml`, `ports` | Phase 2: http://localhost:8000/health im Browser | `127.0.0.1:` vor den Ports entfernen. Dann ist die Demo im Netz sichtbar, also Windows-Firewall beachten. |
| W6 | Der Dateimodus der Recherche verarbeitet 2–3-seitige PDFs mit Tabellen sauber. | `demo-data/rag/*.pdf` | Phase 6: Testfragen 1–12 in der Oberfläche | Tabellen in den Markdown-Quellen in Fließtext umschreiben, dann `python3 werkzeuge/pdf_erzeugen.py` |

**Im Test hier gefundene und behobene Abweichungen.** Das sind keine Annahmen mehr:
- APISIX 3.15 startet im Standalone-Modus nur, wenn `config-guest.yaml` zusätzlich als
  `conf/config.yaml` gemountet ist.
- `enable_ipv6: false` ist gesetzt, weil APISIX ohne IPv6 im Container nicht startet.
- `worker_processes: 2` begrenzt den RAM-Verbrauch.
- Elasticsearch läuft mit `xpack.ml.enabled=false`, gemessen ca. 916 MiB.
- core, opa, feedback-db und elasticsearch wurden in der Build-Umgebung gestartet und
  waren alle „healthy“. Die Images von registry.opencode.de, der Frontend-Build und
  Ollama konnten dort nicht getestet werden.
