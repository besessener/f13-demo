# F13-Demo – Plan

Status: **Entwurf v2.** Die Eckdaten stehen fest. Offen sind nur noch die Hardware-Details in §9.

## 1. Ziel

Die Demo ist intern und dient als **Nachweis für meine Zielvereinbarung**. Ich zeige, dass ich F13
verstehe, selbst betreiben kann und anderen vorführen kann.

| Eckdaten | Festgelegt |
| --- | --- |
| Zielgruppe | Intern: Führungskraft und Kolleg:innen |
| Betrieb | **Vollständig lokal**, nur CPU, keine Cloud, keine GPU |
| Modell | Kleines Open-Weight-Modell (3–4 B) über **Ollama** |
| Funktionen | Chat, Zusammenfassung, **RAG** |
| RAG-Thema | **Pokémon** (siehe §4) |
| Sprache | **Nur Deutsch**: Oberfläche, Wissensbasis, Prompts, Doku |

## 2. Was ist F13?

F13 ist die Open-Source-KI-Assistenz des Landes Baden-Württemberg. Entwickelt wurde sie
vom InnoLab_bw mit PD, betrieben wird sie bei BITBW. Seit dem 23.07.2025 steht sie unter
MPL-2.0 auf openCode: <https://gitlab.opencode.de/f13>.

F13 besteht aus Microservices. Ein zentraler **Core** verbindet das Frontend mit den
Fachdiensten:

| Repo (`gitlab.opencode.de/f13/microservices/…`) | Rolle in der Demo |
| --- | --- |
| `frontend` / `f13-frontend` | Weboberfläche |
| `core` | Schnittstelle zwischen Frontend und Diensten (v3: APISIX-Gateway) |
| `chat` | Chat mit lokalem LLM |
| `summary` | Zusammenfassung von Dokumenten (Map-Reduce) |
| `parser` | PDF/DOCX → Text (CPU-Image, zuletzt gesehen v2.1.5) |
| `rag` | Suche in natürlicher Sprache über die Pokémon-Wissensbasis |

> **Noch nicht verifiziert:** Diese Punkte stammen aus Sekundärquellen und werden in Phase 1
> gegen die offiziellen READMEs geprüft:
> - Frontend-Stack (React oder Svelte)
> - Gastmodus oder Keycloak-Login in v3
> - OPA-Sidecar für Chat v3
> - Welches Embedding-Modell und welche Vektor-DB RAG nutzt, und ob sich beides über
>   Ollama betreiben lässt
>
> `gitlab.opencode.de` war in der Umgebung, in der dieser Plan entstand, gesperrt.

## 3. Architektur (lokal, nur CPU)

```
Browser ──► Frontend ──► Core (APISIX) ──┬─► Chat ─────────────┐
                                         ├─► Summary ──► Parser├─► Ollama :11434
                                         └─► RAG ──► Vektor-DB ┘    ├─ LLM (3–4 B, Q4)
                                                                    └─ Embeddings (bge-m3)
```

Ollama stellt unter `http://<host>:11434/v1/` eine OpenAI-kompatible API bereit, mit
`/v1/chat/completions` und `/v1/embeddings`. Laut offizieller Doku ist diese Schicht noch
„experimental“. Deshalb pinnen wir die Ollama-Version.

### Modellwahl

Wir machen in Phase 2 einen Vergleich mit 5 deutschen Test-Prompts. Kandidaten:

| Modell | Ollama-Tag | Größe (Q4) | Warum |
| --- | --- | --- | --- |
| Qwen 3.5 4B | `qwen3.5:4b` | ca. 3,4 GB | Wird 2026 am häufigsten für CPU-only empfohlen |
| Llama 3.2 3B | `llama3.2:3b` | ca. 2 GB | Deutsch offiziell unterstützt, schnell |
| Gemma 4 (klein) | `gemma4:*` | ca. 1,5–3 GB | Schnellste Option, Deutsch ungetestet |
| **Embeddings:** BGE-M3 | `bge-m3` | ca. 1,2 GB | Mehrsprachig und stark für Deutsch; 8k Kontext |

Bewertet werden: korrektes Deutsch, Treue zu den Quellen bei RAG, Tokens pro Sekunde auf
meinem Rechner. Die genauen Tags und Größen prüfen wir vor dem Download auf ollama.com/library.

### Ressourcenbudget (Annahme: 16 GB RAM)

