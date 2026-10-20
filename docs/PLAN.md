# F13-Demo – Plan

Status: **Umsetzung gestartet (v8).** Stack, Werkzeuge, Wissensbasis und Doku liegen im Repo.
Was noch nicht gegen das echte F13 geprüft ist, steht in [`VERIFIZIEREN.md`](VERIFIZIEREN.md).

## 1. Ziel

Die Demo ist intern und dient als **Nachweis für meine Zielvereinbarung**. Ich zeige, dass ich F13
verstehe, selbst betreiben kann und anderen vorführen kann.

| Eckdaten | Festgelegt |
| --- | --- |
| Zielgruppe | Intern: Führungskraft und Kolleg:innen |
| Termin | **Mo, 09.11.2026** (in 20 Tagen) |
| Rechner | **Windows, 8 GB RAM, keine GPU** |
| Betrieb | **Vollständig lokal**, keine Cloud |
| Modell | Kleines Open-Weight-Modell (2–3 B) über **Ollama** |
| Funktionen | Chat, Zusammenfassung, **RAG** |
| RAG-Thema | **Pokémon** (siehe §4) |
| Sprache | **Nur Deutsch**: Oberfläche, Wissensbasis, Prompts, Doku |
| Branding | **Entfällt.** F13-Frontend v3.0.1 hat keine Branding-Konfiguration (siehe §5). |

## 2. Was ist F13?

F13 ist die Open-Source-KI-Assistenz des Landes Baden-Württemberg. Entwickelt wurde sie
vom InnoLab_bw mit PD, betrieben wird sie bei BITBW. Seit dem 23.07.2025 steht sie unter
MPL-2.0 auf openCode: <https://gitlab.opencode.de/f13>.

F13 besteht aus Microservices. Ein zentraler **Core** verbindet das Frontend mit den
Fachdiensten:

| Repo (`gitlab.opencode.de/f13/microservices/…`) | Rolle in der Demo |
| --- | --- |
| `f13-frontend` (React) / `frontend` (Svelte) | Weboberfläche |
| `core` | Schnittstelle zwischen Frontend und Diensten (v3: APISIX-Gateway) |
| `chat` | Chat mit lokalem LLM |
| `summary` | Zusammenfassung von Dokumenten (Map-Reduce) |
| `parser` | PDF/DOCX → Text (CPU-Image, zuletzt gesehen v2.1.5) |
| `rag` | Suche in natürlicher Sprache über die Pokémon-Wissensbasis |

> **Noch nicht verifiziert:** Diese Punkte stammen aus Sekundärquellen und werden in Phase 1
> gegen die offiziellen READMEs geprüft:
> - Welches Frontend v3 nutzt
> - Gastmodus oder Keycloak-Login
> - OPA-Sidecar für Chat v3
> - Welches Embedding-Modell und welche Vektor-DB RAG nutzt, und ob sich beides über
>   Ollama betreiben lässt
> - ~~Welche Branding-Optionen es gibt~~: keine, siehe §5
>
> `gitlab.opencode.de` war in der Umgebung, in der dieser Plan entstand, gesperrt.

## 3. Architektur und Betrieb mit Windows und 8 GB RAM

```
Windows 11                                                   Rancher Desktop (intern: eigene WSL2-VM, Limit 5 GB)
┌───────────────────────────────┐                            ┌───────────────────────────────────────────────────────────────┐
│ Browser → http://localhost    │──────── localhost ───────► │ dockerd (moby), Kubernetes AUS                                │
│ PowerShell → docker compose … │──────── docker CLI ──────► │  Frontend ─► Core (APISIX) ─┬─► Chat ─────────────┐           │
│ Repo: C:\…\f13-demo           │── Bind-Mounts (config/, ─► │                             ├─► Summary ─► Parser ├─► Ollama  │
│ Rancher-Desktop-Oberfläche    │   demo-data/)              │                             └─► RAG ─► Vektor-DB ─┘   :11434  │
└───────────────────────────────┘                            │  Volumes: Modelle, Vektor-DB                                  │
                                                             └───────────────────────────────────────────────────────────────┘
```

