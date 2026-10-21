"""Stellt die Stammzertifikate für Downloads aus den Containern bereit (Firmen-Proxy).

In manchen Firmennetzen prüft ein Proxy HTTPS-Verbindungen und signiert sie mit einem
eigenen Stammzertifikat neu. Windows vertraut diesem Zertifikat, die Container nicht. Dann
scheitern Downloads mit „CERTIFICATE_VERIFY_FAILED“, z. B. die PDF-Modelle des Parsers.

Zwei Aufgaben:

  python zertifikate.py
      Läuft automatisch bei jedem "docker compose up" als Einmal-Container (Dienst
      "zertifikate"). Schreibt /zertifikate/ca-bundle.pem: die öffentlichen
      Stammzertifikate plus alle eigenen Zertifikate aus config/zertifikate/
      (*.pem, *.crt, *.cer; PEM oder DER). parser und ollama nutzen diese Datei über
      SSL_CERT_FILE. Ohne eigene Zertifikate enthält sie nur die öffentlichen.

  python zertifikate.py pruefen
      Wird von start.cmd (werkzeuge/firmenzertifikat.ps1) aufgerufen. Prüft, ob die
      Verbindung zu huggingface.co mit den öffentlichen Stammzertifikaten gültig ist.
      Exit-Code 0 = gültig, 2 = keine Verbindung, 3 = fremdes Zertifikat. Dann wird die
      vom Proxy gesendete Kette (Server- und Zwischenzertifikate) als PEM ausgegeben, damit
      Windows sie bis zu seinem vertrauten Stammzertifikat ergänzen kann.

Nur Python-Standardbibliothek.
"""

import glob
import os
import socket
import ssl
import sys
import urllib.error
import urllib.request

EIGENE = os.environ.get("EIGENE_ZERTIFIKATE", "/eigene")
ZIEL = os.environ.get("ZERTIFIKAT_BUNDLE", "/zertifikate/ca-bundle.pem")
PRUEF_HOST = os.environ.get("PRUEF_HOST", "huggingface.co")
TIMEOUT_S = 15

OEFFENTLICHE = ("/etc/ssl/certs/ca-certificates.crt", "/etc/ssl/cert.pem")


def oeffentliche_zertifikate():
    pfade = [ssl.get_default_verify_paths().openssl_cafile, *OEFFENTLICHE]
    for pfad in pfade:
        if pfad and os.path.isfile(pfad):
            with open(pfad, encoding="ascii", errors="replace") as datei:
                return pfad, datei.read()
    return None, ""


def als_pem(inhalt):
    """PEM-Text unverändert, DER (binär) wird in PEM umgewandelt."""
    if b"-----BEGIN CERTIFICATE-----" in inhalt:
        return inhalt.decode("ascii", "replace").replace("\r\n", "\n")
    return ssl.DER_cert_to_PEM_cert(inhalt)


def buendeln():
    quelle, text = oeffentliche_zertifikate()
    if not text:
        print("✘ Keine öffentlichen Stammzertifikate im Image gefunden.", flush=True)
        return 1
    teile = [text.rstrip("\n") + "\n"]
    print(f"Öffentliche Stammzertifikate: {quelle} ({text.count('BEGIN CERTIFICATE')})")

    eigene = sorted(p for p in glob.glob(f"{EIGENE}/*")
                    if p.lower().endswith((".pem", ".crt", ".cer")))
    for pfad in eigene:
        name = os.path.basename(pfad)
        try:
            with open(pfad, "rb") as datei:
                pem = als_pem(datei.read())
            # Prüft, ob die Datei wirklich Zertifikate enthält.
            ssl.create_default_context(cadata=pem)
        except (OSError, ValueError, ssl.SSLError) as fehler:
            print(f"  ✘ {name} übersprungen (kein lesbares Zertifikat): {fehler}", flush=True)
            continue
        teile.append(f"# {name}\n{pem.strip()}\n")
        print(f"  ✔ {name} ({pem.count('BEGIN CERTIFICATE')} Zertifikat(e))")
    if not eigene:
        print("Keine eigenen Zertifikate in config/zertifikate/ (ohne Firmen-Proxy normal).")

    os.makedirs(os.path.dirname(ZIEL), exist_ok=True)
    zwischen = f"{ZIEL}.neu"
    with open(zwischen, "w", encoding="ascii", errors="replace") as datei:
        datei.write("".join(teile))
    os.chmod(zwischen, 0o644)
    os.replace(zwischen, ZIEL)
    print(f"✔ {ZIEL} geschrieben.", flush=True)
    return 0


def gesendete_kette():
    """Zertifikate, die die Gegenstelle sendet (ungeprüft), als PEM; Serverzertifikat zuerst."""
    kontext = ssl.create_default_context()
    kontext.check_hostname = False
    kontext.verify_mode = ssl.CERT_NONE
    with socket.create_connection((PRUEF_HOST, 443), timeout=TIMEOUT_S) as roh:
        with kontext.wrap_socket(roh, server_hostname=PRUEF_HOST) as tls:
            # Ab Python 3.13; ältere Versionen liefern nur das Serverzertifikat.
            if hasattr(tls, "get_unverified_chain"):
                kette = tls.get_unverified_chain()
            else:
                kette = [tls.getpeercert(binary_form=True)]
    return [ssl.DER_cert_to_PEM_cert(der) for der in kette]


def pruefen():
    try:
        with urllib.request.urlopen(f"https://{PRUEF_HOST}/", timeout=TIMEOUT_S):
            pass
    except urllib.error.HTTPError:
        pass  # TLS war in Ordnung, nur die Seite antwortet mit einem Fehlercode
    except (urllib.error.URLError, ssl.SSLError, OSError) as fehler:
        grund = getattr(fehler, "reason", fehler)
        if not isinstance(grund, ssl.SSLCertVerificationError):
            print(f"KEINE-VERBINDUNG {grund}")
            return 2
        try:
            print("".join(gesendete_kette()))
        except (OSError, socket.timeout) as fehler2:
            print(f"KEINE-VERBINDUNG {fehler2}")
            return 2
        return 3
    print("GUELTIG")
    return 0


if __name__ == "__main__":
    sys.exit(pruefen() if sys.argv[1:] == ["pruefen"] else buendeln())