LLM ca. 4–5 GB, Embeddings ca. 1,5 GB, Vektor-DB ca. 1–2 GB, F13-Dienste ca. 2–3 GB.
Das passt in **16 GB**. Mit 8 GB wird es eng: dann nehmen wir das kleinste Modell und
lassen Dienste weg, wo es geht.

## 4. RAG-Thema: „Landesamt für Pokémon-Angelegenheiten Kanto“

**Idee:** Eine erfundene Behörde mit erfundenen Verwaltungsvorschriften rund um Pokémon. Das
verbindet den Verwaltungskontext von F13 mit dem Nerd-Faktor.

**Warum erfunden?**
1. **Beweiskraft:** Das Modell kann diese Regeln nicht aus dem Training kennen. Eine
   richtige Antwort beweist also, dass RAG funktioniert.
2. **Keine Lizenzfragen:** Alle Texte schreiben wir selbst. Wir kopieren nichts aus Wikis,
   übernehmen keine offiziellen Bilder oder Sprites und veröffentlichen nichts außerhalb der
   Firma.
3. **Kontrollierbar:** Zu jeder Testfrage gibt es eine bekannte richtige Antwort mit
   Fundstelle.

### Wissensbasis (`demo-data/rag/`, je 1–3 Seiten, als PDF und Markdown)

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

## 5. Ablauf der Vorführung (ca. 10–12 Min.)

1. **Einstieg (1 Min.):** Was ist F13, und warum ist der lokale Betrieb wichtig? Ich zeige
   kurz die Architekturskizze.
2. **Chat (2 Min.):** Ablehnungsbescheid für einen Arenalizenz-Antrag in **Leichter
   Sprache** schreiben lassen.
3. **Zusammenfassung (2 Min.):** Die VwV PokéHaltung als PDF hochladen und eine
   Kurzfassung mit Stichpunkten erzeugen.
4. **RAG (4 Min.):** Die Testfragen stellen und die Quellenangaben zeigen. Danach die
   Gegenprobe ohne RAG.
5. **Souveränität (1 Min.):** WLAN aus und noch eine Frage stellen. Alles läuft weiter.
6. **Grenzen und Fazit (2 Min.):** Geschwindigkeit auf CPU, Qualität eines 4B-Modells,
   was der Produktivbetrieb bräuchte (GPU, größeres Modell).

## 6. Phasen

| Phase | Inhalt | Aufwand |
| --- | --- | --- |
| **1. Erkundung** | Repos klonen und READMEs lesen. Versionen in `versions.env` pinnen. Die offenen Punkte aus §2 klären. | ½–1 Tag |
| **2. Ollama und Modelle** | Ollama installieren, Kandidaten laden, Vergleich mit deutschen Prompts, `curl`-Rauchtest gegen `/v1/chat/completions` und `/v1/embeddings` | ½ Tag |
| **3. Minimal-Stack Chat** | Eigene `docker-compose.yml` mit Frontend, Core und Chat gegen Ollama. `make up`; Chat läuft im Browser. | 1 Tag |
| **4. Zusammenfassung + Parser** | Summary und CPU-Parser einbinden, mit Dokument 1 testen | ½ Tag |
| **5. Wissensbasis schreiben** | Die 6 Dokumente aus §4 und den Antwortschlüssel schreiben, PDFs erzeugen | ½–1 Tag |
| **6. RAG** | RAG-Dienst und Vektor-DB einbinden, Wissensbasis indexieren, Testfragen durchlaufen lassen und Trefferquote notieren | 1 Tag |
| **7. Vorführreife** | `docs/DEMO-SKRIPT.md`, `scripts/healthcheck.sh`, `scripts/reset.sh`, Modelle vorladen (Warm-up), Bildschirmaufnahme als Fallback, Generalprobe | ½–1 Tag |

**Gesamt: ca. 4–6 Tage.**

## 7. Nachweis für die Zielvereinbarung

| Nachweis | Ablage |
| --- | --- |
| Lauffähiges Repo mit Commit-Historie | dieses Repo |
| **Lerntagebuch**: was ich gelernt habe, Probleme und Lösungen, pro Phase | `docs/LERNTAGEBUCH.md` |
| Architekturerklärung in eigenen Worten | `docs/ARCHITEKTUR.md` |
| Ergebnis des Modellvergleichs und Messwerte der RAG-Testfragen | `docs/MESSWERTE.md` |
| Vorführung live und als Aufzeichnung | Termin und Datei |
| Anleitung „In 15 Minuten selbst starten“ für Kolleg:innen | `README.md` |