Ollama stellt unter `http://ollama:11434/v1/` eine OpenAI-kompatible API bereit, mit
`/v1/chat/completions` und `/v1/embeddings`. Laut offizieller Doku ist diese Schicht noch
„experimental“. Deshalb pinnen wir die Ollama-Version.

### Windows-Setup: Windows + Container, sonst nichts

Alles läuft **unter Windows mit Rancher Desktop**:
- Bedient wird nur über PowerShell und den Browser.
- **Alles andere läuft in Containern**, auch Ollama und die Hilfsaufgaben.
- Es gibt keine eigene Linux-Distribution, kein `make` und keine Bash-Skripte.

> Hinweis: Rancher Desktop nutzt unter Windows intern immer WSL2 und bringt dafür seine
> eigene, versteckte VM mit. Wir arbeiten darin aber nie direkt. Wichtig ist das nur für
> das Speicherlimit, siehe Schritt 3.

**Einrichtung (Phase 2):**
1. Rancher Desktop installieren. Voraussetzung ist, dass WSL2 in Windows aktiviert ist,
   dafür braucht man ggf. **Adminrechte** (siehe §11). Version in `versions.env` notieren.
2. **Einstellungen** in Rancher Desktop:
   - **Container Engine: `dockerd (moby)`**, nicht `containerd`. Dann funktionieren
     `docker` und `docker compose` direkt in PowerShell. Achtung: Ein späterer Wechsel der
     Engine verwirft die geladenen Images.
   - **Kubernetes: aus.** k3s würde unnötig RAM kosten.
3. **Speicherlimit:** Unter Windows hat Rancher Desktop **keine** eigene RAM-Einstellung.
   Das Limit steht in `%UserProfile%\.wslconfig`:
   ```ini
   [wsl2]
   memory=5GB   # Rest (~3 GB) bleibt für Windows, Rancher-Oberfläche und Browser
   swap=4GB     # Sicherheitsnetz gegen Abstürze, langsam
   ```
   Danach in PowerShell `wsl --shutdown` ausführen und Rancher Desktop neu starten. Ob
   `autoMemoryReclaim` zusätzlich hilft, prüfen wir in Phase 2.
4. Repo ganz normal unter Windows klonen, z. B. nach `C:\Projekte\f13-demo`.
   - Per Bind-Mount gehen nur kleine Dateien (`config/`, `demo-data/`) in die Container.
     Das bleibt schnell genug.
   - Modelle und Vektor-DB liegen in Docker-Volumes, also in der VM, und sind dort schnell.
5. Smoke-Test in PowerShell: `docker run --rm hello-world` und `docker compose version`

### Bedienung: nur `docker compose`

| Aufgabe | Befehl (PowerShell) |
| --- | --- |
| Starten | `docker compose up -d` |
| Status und Health | `docker compose ps`. Healthchecks sind in der Compose-Datei definiert. |
| Modelle laden (einmalig) | `docker compose run --rm modelle-laden` |
| Wissensbasis indexieren | `docker compose run --rm rag-index` |
| Warm-up vor der Vorführung | `docker compose run --rm warmup` |
| Zurücksetzen (Chat-Verlauf, Uploads) | `docker compose run --rm reset` |
| Stoppen | `docker compose down`. **Ohne `-v`**, sonst sind die Modelle weg. |

Die Hilfsaufgaben sind kleine Container (z. B. ein `curl`-Image) mit dem Compose-Profil
`werkzeuge`. Sie starten deshalb nicht mit `up`.

So braucht es **keine PowerShell-Skripte**, die die Ausführungsrichtlinie auf
Firmenrechnern oft blockiert.

### Modellwahl für 8 GB

Wir machen in Phase 2 einen Vergleich mit 5 deutschen Test-Prompts:

