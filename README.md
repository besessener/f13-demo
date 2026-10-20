# F13-Demo: lokale KI-Assistenz mit Pokémon-Wissensbasis

[![Stack-Test](https://github.com/besessener/f13-demo/actions/workflows/stack-test.yml/badge.svg)](https://github.com/besessener/f13-demo/actions/workflows/stack-test.yml)

[F13](https://gitlab.opencode.de/f13), die Open-Source-KI-Assistenz des Landes
Baden-Württemberg, läuft hier vollständig lokal auf einem Windows-Laptop mit 8 GB RAM und
ohne GPU. Ein kleines Sprachmodell (Ollama) bedient Chat, Zusammenfassung und Recherche (RAG).
Für die Recherche gibt es eine erfundene Wissensbasis zu Pokémon-Vorschriften
(`demo-data/rag/`).

## Voraussetzungen

- Windows 11 mit 8 GB RAM und Git
- [Rancher Desktop](https://rancherdesktop.io/): Container Engine **`dockerd (moby)`**,
  **Kubernetes aus**
- `%UserProfile%\.wslconfig` mit folgendem Inhalt, danach `wsl --shutdown` und Rancher
  Desktop neu starten:

  ```ini
  [wsl2]
  memory=5GB
  swap=4GB
  ```

## Starten

```powershell
git clone https://github.com/besessener/f13-demo.git C:\Projekte\f13-demo
```

Danach `start.cmd` doppelklicken:
- startet alle Container
- prüft jeden Dienst
- lädt die Modelle vor
- öffnet <http://localhost:9999>

Der erste Start braucht Internet: mehrere GB Images plus ca. 2,6 GB Modelle. Danach läuft
alles offline.

Beenden mit `stopp.cmd`.

## Befehle

| Aufgabe | Befehl |
| --- | --- |
| Status | `docker compose ps` |
| Logs | `docker compose logs -f --tail 100 <dienst>` |
| Dienste prüfen | `docker compose run --rm pruefen` |
| Modelle vorladen | `docker compose run --rm warmup` |
| Echte Anfragen an Chat, Summary, RAG | `docker compose run --rm smoke-test` |
| Vorführung im Terminal (ohne Browser) | `docker compose run --rm vorfuehrung` |
| Modelle vergleichen (Tempo, RAM) | `docker compose run --rm modellvergleich` (→ `ausgabe/modellvergleich.md`) |
| Testfragen ohne RAG (Gegenprobe) | `docker compose run --rm testfragen` |
| Verfügbare F13-Image-Tags | `docker compose run --rm versionen` |
| API-Beschreibungen der Dienste | `docker compose run --rm api-doku` (→ `ausgabe/openapi/`) |
| Zurücksetzen | `docker compose restart chat summary rag` |
| Stoppen | `docker compose down` |

`docker compose down -v` löscht auch die heruntergeladenen Modelle.

## Konfiguration

Versionen, Ports und Modelle stehen in `.env`. Für ein anderes Sprachmodell nur
`LLM_MODELL` ändern und `start.cmd` erneut ausführen. Beim Start legt `modelle-laden` daraus
die festen Namen `f13-sprachmodell` und `f13-embedding` an, unter denen F13 die Modelle
anspricht. `LLM_MAX_TOKENS` begrenzt die Länge jeder Antwort.

## Fehlerbehebung

| Problem | Lösung |
| --- | --- |
| Zu wenig RAM | `docker stats --no-stream`. Andere Programme schließen. Prüfen, ob `.wslconfig` greift. |
| Erste Antwort langsam | `docker compose run --rm warmup` |
| Image nicht gefunden | `docker compose run --rm versionen`, dann Tag in `.env` anpassen |
| YAML-Fehler oder `\r` in Logs | Datei hat Windows-Zeilenenden. Im Editor auf LF umstellen. |

## Test

[`.github/workflows/stack-test.yml`](.github/workflows/stack-test.yml) startet bei jedem Push
den kompletten Stack mit den echten F13-Images und einem Mini-Modell (`qwen2.5:0.5b`). Danach
laufen `pruefen` und `smoke-test`.

## Doku

- [docs/ARCHITEKTUR.md](docs/ARCHITEKTUR.md): Aufbau und Anfragefluss
- [docs/DEMO-SKRIPT.md](docs/DEMO-SKRIPT.md): Ablauf der Vorführung
- [docs/MESSWERTE.md](docs/MESSWERTE.md): Modellvergleich, RAM, RAG-Trefferquote
- [docs/VERIFIZIEREN.md](docs/VERIFIZIEREN.md): offene Annahmen
- [demo-data/rag/testfragen.md](demo-data/rag/testfragen.md): Testfragen mit Antwortschlüssel

## Lizenz

Eigene Dateien: [MIT](LICENSE). F13 und die daraus übernommene
`config/core/apisix-guest.yaml` stehen unter MPL-2.0.