## 8. Repo-Struktur

```
f13-demo/
├── README.md                 # Schnellstart (Deutsch)
├── Makefile                  # make up / down / check / reset / index
├── docker-compose.yml        # kompletter Demo-Stack
├── versions.env              # gepinnte F13-Images, Ollama-Version, Modell-Tags
├── config/                   # Dienst-Konfiguration (llm_models.yml, Prompts, …)
├── demo-data/
│   ├── summary/              # Dokument für die Zusammenfassung
│   └── rag/                  # Pokémon-Wissensbasis + testfragen.md
├── scripts/                  # healthcheck.sh, reset.sh, warmup.sh
└── docs/
    ├── PLAN.md               # dieses Dokument
    ├── DEMO-SKRIPT.md
    ├── ARCHITEKTUR.md
    ├── LERNTAGEBUCH.md
    └── MESSWERTE.md
```

## 9. Risiken

| Risiko | Gegenmaßnahme |
| --- | --- |
| Antworten auf CPU zu langsam | Kleinstes brauchbares Modell, kurze Dokumente, Warm-up vor der Vorführung, Kontextlänge begrenzen |
| 4B-Modell halluziniert trotz RAG | Antwortschlüssel; Prompt „nur aus Quellen antworten“; Fragen wählen, die zuverlässig klappen |
| RAG-Dienst erwartet ein Embedding-Modell oder eine DB, die nicht zu Ollama passt | Phase 1 klärt das. Notfalls läuft das Embedding-Modell als eigener Container. |
| Upstream-Doku unvollständig oder nicht passend zu v3 | Versionen pinnen, eigene Compose-Datei, Probleme im Lerntagebuch festhalten |
| Login (Keycloak) blockiert | Für die Demo den Gastmodus nutzen |
| Zu wenig RAM | Modell oder Dienste verkleinern; siehe §3 |
| Markenrecht Pokémon | Nur intern, nur eigene Texte, keine offiziellen Bilder, keine Veröffentlichung |

## 10. Noch offen

1. **Rechner:** Betriebssystem (Windows, macOS oder Linux), RAM, CPU. Ist Docker Desktop
   bzw. Docker Engine erlaubt und installiert?
2. **Termin** der Vorführung

## Quellen

- [F13 KI Assistenz – EU-OSS-Katalog](https://interoperable-europe.ec.europa.eu/eu-oss-catalogue/solutions/f13-ki-assistenz)
- [F13 KI Assistenz – openCode](https://opencode.de/de/software/f-13-ki-assistenz-5250)
- [Staatsanzeiger: F13 wird Open Source](https://www.staatsanzeiger.de/nachrichten/politik-und-verwaltung/f13-wird-open-source-baden-wuerttemberg-bringt-ki-in-die-verwaltung/)
- [Treffpunkt Kommune: F13 wird Open-Source-Software](https://www.treffpunkt-kommune.de/der-startschuss-fuer-ein-souveraenes-europaeisches-ki-oekosystem-ki-assistenz-f13-wird-open-source-software/)
- [f13-os.de – Kennenlernen](https://f13-os.de/kennenlernen/)
- F13-Repos: [Gruppe](https://gitlab.opencode.de/f13), [Chat](https://gitlab.opencode.de/f13/microservices/chat), [Core](https://gitlab.opencode.de/f13/microservices/core), [Frontend](https://gitlab.opencode.de/f13/microservices/frontend), [Summary](https://gitlab.opencode.de/f13/microservices/summary), [Parser-Releases](https://gitlab.opencode.de/f13/microservices/parser/-/releases), [RAG](https://gitlab.opencode.de/f13/microservices/rag)
- [Ollama – OpenAI-Kompatibilität](https://docs.ollama.com/api/openai-compatibility.md)
- [Ollama – bge-m3](https://registry.ollama.ai/library/bge-m3)
- [Embedding-Modelle für Deutsch 2026 – WZ-IT](https://wz-it.com/blog/embedding-modelle-deutsch-vergleich/)
- [Best CPU-only local LLMs 2026 – Popular AI](https://www.popularai.org/p/best-cpu-only-local-llm-2026)
- [Qwen 3.5 mit Ollama – Apidog](https://apidog.com/blog/use-qwen-3-5-with-ollama/)
- [Ollama-Qwen-Tags – AgenticWire](https://www.agenticwire.news/article/ollama-qwen)