| Modell | Ollama-Tag | Größe (ca.) | Warum |
| --- | --- | --- | --- |
| Llama 3.2 3B | `llama3.2:3b` | 2 GB | Deutsch offiziell unterstützt; **Favorit** |
| Gemma 4 (klein) | `gemma4` (E2B) | 1,5 GB | Kleinste und schnellste Option; Deutsch ungetestet |
| Qwen 3.5 2B | `qwen3.5:2b` | 2,7 GB | Gut bewertet, aber größer als erwartet |
| ~~Qwen 3.5 4B~~ | `qwen3.5:4b` | 3,4 GB | Passt mit 8 GB voraussichtlich **nicht** |
| **Embeddings:** Granite Embedding 278M | `granite-embedding:278m` | 0,6 GB | Mehrsprachig mit Deutsch, klein. Max. 512 Tokens pro Abschnitt, daher kurze Abschnitte in der Wissensbasis. |
| Embeddings (Alternative) | `bge-m3` | 1,2 GB | Besser, aber nur wenn genug RAM übrig ist |

Bewertet werden: korrektes Deutsch, Treue zu den Quellen bei RAG, Tokens pro Sekunde. Die
genauen Tags und Größen prüfen wir vor dem Download auf ollama.com/library.

### RAM-Budget (8 GB)

| Posten | ca. | Wo |
| --- | --- | --- |
| Windows 11 und Desktop | 2,5 GB | Windows |
| Browser (nur ein Tab) | 0,5 GB | Windows |
| Rancher-Desktop-Oberfläche | 0,3–0,5 GB | Windows |
| LLM inkl. KV-Cache (4k Kontext) | 2–2,5 GB | Container |
| Embedding-Modell | 0,6 GB | Container |
| F13-Dienste und Vektor-DB | 1,5–2 GB | Container |
| **Summe** | **7,5–8,5 GB, also knapp** | Container-Limit 5 GB + 4 GB Swap |

### Sparmaßnahmen

- Rancher Desktop: Kubernetes aus. Während der Vorführung das Fenster nur minimieren;
  die App muss weiterlaufen.
- Ollama-Einstellungen als `environment` im Compose-Service:
  - `OLLAMA_NUM_PARALLEL=1`
  - `OLLAMA_CONTEXT_LENGTH=4096`
  - `OLLAMA_FLASH_ATTENTION=1` und `OLLAMA_KV_CACHE_TYPE=q8_0`
  - `OLLAMA_MAX_LOADED_MODELS=2` (LLM und Embedding)
  - `OLLAMA_KEEP_ALIVE=-1` während der Vorführung
- `mem_limit` für jeden Container. Falls die Vektor-DB Elasticsearch ist, den Heap auf
  512 MB begrenzen.
- Während der Vorführung Teams, Outlook und alle anderen Programme schließen. Das ist
  unter Windows besonders wichtig, weil dort nur ca. 3 GB übrig bleiben.
- Für die Zusammenfassung nur kurze Dokumente (2–3 Seiten) verwenden.

### Go/No-Go am Fr, 23.10.

Laufen Chat und Embeddings gleichzeitig stabil? Falls nicht, gehen wir in dieser
Reihenfolge zurück:
1. Kleineres Modell (Gemma 4 E2B)
2. Summary-Dienst weglassen und die Zusammenfassung über den Chat zeigen
3. Für die Vorführung einen Rechner mit 16 GB ausleihen

## 4. RAG-Thema: „Landesamt für Pokémon-Angelegenheiten Kanto“

**Idee:** Eine erfundene Behörde mit erfundenen Verwaltungsvorschriften rund um Pokémon. Das
verbindet den Verwaltungskontext von F13 mit dem Nerd-Faktor.

**Warum erfunden?**
1. **Beweiskraft:** Das Modell kann diese Regeln nicht aus dem Training kennen. Eine
   richtige Antwort beweist also, dass RAG funktioniert.
