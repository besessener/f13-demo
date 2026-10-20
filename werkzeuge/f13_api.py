"""Gemeinsame Aufrufe der F13-API über Core – genutzt von smoke-test und vorfuehrung.

Die Anfrageformate stammen aus den OpenAPI-Beschreibungen der echten Dienste
(docker compose run --rm api-doku). Nur Python-Standardbibliothek.
"""

import json
import os
import time
import urllib.error
import urllib.request
import uuid

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434").rstrip("/")
CORE_URL = os.environ.get("CORE_URL", "http://core:8000").rstrip("/")
LLM_MODELL = os.environ.get("LLM_MODELL", "llama3.2:3b")
EMBEDDING_MODELL = os.environ.get("EMBEDDING_MODELL", "granite-embedding:278m")
F13_MODELL_ID = os.environ.get("F13_MODELL_ID", "llama_lokal")
DATEN = os.environ.get("DEMO_DATEN", "/demo-data")
TIMEOUT_S = int(os.environ.get("F13_TIMEOUT_S", "900"))

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def senden(url, daten=None, kopf=None):
    """Gibt (Status, Text, Sekunden) zurück. Status 0 = keine Verbindung."""
    anfrage = urllib.request.Request(url, data=daten, headers=kopf or {})
    start = time.monotonic()
    try:
        with OPENER.open(anfrage, timeout=TIMEOUT_S) as antwort:
            return antwort.status, antwort.read().decode("utf-8", "replace"), time.monotonic() - start
    except urllib.error.HTTPError as fehler:
        return fehler.code, fehler.read().decode("utf-8", "replace"), time.monotonic() - start
    except (urllib.error.URLError, OSError) as fehler:
        return 0, str(fehler), time.monotonic() - start


def json_senden(url, nutzlast):
    return senden(url, json.dumps(nutzlast).encode("utf-8"), {"Content-Type": "application/json"})


def multipart_senden(url, felder, dateien):
    """felder: {name: wert}, dateien: [(feldname, dateiname, bytes, typ), …]"""
    grenze = uuid.uuid4().hex
    teile = []
    for name, wert in felder.items():
        teile.append(f'--{grenze}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'
                     f"{wert}\r\n".encode("utf-8"))
    for feld, dateiname, inhalt, typ in dateien:
        teile.append(f'--{grenze}\r\nContent-Disposition: form-data; name="{feld}"; '
                     f'filename="{dateiname}"\r\nContent-Type: {typ}\r\n\r\n'.encode("utf-8")
                     + inhalt + b"\r\n")
    teile.append(f"--{grenze}--\r\n".encode("utf-8"))
    return senden(url, b"".join(teile), {"Content-Type": f"multipart/form-data; boundary={grenze}"})


def pdf(pfad):
    with open(pfad, "rb") as datei:
        return ("file", os.path.basename(pfad), datei.read(), "application/pdf")


# --- Aufrufe ------------------------------------------------------------------------

def chat(nachricht, verlauf=None):
    """POST /chat/completion – ChatInput (chat v3.0.0)."""
    return json_senden(f"{CORE_URL}/chat/completion", {
        "language_model": F13_MODELL_ID,
        "chat_history": verlauf or [],
        "new_message": {"role": "user", "content": nachricht}})


def zusammenfassung_text(text):
    """POST /summary/text – SummaryTextAPIInput (summary v4.1.0)."""
    return json_senden(f"{CORE_URL}/summary/text", {"language_model": F13_MODELL_ID, "text": text})


def zusammenfassung_datei(pfad):
    """POST /summary/file – multipart: file, language_model (summary v4.1.0)."""
    return multipart_senden(f"{CORE_URL}/summary/file", {"language_model": F13_MODELL_ID}, [pdf(pfad)])


def recherche_dateien(pfade, frage):
    """POST /rag/file – ANNAHME (ungeprüft): Feldnamen bis zur ersten OpenAPI-Auswertung geraten."""
    return multipart_senden(
        f"{CORE_URL}/rag/file",
        {"question": frage, "language_model": F13_MODELL_ID},
        [("files",) + pdf(p)[1:] for p in pfade])


def ohne_rag(frage):
    """Gegenprobe: dieselbe Frage direkt an das Sprachmodell, ohne Dokumente."""
    return json_senden(f"{OLLAMA_URL}/api/chat", {
        "model": LLM_MODELL, "stream": False,
        "messages": [{"role": "system", "content": "Antworte knapp auf Deutsch."},
                     {"role": "user", "content": frage}]})


def text_aus(antwort_text):
    """Holt den eigentlichen Text aus einer F13-Antwort, egal wie das Feld heißt."""
    try:
        daten = json.loads(antwort_text)
    except ValueError:
        return antwort_text.strip()
    if isinstance(daten, dict):
        for schluessel in ("response", "summary", "answer", "message", "content"):
            wert = daten.get(schluessel)
            if isinstance(wert, str) and wert.strip():
                return wert.strip()
            if isinstance(wert, dict) and isinstance(wert.get("content"), str):
                return wert["content"].strip()
    return json.dumps(daten, ensure_ascii=False, indent=2)


def quellen_aus(antwort_text):
    """Liefert Quellenangaben einer RAG-Antwort, falls vorhanden."""
    try:
        daten = json.loads(antwort_text)
    except ValueError:
        return []
    kandidaten = []
    if isinstance(daten, dict):
        for schluessel in ("sources", "documents", "quellen", "references"):
            if isinstance(daten.get(schluessel), list):
                kandidaten = daten[schluessel]
                break
    quellen = []
    for eintrag in kandidaten:
        if isinstance(eintrag, dict):
            meta = eintrag.get("meta") or {}
            name = (eintrag.get("source") or eintrag.get("title") or meta.get("source")
                    or meta.get("file_name") or eintrag.get("url") or "")
            quellen.append(str(name) or json.dumps(eintrag, ensure_ascii=False)[:120])
        else:
            quellen.append(str(eintrag)[:120])
    return quellen
