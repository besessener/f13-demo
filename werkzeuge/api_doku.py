"""Speichert die API-Beschreibungen (OpenAPI) der F13-Dienste und zeigt ihre Endpunkte.

Aufruf (PowerShell):  docker compose run --rm api-doku

Die F13-Dienste sind FastAPI-Anwendungen. ANNAHME (ungeprüft): Sie liefern ihre
Beschreibung unter /openapi.json. Die Dateien landen im Repo-Ordner unter
ausgabe/openapi/<dienst>.json. Damit lassen sich die echten Anfrageformate nachschlagen,
statt sie zu raten.

Nur Python-Standardbibliothek.
"""

import json
import os
import sys
import urllib.error
import urllib.request

DIENSTE = [d.strip() for d in os.environ.get(
    "API_DIENSTE", "chat,summary,rag,parser,feedback").split(",") if d.strip()]
PORT = os.environ.get("API_PORT", "8000")
ZIEL = os.environ.get("AUSGABE_ORDNER", "/ausgabe") + "/openapi"

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def schema_name(ref):
    return ref.rsplit("/", 1)[-1] if ref else ""


def endpunkte(doku):
    """Liefert Zeilen wie 'POST /completion  ← CompletionRequest'."""
    zeilen = []
    for pfad, methoden in sorted(doku.get("paths", {}).items()):
        for methode, info in methoden.items():
            if methode.lower() not in ("get", "post", "put", "patch", "delete"):
                continue
            koerper = ""
            inhalt = (info.get("requestBody") or {}).get("content") or {}
            for medientyp, angabe in inhalt.items():
                schema = angabe.get("schema") or {}
                name = schema_name(schema.get("$ref", "")) or schema.get("type", "")
                koerper = f"  ← {medientyp}: {name}"
                break
            zeilen.append(f"{methode.upper():6} {pfad}{koerper}")
    return zeilen


def main():
    os.makedirs(ZIEL, exist_ok=True)
    fehler = 0
    for dienst in DIENSTE:
        url = f"http://{dienst}:{PORT}/openapi.json"
        print(f"\n▶ {dienst}  ({url})")
        try:
            with OPENER.open(url, timeout=30) as antwort:
                doku = json.load(antwort)
        except (urllib.error.URLError, OSError, ValueError) as grund:
            print(f"  ✘ nicht abrufbar: {grund}")
            fehler += 1
            continue
        datei = f"{ZIEL}/{dienst}.json"
        with open(datei, "w", encoding="utf-8") as ausgabe:
            json.dump(doku, ausgabe, ensure_ascii=False, indent=2)
        version = (doku.get("info") or {}).get("version", "?")
        print(f"  ✔ gespeichert: ausgabe/openapi/{dienst}.json (Version {version})")
        for zeile in endpunkte(doku):
            print(f"    {zeile}")
    if fehler:
        print(f"\n{fehler} Dienst(e) ohne API-Beschreibung.")
        return 1
    print("\nFertig.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