2. **Keine Lizenzfragen:** Alle Texte schreiben wir selbst. Wir kopieren nichts aus Wikis,
   übernehmen keine offiziellen Bilder und veröffentlichen nichts außerhalb der Firma.
3. **Kontrollierbar:** Zu jeder Testfrage gibt es eine bekannte richtige Antwort mit
   Fundstelle.

### Wissensbasis (`demo-data/rag/`)

Je Dokument 1–3 Seiten, als PDF und Markdown. Kurze Paragraphen mit höchstens 512 Tokens,
passend zum Embedding-Modell.

| Nr. | Dokument | Inhalt (Beispiele) |
| --- | --- | --- |
| 1 | **VwV PokéHaltung**: Verwaltungsvorschrift über die Haltung von Pokémon in Dienstgebäuden | § 3: Feuer-Pokémon brauchen eine Brandschutzfreigabe. § 5: Relaxo darf keine Fluchtwege blockieren. § 7: Elektro-Pokémon haben Zutrittsverbot zum Serverraum. § 9: Psycho-Pokémon dürfen nicht an Personalgesprächen teilnehmen. |
| 2 | **ArenaLizO**: Verordnung über die Erteilung von Arenalizenzen | Voraussetzungen (8 Orden, Sachkundenachweis), Gebühr, Fristen, Widerspruch |
| 3 | **GebO Pokécenter**: Gebührenordnung der Pokécenter | Heilung gebührenfrei, Sonderleistungen (z. B. Wiederbelebung bei Fossilien), Ermäßigungen |
| 4 | **Merkblatt Typenwirksamkeit für den Dienstgebrauch** | Echte Typentabelle (Wasser > Feuer usw.), selbst formuliert |
| 5 | **FAQ Bürgeranfragen** des Professor-Eich-Instituts | „Wo melde ich ein entlaufenes Pokémon?“, „Wie beantrage ich einen Pokédex?“ |
| 6 | **Dienstanweisung Pokéball-Inventur** | Jährliche Inventur, Verlustmeldung, Umgang mit Meisterbällen (Verschlusssache) |

### Testfragen mit Antwortschlüssel (`demo-data/rag/testfragen.md`)

| Frage | Erwartete Antwort und Fundstelle |
| --- | --- |
| „Darf ich mein Glurak mit ins Büro bringen?“ | Nur mit Brandschutzfreigabe (VwV PokéHaltung § 3) |
| „Was kostet eine Arenalizenz und wie lange dauert das Verfahren?“ | Betrag und Frist aus ArenaLizO |
| „Welche Pokémon dürfen nicht in den Serverraum?“ | Elektro-Typen (VwV PokéHaltung § 7) |
| „Wer darf Meisterbälle ausgeben?“ | Dienstanweisung Inventur, Abschnitt Verschlusssachen |
| **Gegenprobe:** dieselbe Frage im Chat **ohne** RAG | Das Modell rät oder weiß es nicht. Das zeigt den Unterschied. |

## 5. Branding: entfällt

**Regel:** Wir branden nur, wenn F13 es über die eingebaute Konfiguration erlaubt. Kein
eigenes Image, kein Wrapper, kein Patch.

**Ergebnis der Recherche:** Das Frontend v3.0.1 liest beim Start nur wenige
Env-Variablen, nämlich `API_URL`, Keycloak-Einstellungen und Chat-Limits. Optionen für
Logo, Farben oder Titel gibt es nicht. Die Demo läuft deshalb im **Standard-Design von
F13**. Der Pokémon-Bezug steckt in der Wissensbasis.

## 6. Ablauf der Vorführung (ca. 10–12 Min.)

1. **Einstieg (1 Min.):** Was ist F13, und warum ist der lokale Betrieb wichtig? Ich zeige
   kurz die Architekturskizze.
2. **Chat (2 Min.):** Ablehnungsbescheid für einen Arenalizenz-Antrag in **Leichter
   Sprache** schreiben lassen.
