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


def aufloesen(doku, schema):
    """Folgt einer $ref innerhalb der OpenAPI-Datei."""
    tiefe = 0
    while isinstance(schema, dict) and "$ref" in schema and tiefe < 10:
        teile = schema["$ref"].lstrip("#/").split("/")
        ziel = doku
        for teil in teile:
            ziel = ziel.get(teil, {})
        schema = ziel
        tiefe += 1
    return schema if isinstance(schema, dict) else {}


def typ_text(doku, schema):
    schema = schema or {}
    if "$ref" in schema:
        return schema_name(schema["$ref"])
    if "anyOf" in schema or "oneOf" in schema:
        return " | ".join(typ_text(doku, s) for s in schema.get("anyOf") or schema.get("oneOf"))
    if schema.get("type") == "array":
        return f"[{typ_text(doku, schema.get('items'))}]"
    if "enum" in schema:
        return "enum(" + ", ".join(map(str, schema["enum"])) + ")"
    return schema.get("type", "?")


def felder(doku, schema, einzug="        ", gesehen=None):
    """Zeilen mit allen Feldern eines Anfrage-Schemas (Pflichtfelder mit *)."""
    gesehen = gesehen or set()
    schema = aufloesen(doku, schema)
    pflicht = set(schema.get("required", []))
    zeilen = []
    for name, eigenschaft in (schema.get("properties") or {}).items():
        stern = "*" if name in pflicht else " "
        zeilen.append(f"{einzug}{stern} {name}: {typ_text(doku, eigenschaft)}")
        ref = eigenschaft.get("$ref") or (eigenschaft.get("items") or {}).get("$ref")
        if ref and ref not in gesehen and len(einzug) < 16:
            gesehen.add(ref)
            zeilen.extend(felder(doku, {"$ref": ref}, einzug + "    ", gesehen))
    return zeilen


def endpunkte(doku):
    """Liefert Zeilen wie 'POST /completion  ← CompletionRequest'."""
    zeilen = []
    for pfad, methoden in sorted(doku.get("paths", {}).items()):
        for methode, info in methoden.items():
            if methode.lower() not in ("get", "post", "put", "patch", "delete"):
                continue
            koerper = ""
            details = []
            inhalt = (info.get("requestBody") or {}).get("content") or {}
            for medientyp, angabe in inhalt.items():
                schema = angabe.get("schema") or {}
                name = schema_name(schema.get("$ref", "")) or schema.get("type", "")
                koerper = f"  ← {medientyp}: {name}"
                details = felder(doku, schema)
                break
            for parameter in info.get("parameters") or []:
                details.append(f"        {'*' if parameter.get('required') else ' '} "
                               f"{parameter.get('name')} ({parameter.get('in')}): "
                               f"{typ_text(doku, parameter.get('schema'))}")
            zeilen.append(f"{methode.upper():6} {pfad}{koerper}")
            zeilen.extend(details)
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
    print("\n(* = Pflichtfeld)")
    if fehler:
        print(f"\n{fehler} Dienst(e) ohne API-Beschreibung.")
        return 1
    print("\nFertig.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
