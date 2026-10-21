# Architektur der F13-Demo

Hier beschreibe ich, wie ich F13 lokal auf einem Windows-Laptop mit 8 GB RAM betreibe, welche
Rolle jeder Dienst spielt und wie eine Anfrage durch das System läuft.

> Stellen, die auf ungeprüften Annahmen über F13-Interna beruhen, sind mit
> **ANNAHME (ungeprüft)** markiert und in [VERIFIZIEREN.md](VERIFIZIEREN.md) gesammelt.

## Überblick

```
Windows 11 (8 GB RAM)
┌──────────────────────────────────────────────────────────────────────┐
│ Browser                                                              │
│   Oberfläche   http://localhost:9999 ──────────────┐                 │
│   API-Aufrufe  http://localhost:8000 ──────────────┼──────┐          │
│ PowerShell     docker compose …                    │      │          │
│ Repo           C:\Projekte\f13-demo                │      │          │
│                config\, demo-data\, werkzeuge\     │      │          │
│                → als Bind-Mounts in die Container  │      │          │
└────────────────────────────────────────────────────┼──────┼──────────┘
                         nur 127.0.0.1               │      │
┌────────────────────────────────────────────────────┼──────┼──────────┐
│ Rancher Desktop: eigene WSL2-VM                    │      │          │
│ Limit 5 GB + 4 GB Swap, dockerd (moby)             │      │          │
│ ohne Kubernetes, Compose-Projekt „f13-demo“        │      │          │
│                                                    ▼      │          │
│                                            frontend :9999 │          │
│                                                           ▼          │
│  core :8000 = APISIX-Gateway (CORS, Routen, Pfade umschreiben)       │
│     │               │                  │                │            │
│     ▼               ▼                  ▼                ▼            │
│   chat ──► opa    summary            rag ──► elastic- feedback       │
│     │               │   │           │  │     search      │           │
│     │               │   └─► parser ◄┘  │                 ▼           │
│     │               │                  │            feedback-db      │
│     ▼               ▼                  ▼                             │
│  ollama :11434 (nur intern): llama3.2:3b + granite-embedding:278m    │
│                                                                      │
│  Volumes:   ollama-modelle, parser-modelle, zertifikate, es-daten,   │
│             feedback-db-daten                                        │
│  Einmal:    zertifikate, modelle-laden (bei jedem up)                │
│  Werkzeuge: warmup, pruefen, versionen, testfragen, smoke-test, …    │
│             (Profil „werkzeuge“, nur per docker compose run --rm)    │
└──────────────────────────────────────────────────────────────────────┘
```

Nach außen sind nur zwei Ports offen, beide nur an `127.0.0.1`: **9999** (Oberfläche) und
**8000** (Core). Alle anderen Dienste sind nur im internen Compose-Netz per Dienstname
erreichbar, z. B. `http://ollama:11434`.

## Die Dienste

| Dienst | Image | Rolle |
| --- | --- | --- |
| `frontend` | selbst gebaut aus dem Repo `frontend` v3.0.1 (git) | Weboberfläche mit u. a. Chat, Recherche, Zusammenfassung und Transkription (Letztere ohne Backend). Läuft im Gastmodus (`KEYCLOAK_DISABLED=true`). `API_URL=http://localhost:8000`, weil der **Browser** den Core aufruft, nicht der Container. |
| `core` | `apache/apisix` | API-Gateway, das Herzstück von F13 v3. Nimmt alle API-Aufrufe an, setzt CORS-Header, schreibt Pfade um und leitet an die Fachdienste weiter. Läuft „stand-alone“ mit Routen aus einer YAML-Datei, ohne etcd. |
| `chat` | F13 `chat` v3.0.0 | Chat mit dem lokalen LLM. Spricht Ollama über die OpenAI-kompatible API `http://ollama:11434/v1` an. |
| `opa` | Open Policy Agent | Richtlinien-Dienst, ohne den Chat v3 nicht startet. Entscheidet, welche Werkzeuge (Tools) ein Nutzer im agentischen Chat verwenden darf. Meine Minimal-Richtlinie erlaubt alles ohne Rollenbedarf. |
| `summary` | F13 `summary` | Zusammenfassung von Dokumenten per Map-Reduce: Text in Teile schneiden, jeden Teil zusammenfassen, dann die Teilergebnisse zusammenführen. |
| `parser` | F13 `parser` (CPU) | Wandelt PDF/DOCX in Text um. Wird von `summary` und `rag` aufgerufen. Lädt beim ersten Start seine PDF-Modelle (docling) von `huggingface.co` und öffnet erst danach Port 8000. Die Modelle liegen im Volume `parser-modelle`. |
| `rag` | F13 `rag` | Recherche: Dokumente in Abschnitte teilen, Embeddings berechnen, passende Abschnitte suchen und eine Antwort mit Quellen erzeugen. |
| `reranker` | eigener kleiner Dienst (`werkzeuge/reranker.py`) | F13 RAG verlangt einen Reranker mit Cohere-Schnittstelle. Ein echtes Reranking-Modell bräuchte ca. 1 GB RAM. Dieser Dienst sortiert die Treffer stattdessen nach gemeinsamen Stichwörtern mit der Frage (BM25-artig) und braucht ca. 20 MB. Er trägt außerdem den Netzwerknamen `tusd`, den das Frontend-nginx beim Start erwartet. |
| `elasticsearch` | Elasticsearch 8 | Vektor-Datenbank für die Wissensdatenbank von RAG (Index `wissensdatenbank`). Heap auf 512 MB begrenzt. |
| `feedback` + `feedback-db` | F13 `feedback` + Postgres | Speichert Daumen hoch/runter aus der Oberfläche. Für die Demo Nebensache, aber Teil des Standard-Stacks. |
| `zertifikate` | eigener Einmal-Container (`werkzeuge/zertifikate.py`) | Läuft bei jedem `up` vor `parser` und `ollama`. Schreibt die öffentlichen Stammzertifikate plus eigene aus `config/zertifikate/` ins Volume `zertifikate`. `parser`, `ollama` und `versionen` nutzen sie über `SSL_CERT_FILE`. Nötig hinter einem Firmen-Proxy, der HTTPS neu signiert; ohne Proxy nur die öffentlichen. |
| `ollama` | `ollama/ollama` | Führt die Modelle aus: `llama3.2:3b` als LLM für chat/summary/rag (ID `llama_lokal`) und `granite-embedding:278m` für Embeddings (ID `granite_lokal`). |