3. **Zusammenfassung (2 Min.):** Die VwV PokéHaltung als PDF hochladen und eine
   Kurzfassung mit Stichpunkten erzeugen.
4. **RAG (4 Min.):** Die Testfragen stellen und die Quellenangaben zeigen. Danach die
   Gegenprobe ohne RAG.
5. **Souveränität (1 Min.):** WLAN aus und noch eine Frage stellen. Alles läuft weiter.
6. **Grenzen und Fazit (2 Min.):** Läuft auf einem Laptop mit 8 GB, aber langsam. Ein
   2–3B-Modell hat begrenzte Qualität. Was der Produktivbetrieb bräuchte (GPU, größeres
   Modell).

## 7. Zeitplan

Heute ist Di, 20.10.2026. Die Demo ist am Mo, 09.11.2026.

| Phase | Inhalt | Wann |
| --- | --- | --- |
| **1. Erkundung** | Checkliste [`VERIFIZIEREN.md`](VERIFIZIEREN.md) abarbeiten. Mit `docker compose run --rm versionen` die echten Image-Tags ermitteln und in `.env` pinnen. | Mi 21.10. |
| **2. Rancher Desktop, Ollama und Modelle** | Rancher Desktop (moby, ohne Kubernetes) und `.wslconfig` einrichten (§3). Ollama-Container starten, Modelle vergleichen, `curl`-Smoke-Test gegen `/v1/chat/completions` und `/v1/embeddings`. RAM messen mit `docker stats` und dem Task-Manager. | Do 22.10. – Fr 23.10. |
| 🚦 **Go/No-Go** | RAM-Test bestanden? Sonst Rückfallstufen aus §3 | **Fr 23.10.** |
| **3. Minimal-Stack Chat** | Eigene `docker-compose.yml` mit Frontend, Core und Chat gegen Ollama. `docker compose up -d`; Chat läuft im Browser. | Mo 26.10. – Di 27.10. |
| **4. Zusammenfassung + Parser** | Summary und CPU-Parser einbinden, mit Dokument 1 testen | Mi 28.10. |
| **5. Wissensbasis** | Die 6 Dokumente und den Antwortschlüssel schreiben, PDFs erzeugen. Kann parallel laufen. | bis Do 29.10. |
| **6. RAG** | RAG-Dienst und Vektor-DB einbinden, indexieren, Testfragen durchlaufen lassen, Trefferquote notieren | Do 29.10. – Mo 02.11. |
| **7. ~~Branding~~** | Entfällt (§5). Die Zeit wird Puffer für RAG. | Di 03.11. |
| **8. Vorführreife** | `docs/DEMO-SKRIPT.md`; Healthchecks und die Hilfscontainer `warmup` und `reset`; Generalprobe auf dem Demo-Rechner und Bildschirmaufnahme als Fallback | Mi 04.11. – Do 05.11. |
| Puffer | Für alles, was länger dauert | Fr 06.11. |
| 🎬 **Demo** | | **Mo 09.11.** |

## 8. Nachweis für die Zielvereinbarung

| Nachweis | Ablage |
| --- | --- |
| Lauffähiges Repo mit Commit-Historie | dieses Repo |
| Architekturerklärung in eigenen Worten | `docs/ARCHITEKTUR.md` |
| Ergebnis des Modellvergleichs, RAM-Messung und Trefferquote der RAG-Testfragen | `docs/MESSWERTE.md` |
| Vorführung live und als Aufzeichnung | 09.11. und Datei |
| Anleitung „In 15 Minuten selbst starten“ für Kolleg:innen | `README.md` |

## 9. Repo-Struktur

