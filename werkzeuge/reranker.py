"""Stichwort-Reranker: ein sehr kleiner, lokaler Ersatz für ein Reranking-Modell.

Der RAG-Dienst von F13 verlangt einen Reranker mit Cohere-kompatibler Schnittstelle
(POST /v1/rerank). Ein echtes Reranking-Modell bräuchte zusätzlich ca. 1 GB RAM, zu viel
für den 8-GB-Laptop. Dieser Dienst sortiert die gefundenen Textabschnitte stattdessen nach
gemeinsamen Stichwörtern mit der Frage. Seltene Wörter zählen mehr als häufige (wie bei
BM25). Die eigentliche Suche macht weiterhin das Embedding-Modell; hier wird nur die
Reihenfolge der Treffer verfeinert.

Läuft als Compose-Dienst "reranker" auf Port 7997. Nur Python-Standardbibliothek.
"""

import json
import math
import re
import sys
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODELL = "stichwort-reranker"
PORT = 7997

# Häufige deutsche Wörter ohne Aussagekraft für die Suche.
STOPPWOERTER = set("""
aber alle allem allen aller alles als also am an auch auf aus bei beim bin bis bitte da
damit dann das dass dem den denn der des die dies diese diesem diesen dieser dieses doch
dort du durch ein eine einem einen einer eines er es etwa euch für gegen hat hatte hier
ich ihr im in ins ist ja jede jedem jeden jeder jedes kann kein keine können mal man mehr
mein mich mit muss müssen nach nein nicht noch nur ob oder ohne sein seine sich sie sind
so soll sollen über um und uns unter vom von vor wann war was weil welche welcher wenn wer
werden wie wieder wir wird wo zu zum zur darf dürfen mein meine meinem meinen
""".split())

ENDUNGEN = ("ungen", "ung", "en", "er", "es", "em", "e", "n", "s")


def stamm(wort):
    """Sehr einfache Stammbildung: häufige deutsche Endungen abschneiden."""
    for endung in ENDUNGEN:
        if len(wort) > len(endung) + 3 and wort.endswith(endung):
            return wort[: -len(endung)]
    return wort


def woerter(text):
    gefunden = re.findall(r"[a-zäöüßé0-9][a-zäöüßé0-9\-]{1,}", text.lower())
    return [stamm(w) for w in gefunden if w not in STOPPWOERTER and len(w) > 2]


def bewerten(frage, dokumente):
    """Gibt für jedes Dokument eine Punktzahl zwischen 0 und 1 zurück."""
    frage_woerter = set(woerter(frage))
    dokument_woerter = [woerter(d) for d in dokumente]
    anzahl = len(dokumente) or 1
    # Inverse Dokumenthäufigkeit innerhalb der Kandidaten: seltene Treffer wiegen mehr.
    idf = {w: math.log(1 + anzahl / (1 + sum(w in set(d) for d in dokument_woerter)))
           for w in frage_woerter}
    rohwerte = []
    for woerter_im_dokument in dokument_woerter:
        laenge = max(len(woerter_im_dokument), 1)
        haeufigkeit = {}
        for w in woerter_im_dokument:
            haeufigkeit[w] = haeufigkeit.get(w, 0) + 1
        wert = 0.0
        for w in frage_woerter:
            tf = haeufigkeit.get(w, 0)
            if tf:
                # BM25-artige Sättigung, kurze Abschnitte leicht bevorzugt.
                wert += idf[w] * (tf * 2.2) / (tf + 1.2 * (0.25 + 0.75 * laenge / 120))
        rohwerte.append(wert)
    hoechster = max(rohwerte) if rohwerte and max(rohwerte) > 0 else 1.0
    return [round(w / hoechster, 4) for w in rohwerte]


def text_von(dokument):
    if isinstance(dokument, dict):
        return str(dokument.get("text") or dokument.get("content") or "")
    return str(dokument)


class Handler(BaseHTTPRequestHandler):
    def _antwort(self, status, daten):
        inhalt = json.dumps(daten, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(inhalt)))
        self.end_headers()
        self.wfile.write(inhalt)

    def do_GET(self):
        pfad = self.path.split("?")[0].rstrip("/")
        if pfad in ("/v1/models", "/models"):
            self._antwort(200, {"object": "list",
                                "data": [{"id": MODELL, "object": "model", "owned_by": "f13-demo"}]})
        elif pfad in ("", "/health", "/v1/health"):
            self._antwort(200, {"status": "ok", "model": MODELL})
        else:
            self._antwort(404, {"error": "nicht gefunden"})

    def do_POST(self):
        pfad = self.path.split("?")[0].rstrip("/")
        if pfad not in ("/v1/rerank", "/v2/rerank", "/rerank"):
            self._antwort(404, {"error": "nicht gefunden"})
            return
        try:
            laenge = int(self.headers.get("Content-Length") or 0)
            anfrage = json.loads(self.rfile.read(laenge) or b"{}")
            frage = str(anfrage.get("query", ""))
            dokumente = [text_von(d) for d in anfrage.get("documents", [])]
        except (ValueError, TypeError, AttributeError) as fehler:
            self._antwort(400, {"error": f"ungültige Anfrage: {fehler}"})
            return
        punkte = bewerten(frage, dokumente)
        reihenfolge = sorted(range(len(dokumente)), key=lambda i: punkte[i], reverse=True)
        top_n = anfrage.get("top_n") or len(dokumente)
        mit_text = anfrage.get("return_documents", False)
        ergebnisse = []
        for i in reihenfolge[: int(top_n)]:
            eintrag = {"index": i, "relevance_score": punkte[i]}
            if mit_text:
                eintrag["document"] = {"text": dokumente[i]}
            ergebnisse.append(eintrag)
        self._antwort(200, {"id": str(uuid.uuid4()), "results": ergebnisse,
                            "meta": {"api_version": {"version": "1"},
                                     "billed_units": {"search_units": 1}}})

    def log_message(self, format, *args):
        sys.stderr.write(f"reranker: {self.address_string()} {format % args}\n")


def main():
    print(f"Stichwort-Reranker läuft auf Port {PORT} (Modell „{MODELL}“).", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
