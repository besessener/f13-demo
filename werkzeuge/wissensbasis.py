"""Lädt die Pokémon-Wissensbasis in die Datenbank von F13-RAG (Elasticsearch).

Aufruf (PowerShell):  docker compose run --rm wissensbasis
start.cmd ruft das bei jedem Start auf.

Schickt die sechs Dokumente aus demo-data/rag/ (0*.md, ohne testfragen.md) an
POST /database_ingestion des RAG-Dienstes. RAG teilt sie in Abschnitte, berechnet die
Embeddings und speichert sie im Index „wissensdatenbank“. Danach beantwortet
POST /rag/database Fragen daraus, ohne dass Dateien hochgeladen werden müssen.

Lädt nur, wenn sich die Dokumente geändert haben oder der Index leer ist. Der Stand (eine
Prüfsumme) liegt im Index „f13-demo-wissensbasis“. Neu laden erzwingen: NEU=1.

Nur Python-Standardbibliothek.
"""

import glob
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

RAG_URL = os.environ.get("RAG_URL", "http://rag:8000").rstrip("/")
ES_URL = os.environ.get("ELASTICSEARCH_URL", "http://elasticsearch:9200").rstrip("/")
DATEN = os.environ.get("DEMO_DATEN", "/demo-data")
# Muss zu "sources" in config/rag/rag_pipeline_config.yml passen.
QUELLE = os.environ.get("WISSENSBASIS_QUELLE", "Pokémon-Regeln")
INDEX = "wissensdatenbank"  # pipeline.index.database in rag_pipeline_config.yml
STAND_INDEX = "f13-demo-wissensbasis"
NEU = os.environ.get("NEU", "0") == "1"
# Embeddings für alle Abschnitte auf der CPU (Sekunden).
TIMEOUT_S = int(os.environ.get("WISSENSBASIS_TIMEOUT_S", "1800"))

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def anfrage(methode, url, daten=None, timeout=60):
    """Gibt (Status, JSON oder Text) zurück; Status 0 = keine Verbindung."""
    koerper = json.dumps(daten).encode("utf-8") if daten is not None else None
    req = urllib.request.Request(url, data=koerper, method=methode,
                                 headers={"Content-Type": "application/json"})
    try:
        with OPENER.open(req, timeout=timeout) as antwort:
            status, text = antwort.status, antwort.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as fehler:
        status, text = fehler.code, fehler.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError) as fehler:
        return 0, str(fehler)
    try:
        return status, json.loads(text)
    except ValueError:
        return status, text


def dokumente():
    """Die Dokumente der Wissensbasis als Liste für /database_ingestion."""
    ergebnis = []
    for pfad in sorted(glob.glob(f"{DATEN}/rag/0*.md")):
        with open(pfad, encoding="utf-8") as datei:
            text = datei.read()
        titel = re.match(r"#\s+(.+)", text)
        ergebnis.append({
            "content": re.sub(r"\*\*", "", text).strip(),
            "meta": {"source": QUELLE,
                     "title": titel.group(1).strip() if titel else os.path.basename(pfad)},
        })
    return ergebnis


def pruefsumme(docs):
    return hashlib.sha256(json.dumps(docs, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def anzahl_abschnitte():
    anfrage("POST", f"{ES_URL}/{INDEX}/_refresh")
    status, daten = anfrage("GET", f"{ES_URL}/{INDEX}/_count")
    return daten.get("count", 0) if status == 200 and isinstance(daten, dict) else 0


def gespeicherter_stand():
    status, daten = anfrage("GET", f"{ES_URL}/{STAND_INDEX}/_doc/stand")
    if status == 200 and isinstance(daten, dict):
        return (daten.get("_source") or {}).get("pruefsumme")
    return None


def main():
    docs = dokumente()
    if not docs:
        print(f"✘ Keine Dokumente unter {DATEN}/rag/0*.md gefunden.")
        return 1
    stand = pruefsumme(docs)
    print(f"Wissensbasis „{QUELLE}“: {len(docs)} Dokumente")
    for d in docs:
        print(f"  • {d['meta']['title']}")

    vorhanden = anzahl_abschnitte()
    if not NEU and vorhanden and gespeicherter_stand() == stand:
        print(f"\n✔ Schon geladen ({vorhanden} Abschnitte im Index „{INDEX}“), nichts zu tun.")
        return 0

    if vorhanden:
        print(f"\nAlter Stand ({vorhanden} Abschnitte) wird gelöscht …", flush=True)
        status, daten = anfrage("POST", f"{ES_URL}/{INDEX}/_delete_by_query?refresh=true",
                                {"query": {"match_all": {}}})
        if status != 200:
            print(f"✘ Löschen fehlgeschlagen (HTTP {status}): {str(daten)[:300]}")
            return 1

    print("\nLade die Dokumente in die Wissensbasis (Embeddings auf der CPU, kann dauern) …",
          flush=True)
    start = time.monotonic()
    for versuch in range(1, 13):
        status, daten = anfrage("POST", f"{RAG_URL}/database_ingestion", {"documents": docs},
                                timeout=TIMEOUT_S)
        if status != 0:
            break
        # RAG startet vielleicht noch.
        print(f"  RAG nicht erreichbar ({daten}), neuer Versuch in 10 s …", flush=True)
        time.sleep(10)
    dauer = time.monotonic() - start
    if status != 200:
        print(f"✘ /database_ingestion: HTTP {status}: {str(daten)[:500]}")
        return 1

    abschnitte = anzahl_abschnitte()
    if not abschnitte:
        print(f"✘ RAG meldet Erfolg, aber der Index „{INDEX}“ ist leer: {str(daten)[:300]}")
        return 1
    anfrage("PUT", f"{ES_URL}/{STAND_INDEX}/_doc/stand?refresh=true",
            {"pruefsumme": stand, "quelle": QUELLE, "dokumente": len(docs)})
    print(f"✔ {abschnitte} Abschnitte im Index „{INDEX}“ ({dauer:.0f} s).")
    print(f"  Antwort von RAG: {json.dumps(daten, ensure_ascii=False)[:300]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