```
f13-demo/
├── README.md                 # Schnellstart (Deutsch, PowerShell)
├── docker-compose.yml        # kompletter Demo-Stack, mit mem_limit, Healthchecks und Profil "werkzeuge"
├── .env                      # gepinnte Versionen, Ports, Modell-Tags
├── .gitattributes            # LF-Zeilenenden für alles, was in Container gemountet wird
├── config/
│   ├── core/                 # APISIX (Core) im Gastmodus: Routen + Standalone-Konfiguration
│   ├── chat/                 # Chat v3: general.yml, llm_models.yml, agentic_chat.yml (ohne Websuche)
│   ├── f13/                  # gemeinsame general.yml + llm_models.yml für summary, rag, parser, feedback
│   ├── opa/policies/         # Tool-Berechtigungen (Pflicht für Chat v3)
│   └── secrets/              # lokales Demo-Passwort der Feedback-DB (nie veröffentlicht)
├── werkzeuge/                # modelle_laden, warmup, pruefen, testfragen, versionen (+ pdf_erzeugen)
├── demo-data/
│   ├── summary/              # PDF für die Zusammenfassung
│   └── rag/                  # 6 fiktive Vorschriften (MD + PDF) + testfragen.md
└── docs/
    ├── PLAN.md               # dieses Dokument
    ├── VERIFIZIEREN.md       # Checkliste aller ungeprüften Annahmen (Phase 1)
    ├── DEMO-SKRIPT.md
    ├── ARCHITEKTUR.md
    └── MESSWERTE.md
```

## 10. Risiken

