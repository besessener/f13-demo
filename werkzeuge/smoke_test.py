"""Smoke-Test: schickt je eine echte Anfrage an Ollama und über Core an Chat, Summary und RAG.

Aufruf (PowerShell):  docker compose run --rm smoke-test

Anders als "pruefen" (nur erreichbar ja/nein) prüft dieser Test, ob die Dienste wirklich
antworten. Auf der CPU kann das einige Minuten dauern.

ANNAHME (ungeprüft): Die Anfrageformate für /chat/completion, /summary/text und
/rag/file sind geraten. Bei HTTP 422 zeigt die Ausgabe, welche Felder der Dienst
tatsächlich erwartet. Die echten Formate liefert: docker compose run --rm api-doku

Nur Python-Standardbibliothek.
"""

import json
import os
import sys
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
TIMEOUT_S = int(os.environ.get("SMOKE_TEST_TIMEOUT_S", "900"))

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def senden(url, daten=None, kopf=None):
    """Gibt (Status, Text, Sekunden) zurück. Status 0 = keine Verbindung."""
    anfrage = urllib.request.Request(url, data=daten, headers=kopf or {})
    start = time.monotonic()
    try:
        with OPENER.open(anfrage, timeout=TIMEOUT_S) as antwort:
            text = antwort.read().decode("utf-8", "replace")
            return antwort.status, text, time.monotonic() - start
    except urllib.error.HTTPError as fehler:
        text = fehler.read().decode("utf-8", "replace")
        return fehler.code, text, time.monotonic() - start
    except (urllib.error.URLError, OSError) as fehler:
        return 0, str(fehler), time.monotonic() - start


def json_senden(url, nutzlast):
    return senden(url, json.dumps(nutzlast).encode("utf-8"),
                  {"Content-Type": "application/json"})


def multipart_senden(url, felder, dateien):
    """felder: {name: wert}, dateien: {name: (dateiname, bytes, typ)}"""
    grenze = uuid.uuid4().hex
    teile = []
    for name, wert in felder.items():
        teile.append(f'--{grenze}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'
                     f"{wert}\r\n".encode("utf-8"))
    for name, (dateiname, inhalt, typ) in dateien.items():
        teile.append(f'--{grenze}\r\nContent-Disposition: form-data; name="{name}"; '
                     f'filename="{dateiname}"\r\nContent-Type: {typ}\r\n\r\n'.encode("utf-8")
                     + inhalt + b"\r\n")
    teile.append(f"--{grenze}--\r\n".encode("utf-8"))
    return senden(url, b"".join(teile),
                  {"Content-Type": f"multipart/form-data; boundary={grenze}"})


def kurz(text, laenge=800):
    text = " ".join(text.split())
    return text if len(text) <= laenge else text[:laenge] + " …"


def test_ollama_antwort():
    status, text, sek = json_senden(f"{OLLAMA_URL}/api/generate", {
        "model": LLM_MODELL, "stream": False, "keep_alive": -1,
        "prompt": "Antworte mit genau einem Wort: Welche Farbe hat Pikachu?",
        "options": {"num_predict": 20}})
    if status != 200:
        return False, f"HTTP {status}: {kurz(text)}", sek
    daten = json.loads(text)
    tokens = daten.get("eval_count", 0)
    dauer = (daten.get("eval_duration") or 1) / 1e9
    return True, f"„{daten.get('response', '').strip()}“ ({tokens / dauer:.1f} Tokens/s)", sek


def test_ollama_embedding():
    # Gleicher Weg wie die F13-Dienste: OpenAI-kompatible Schnittstelle.
    status, text, sek = json_senden(f"{OLLAMA_URL}/v1/embeddings", {
        "model": EMBEDDING_MODELL, "input": "Glurak braucht eine Brandschutzfreigabe."})
    if status != 200:
        return False, f"HTTP {status}: {kurz(text)}", sek
    vektor = json.loads(text)["data"][0]["embedding"]
    return True, f"Vektor mit {len(vektor)} Dimensionen", sek


def test_chat():
    status, text, sek = json_senden(f"{CORE_URL}/chat/completion", {
        "language_model": F13_MODELL_ID,
        "chat_history": [],
        "new_message": {"role": "user", "content": "Antworte nur mit dem Wort: Hallo"}})
    return status == 200, f"HTTP {status}: {kurz(text)}", sek


def test_summary():
    with open(f"{DATEN}/rag/01_vwv_pokehaltung.md", encoding="utf-8") as datei:
        text = datei.read()[:2500]
    status, antwort, sek = json_senden(f"{CORE_URL}/summary/text", {
        "language_model": F13_MODELL_ID, "text": text})
    return status == 200, f"HTTP {status}: {kurz(antwort)}", sek


def test_rag_datei():
    pfad = f"{DATEN}/rag/01_vwv_pokehaltung.pdf"
    with open(pfad, "rb") as datei:
        inhalt = datei.read()
    status, antwort, sek = multipart_senden(
        f"{CORE_URL}/rag/file",
        {"question": "Welche Pokémon dürfen nicht in den Serverraum?",
         "language_model": F13_MODELL_ID},
        {"files": ("01_vwv_pokehaltung.pdf", inhalt, "application/pdf")})
    return status == 200, f"HTTP {status}: {kurz(antwort)}", sek


TESTS = [
    ("Ollama: Antwort des Sprachmodells", test_ollama_antwort),
    ("Ollama: Embedding (/v1/embeddings)", test_ollama_embedding),
    ("Core → Chat: /chat/completion", test_chat),
    ("Core → Summary: /summary/text", test_summary),
    ("Core → RAG: /rag/file (PDF + Frage)", test_rag_datei),
]


def main():
    print(f"Smoke-Test  (Sprachmodell {LLM_MODELL}, F13-Modell-ID {F13_MODELL_ID})\n")
    fehler = 0
    for name, test in TESTS:
        print(f"▶ {name} …", flush=True)
        try:
            ok, info, sek = test()
        except Exception as grund:  # noqa: BLE001 – jeden Fehler verständlich melden
            ok, info, sek = False, f"{type(grund).__name__}: {grund}", 0.0
        sekunden = f"{sek:.1f}".replace(".", ",")
        print(f"  {'✔' if ok else '✘'} {info}  [{sekunden} s]", flush=True)
        fehler += 0 if ok else 1
    print(f"\n{len(TESTS) - fehler} von {len(TESTS)} Tests bestanden.")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
