"""Smoke-Test: schickt je eine echte Anfrage an Ollama und über Core an Chat, Summary und RAG.

Aufruf (PowerShell):  docker compose run --rm smoke-test

Anders als "pruefen" (nur erreichbar ja/nein) prüft dieser Test, ob die Dienste wirklich
antworten. Der Test der Wissensdatenbank setzt "docker compose run --rm wissensbasis" voraus
(macht start.cmd). Auf der CPU kann das einige Minuten dauern. Die Anfragen selbst stehen in
f13_api.py.

Nur Python-Standardbibliothek.
"""

import json
import sys

import f13_api as api


def kurz(text, laenge=600):
    text = " ".join(text.split())
    return text if len(text) <= laenge else text[:laenge] + " …"


def test_ollama_antwort():
    status, text, sek = api.json_senden(f"{api.OLLAMA_URL}/api/generate", {
        "model": api.LLM_MODELL, "stream": False, "keep_alive": -1,
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
    status, text, sek = api.json_senden(f"{api.OLLAMA_URL}/v1/embeddings", {
        "model": api.EMBEDDING_MODELL, "input": "Glurak braucht eine Brandschutzfreigabe."})
    if status != 200:
        return False, f"HTTP {status}: {kurz(text)}", sek
    vektor = json.loads(text)["data"][0]["embedding"]
    return True, f"Vektor mit {len(vektor)} Dimensionen", sek


def test_chat():
    status, text, sek = api.chat("Antworte nur mit dem Wort: Hallo")
    return status == 200, f"HTTP {status}: {kurz(text)}", sek


def test_summary():
    with open(f"{api.DATEN}/rag/01_vwv_pokehaltung.md", encoding="utf-8") as datei:
        text = datei.read()[:2500]
    status, antwort, sek = api.zusammenfassung_text(text)
    return status == 200, f"HTTP {status}: {kurz(antwort)}", sek


def test_rag_datei():
    status, antwort, sek = api.recherche_dateien(
        [f"{api.DATEN}/rag/01_vwv_pokehaltung.pdf"],
        "Welche Pokémon dürfen nicht in den Serverraum?")
    return status == 200, f"HTTP {status}: {kurz(antwort)}", sek


def test_rag_quellen():
    status, text, sek = api.quellen_der_datenbank()
    if status != 200:
        return False, f"HTTP {status}: {kurz(text)}", sek
    if api.WISSENSBASIS not in text:
        return False, f"„{api.WISSENSBASIS}“ fehlt: {kurz(text)}", sek
    return True, f"„{api.WISSENSBASIS}“ ist auswählbar: {kurz(text, 200)}", sek


def test_rag_datenbank():
    status, antwort, sek = api.recherche_datenbank("Welche Pokémon dürfen nicht in den Serverraum?")
    if status != 200:
        return False, f"HTTP {status}: {kurz(antwort)}", sek
    quellen = api.quellen_aus(antwort)
    if not quellen:
        return False, f"keine Quellen in der Antwort (Wissensdatenbank leer?): {kurz(antwort)}", sek
    return True, f"{kurz(api.text_aus(antwort), 300)}  Quellen: {'; '.join(dict.fromkeys(quellen))}", sek


TESTS = [
    ("Ollama: Antwort des Sprachmodells", test_ollama_antwort),
    ("Ollama: Embedding (/v1/embeddings)", test_ollama_embedding),
    ("Core → Chat: /chat/completion", test_chat),
    ("Core → Summary: /summary/text", test_summary),
    ("Core → RAG: /rag/file (PDF + Frage)", test_rag_datei),
    ("Core → RAG: /rag/sources (Wissensdatenbank)", test_rag_quellen),
    ("Core → RAG: /rag/database (Frage an die Wissensdatenbank)", test_rag_datenbank),
]


def main():
    print(f"Smoke-Test  (Sprachmodell {api.LLM_MODELL}, F13-Modell-ID {api.F13_MODELL_ID})\n")
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