`summary`, `rag`, `parser` und `feedback` lesen eine gemeinsame `general.yml` und
`llm_models.yml` aus `config/f13/`. `chat` hat eigene Dateien in `config/chat/`, die einzeln
gemountet werden, damit die im Image enthaltene `prompt_maps.yml` erhalten bleibt.

### Routen im Core (APISIX)

Grundlage ist die Gastmodus-Konfiguration aus F13 core v3.0.0
(`config/core/apisix-guest.yaml`). Ich habe nur die Transkription (`transcription`, `tusd`)
entfernt, weil sie in der Demo nicht installiert ist.

| Pfad am Core (`:8000`) | Ziel | Umschreiben |
| --- | --- | --- |
| `/chat/completion`, `/chat/completion/stream`, `/chat/v2/completion/stream`, `/chat/experimental/agentic/completion/stream`, `/chat/llms` | `chat:8000` | `/chat/…` → `/…` |
| `/summary/llms` | `summary:8000` | `/summary/…` → `/…` |
| `/summary/file`, `/summary/text` | `summary:8000` | keins |
| `/rag/file` | `rag:8000` (Datei-Modus) | `/rag/…` → `/…` |
| `/rag/database`, `/rag/sources` | `rag:8000` (Datenbank-Modus) | `/rag/…` → `/…` |
| `/rag/llms` | `rag:8000` | `/rag/…` → `/…` |
| `/feedback/general`, `/feedback/summary`, `/feedback/rag`, `/feedback/chat` | `feedback:8000` | `/feedback/…` → `/…` |
| `/`, `/health` | Core selbst | Antwort `{"status":"F13-Core is running"}` |

Eine globale CORS-Regel erlaubt nur den Ursprung `http://localhost:9999`.

## Ablauf einer Anfrage

### Chat

1. Ich tippe im Reiter **Chat** eine Frage. Die Oberfläche läuft im Browser.
2. Der Browser schickt die Anfrage an `http://localhost:8000/chat/completion/stream`
   (bzw. eine der anderen Chat-Routen).
3. APISIX prüft CORS, schreibt den Pfad auf `/completion/stream` um und leitet an
   `chat:8000` weiter.
4. Der Chat-Dienst baut aus Systemprompt (`prompt_map: base_assistant`), Verlauf und Frage den
   Prompt. **ANNAHME (ungeprüft):** OPA wird nur für die Werkzeugfreigabe im agentischen Chat
   gefragt, nicht bei jeder einfachen Chat-Anfrage.
5. Chat ruft `http://ollama:11434/v1/chat/completions` auf. Ollama erzeugt die Antwort auf
   der CPU.
6. Die Tokens fließen als Stream zurück über APISIX in den Browser.

### Zusammenfassung

1. Im Reiter **Zusammenfassung** lade ich ein PDF hoch.
2. Der Browser schickt es an `http://localhost:8000/summary/file`. APISIX leitet es ohne
   Umschreiben an `summary:8000` weiter.