| Risiko | Gegenmaßnahme |
| --- | --- |
| **8 GB RAM reichen nicht** | Sparmaßnahmen aus §3; Go/No-Go am 23.10. mit Rückfallstufen |
| Keine Adminrechte, oder WSL ist per Firmenrichtlinie gesperrt | **Sofort klären** (§11). Ohne WSL2 läuft Rancher Desktop unter Windows nicht. |
| Windows-Zeilenenden (CRLF) zerstören Configs oder Skripte im Container | `.gitattributes` mit `* text=auto eol=lf` |
| Langsame Bind-Mounts von `C:\` | Nur kleine Dateien mounten; Modelle und DB liegen in Volumes |
| `docker compose down -v` löscht die Modelle (mehrere GB neu laden) | In README und DEMO-SKRIPT deutlich warnen; `reset` löscht nur die Demo-Daten |
| Antworten auf CPU zu langsam | Kleines Modell, 4k Kontext, kurze Dokumente, Warm-up vor der Vorführung |
| Kleines Modell halluziniert trotz RAG | Antwortschlüssel; Prompt „nur aus Quellen antworten“; Fragen wählen, die zuverlässig klappen |
| RAG-Dienst erwartet ein Embedding-Modell oder eine DB, die nicht zu Ollama passt | Phase 1 klärt das. Notfalls läuft das Embedding-Modell als eigener Container. |
| Der Weg zum Befüllen der Wissensdatenbank (Ingestion) ist unbekannt | **Hauptweg ist der Dateimodus:** Die 6 PDFs werden in der Recherche hochgeladen. Der Datenbankmodus ist optional (siehe `VERIFIZIEREN.md`). |
| Upstream-Doku unvollständig oder nicht passend zu v3 | Versionen pinnen, eigene Compose-Datei, Probleme in der README festhalten |
| Login (Keycloak) blockiert | Für die Demo den Gastmodus nutzen. Keycloak würde zusätzlich RAM kosten. |
| Zeitplan rutscht | Puffertag am 06.11. und der frei gewordene Branding-Tag; als Erstes fällt die Zusammenfassung weg |
| Markenrecht Pokémon | Nur intern; nur eigene Texte und eigenes Logo; keine offiziellen Logos oder Bilder; keine Veröffentlichung |

## 11. Noch offen

1. **Adminrechte:** Darf ich auf dem Demo-Rechner Rancher Desktop installieren, und ist
   WSL2 erlaubt bzw. schon aktiviert? Wenn nicht: rechtzeitig bei der IT anfragen,
   **spätestens bis Mi 21.10.**

## Quellen

- [F13 KI Assistenz – EU-OSS-Katalog](https://interoperable-europe.ec.europa.eu/eu-oss-catalogue/solutions/f13-ki-assistenz)
- [F13 KI Assistenz – openCode](https://opencode.de/de/software/f-13-ki-assistenz-5250)
- [Staatsanzeiger: F13 wird Open Source](https://www.staatsanzeiger.de/nachrichten/politik-und-verwaltung/f13-wird-open-source-baden-wuerttemberg-bringt-ki-in-die-verwaltung/)
- [Treffpunkt Kommune: F13 wird Open-Source-Software](https://www.treffpunkt-kommune.de/der-startschuss-fuer-ein-souveraenes-europaeisches-ki-oekosystem-ki-assistenz-f13-wird-open-source-software/)
- [f13-os.de – Kennenlernen](https://f13-os.de/kennenlernen/)
- F13-Frontends: [f13-frontend (React)](https://gitlab.opencode.de/f13/microservices/f13-frontend), [frontend (Svelte)](https://gitlab.opencode.de/f13/microservices/frontend)
- F13-Repos: [Gruppe](https://gitlab.opencode.de/f13), [Chat](https://gitlab.opencode.de/f13/microservices/chat), [Core](https://gitlab.opencode.de/f13/microservices/core), [Summary](https://gitlab.opencode.de/f13/microservices/summary), [Parser-Releases](https://gitlab.opencode.de/f13/microservices/parser/-/releases), [RAG](https://gitlab.opencode.de/f13/microservices/rag)
- [Ollama – OpenAI-Kompatibilität](https://docs.ollama.com/api/openai-compatibility.md)
- [Ollama – granite-embedding](https://registry.ollama.ai/library/granite-embedding)
- [Docker Hub – granite-embedding-multilingual](https://hub.docker.com/r/ai/granite-embedding-multilingual)
- [Ollama – bge-m3](https://registry.ollama.ai/library/bge-m3)
- [Ollama – Kontextlänge und KV-Cache (SSD Nodes)](https://www.ssdnodes.com/learn/ollama-context-length-num-ctx)
- [Ollama – FAQ](https://docs.ollama.com/faq)
- [WSL2 – Speicher begrenzen mit .wslconfig (OneUptime, 2026)](https://oneuptime.com/blog/post/2026-02-08-how-to-configure-docker-desktop-memory-and-cpu-limits-on-windows/markdown)
- [WSL 2.0.0 – autoMemoryReclaim (ElevenForum)](https://www.elevenforum.com/t/windows-subsystem-for-linux-wsl-2-0-0-september-2023-update-released.18072/)
- [Rancher Desktop – Container Engine (offizielle Doku)](https://docs.rancherdesktop.io/ui/preferences/container-engine/general/)
- [Rancher Desktop – WSL-Einstellungen (offizielle Doku)](https://docs.rancherdesktop.io/1.7/ui/preferences/wsl/)
- [Rancher Desktop – Releases](https://github.com/rancher-desktop/rancher-desktop/releases), [v1.24.0](https://newreleases.io/project/github/rancher-sandbox/rancher-desktop/release/v1.24.0)
- [Rancher Desktop unter WSL2 (OneUptime, 2026)](https://oneuptime.com/blog/post/2026-03-20-rancher-desktop-wsl2/view)
- [Rancher Desktop – RAM unter Windows nur per .wslconfig (Rancher Slack)](https://slack-archive.rancher.com/t/8505719/hi-team-how-do-we-adjust-the-virtual-memory-in-rancher-deskt)
- [Ollama – Umgebungsvariablen (DEV)](https://dev.to/threesevenths/ollama-environment-variables-362j)
- [Ollama – Out-of-Memory-Fehler (LocalAIMaster)](https://localaimaster.com/blog/ollama-out-of-memory-errors)
- [Best CPU-only local LLMs 2026 – Popular AI](https://www.popularai.org/p/best-cpu-only-local-llm-2026)
- [Ollama-Qwen-Tags – AgenticWire](https://www.agenticwire.news/article/ollama-qwen)