3. Summary schickt die Datei an `parser:8000` und bekommt Text zurück.
4. Summary schneidet den Text in Teile, lässt jeden Teil von Ollama zusammenfassen (Map) und
   führt die Teilergebnisse zusammen (Reduce), mit `prompt_map: map_reduce_summarizer`.
5. Das Ergebnis geht zurück an den Browser. Auf der CPU sind das mehrere LLM-Aufrufe
   nacheinander; deshalb nur kurze Dokumente.

### Recherche (RAG) im Datei-Modus

Rückfallebene, falls die Wissensdatenbank nicht geladen ist. Der Hauptweg ist die
Wissensdatenbank (nächster Abschnitt).

1. Im Reiter **Recherche** lade ich die 6 PDFs der Wissensbasis hoch und stelle eine Frage.
2. Der Browser schickt Dateien und Frage an `http://localhost:8000/rag/file`. APISIX schreibt
   auf `/file` um und leitet an `rag:8000` weiter.
3. RAG lässt die PDFs vom `parser` in Text umwandeln.
4. RAG teilt den Text in Abschnitte von 180 Wörtern mit 30 Wörtern Überlappung
   (`document_splitter_config`).
5. Für jeden Abschnitt und für die Frage berechnet Ollama mit `f13-embedding` (standardmäßig
   `granite-embedding:278m`) einen Vektor (`/v1/embeddings`).
6. RAG sucht die ähnlichsten Abschnitte. Der Dienst `reranker` (Stichwort-Reranker,
   `werkzeuge/reranker.py`) sortiert sie nach gemeinsamen Stichwörtern mit der Frage. RAG
   nimmt höchstens 3 davon (`max_chunks_to_use: 3`), damit der Prompt in 4096 Tokens passt.
7. Ollama erzeugt mit `f13-sprachmodell` (standardmäßig `llama3.2:3b`) und
   `prompt_map: base_answer_generator` eine Antwort nur aus diesen Abschnitten.
8. Antwort und Quellenangaben gehen zurück an den Browser.

**ANNAHME (ungeprüft):** Im Datei-Modus werden die Dateien bei jeder Frage neu verarbeitet
und nicht dauerhaft gespeichert. Das kostet Zeit pro Frage.

### Wissensdatenbank (Datenbank-Modus)

Der Hauptweg der Demo. Die Dokumente werden einmal verarbeitet statt bei jeder Frage:

1. `start.cmd` ruft `docker compose run --rm wissensbasis` auf (`werkzeuge/wissensbasis.py`).
   Das schickt die sechs Markdown-Fassungen aus `demo-data/rag/` (ohne `testfragen.md`) an
   `rag:8000/database_ingestion`, jeweils mit `source: "Pokémon-Regeln"` und dem Titel des
   Dokuments. Dieser Weg geht nicht über den Core, ist also vom Browser aus nicht erreichbar.
2. RAG teilt die Texte in Abschnitte, berechnet mit `f13-embedding` die Vektoren und
   speichert sie im Elasticsearch-Index `wissensdatenbank`.
3. Ein Prüfsummen-Eintrag im Index `f13-demo-wissensbasis` merkt sich den Stand. Bei
   späteren Starts wird nur neu geladen, wenn sich die Dokumente geändert haben.
4. Die Oberfläche fragt `/rag/sources` ab und zeigt die Quellen aus
   `config/rag/rag_pipeline_config.yml` unter „Wissensdatenbank auswählen“, hier nur
   „Pokémon-Regeln“.
5. Eine Frage geht an `http://localhost:8000/rag/database`, gefiltert auf die gewählte
   Quelle. RAG sucht im Index, sortiert mit dem Reranker, nimmt höchstens 3 Abschnitte und
   lässt `f13-sprachmodell` daraus antworten.

`config/rag/rag_pipeline_config.yml` ist die im Image eingebaute Datei. Geändert sind nur die
Quellen (statt der Beispiele Koalitionsvertrag, Landesdrucksachen, Pressemitteilungen) und
`document_summaries.llm_name: null` (Zusammenfassungen je Dokument braucht nur die
hierarchische Suche, die aus ist).

## Warum Ollama im Container?

- **Keine Installation unter Windows:** keine Adminrechte, kein Dienst, der im Hintergrund
  läuft, nichts, was nach der Demo übrig bleibt.
- **Gepinnte Version** (`OLLAMA_VERSION` in `.env`). Die OpenAI-kompatible API von Ollama
  gilt noch als „experimental“, daher soll sich die Version nicht unbemerkt ändern.
- **Gleiches Netz wie F13:** Die Dienste erreichen Ollama einfach unter `http://ollama:11434`.
  Ollama ist **nicht** zum Host freigegeben.
- **Ein RAM-Topf:** Modell und F13-Dienste teilen sich das 5-GB-Limit der VM. So sehe ich
  mit `docker stats` alles an einer Stelle.
- Nachteil: Ohne GPU läuft alles auf der CPU. Das wäre bei einer Windows-Installation auf
  diesem Laptop aber genauso.

Ollama-Einstellungen für wenig RAM: `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_CONTEXT_LENGTH=4096`,
`OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q8_0`, `OLLAMA_MAX_LOADED_MODELS=2` (LLM und
Embedding gleichzeitig) und `OLLAMA_KEEP_ALIVE=-1` (Modelle bleiben geladen).

## RAM-Budget (8 GB)

| Posten | ca. | Wo |
| --- | --- | --- |
| Windows 11 und Desktop | 2,5 GB | Windows |
| Browser (ein Tab) | 0,5 GB | Windows |
| Rancher-Desktop-Oberfläche | 0,3–0,5 GB | Windows |
| LLM inkl. KV-Cache (4k Kontext) | 2–2,5 GB | VM |
| Embedding-Modell | 0,6 GB | VM |
| F13-Dienste und Elasticsearch | 1,5–2 GB | VM |
| **Summe** | **7,5–8,5 GB, also knapp** | VM-Limit 5 GB + 4 GB Swap |

Jeder Container hat ein `mem_limit`:

| Dienst | Limit |
| --- | --- |
| ollama | 3500 MB |
| elasticsearch | 1200 MB |
| rag, parser | je 900 MB |
| summary, chat | je 500 MB |
| core, feedback, feedback-db | je 256 MB |
| frontend | 200 MB |
| opa, Werkzeuge | je 128 MB |

Die Limits zusammen ergeben ca. 8,6 GB, also mehr als die 5 GB der VM. Das ist Absicht: Ein
Limit ist eine Obergrenze, keine Reservierung. Es verhindert, dass ein einzelner Dienst den
ganzen Speicher frisst. Was tatsächlich belegt ist, messe ich mit `docker stats` und trage es
in [MESSWERTE.md](MESSWERTE.md) ein.

## Datensouveränität

- **Nichts verlässt den Laptop.** Modelle, Dokumente, Embeddings und Antworten bleiben in
  der VM. Es gibt keinen Cloud-Dienst und keinen API-Schlüssel.
- **Ports nur an `127.0.0.1`:** Oberfläche und Core sind nur vom Laptop selbst erreichbar,
  nicht aus dem WLAN oder Firmennetz.
- **Keine externe Websuche:** Im agentischen Chat sind keine MCP-Server eingetragen
  (`tools.mcp_endpoints: []` in `config/chat/agentic_chat.yml`). Das Frontend zeigt die
  Funktion „Onlinesuche“ im Gastmodus zwar an, ohne MCP-Server gibt es aber nichts, was sie
  aufrufen könnte (**ANNAHME (ungeprüft)**, in der Generalprobe ausprobieren).
- **Netz nur bei der Einrichtung:** Images, Modelle und der Frontend-Code werden einmal
  geladen. Danach läuft die Demo auch mit ausgeschaltetem WLAN; genau das zeige ich in der
  Vorführung.
- Kein Login (Gastmodus, kein Keycloak). Für eine lokale Einzelplatz-Demo ist das
  vertretbar, für den Produktivbetrieb nicht.

## Lizenzen

| Bestandteil | Lizenz | Hinweis |
| --- | --- | --- |
| F13 (Frontend, Core, Chat, Summary, RAG, Parser, Feedback) | MPL-2.0 | Images werden nur gezogen, nicht weitergegeben. |
| `config/core/apisix-guest.yaml` | MPL-2.0 | Aus F13 core v3.0.0 übernommen und angepasst. Der SPDX-Kopf bleibt erhalten, ergänzt um den Hinweis „angepasst für f13-demo“. MPL-2.0 gilt pro Datei: Die geänderte Datei bleibt MPL-2.0. |
| Eigene Dateien dieses Repos | siehe `LICENSE` | |
| Llama 3.2 | Llama 3.2 Community License | Bei Weitergabe Lizenzbedingungen beachten |
| Granite Embedding | Apache-2.0 | |
| Ollama, APISIX, OPA, Postgres | MIT, Apache-2.0, Apache-2.0, PostgreSQL License | |
| Elasticsearch | Elastic License 2.0 / AGPL-3.0 / SSPL | Interne Nutzung unkritisch, vor jeder Weitergabe prüfen |
| Pokémon-Wissensbasis | eigene, erfundene Texte | Nur intern; Pokémon ist eine Marke Dritter, keine offiziellen Logos oder Bilder |
