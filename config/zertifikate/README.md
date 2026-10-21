# Eigene Stammzertifikate (Firmen-Proxy)

In manchen Firmennetzen prüft ein Proxy HTTPS-Verbindungen und signiert sie mit einem
eigenen Stammzertifikat neu. Windows vertraut diesem Zertifikat, die Container nicht. Ohne
es scheitert z. B. der Parser beim ersten Start mit `CERTIFICATE_VERIFY_FAILED`, weil er
seine PDF-Modelle von `huggingface.co` lädt.

## Automatisch

`start.cmd` erledigt das selbst (Schritt 2, `werkzeuge/firmenzertifikat.ps1`):

1. Ein Container prüft die Verbindung zu `huggingface.co`.
2. Ist das Zertifikat fremd, ergänzt Windows die Kette aus seinem Zertifikatspeicher.
3. Zwischen- und Stammzertifikat landen hier als `firmen-ca.pem`.

Neu erkennen, z. B. nach einem Wechsel des Proxys: `firmen-ca.pem` löschen und `start.cmd`
erneut ausführen.

## Von Hand

Kennt Windows das Zertifikat nicht, meldet `start.cmd` das. Dann bei der IT das
Stammzertifikat der SSL-Prüfung erfragen und hier ablegen. Erlaubt sind `*.pem`, `*.crt`
und `*.cer`, jeweils als PEM (Base64) oder DER (binär). Danach `start.cmd` erneut
ausführen.

## Was damit passiert

Der Einmal-Container `zertifikate` (`werkzeuge/zertifikate.py`) läuft bei jedem
`docker compose up`. Er schreibt die öffentlichen Stammzertifikate plus alle Dateien aus
diesem Ordner ins Volume `zertifikate`. `parser`, `ollama` und `versionen` lesen die Datei
über `SSL_CERT_FILE`. Ohne Dateien hier enthält sie nur die öffentlichen
Stammzertifikate; die Demo funktioniert dann wie ohne Proxy.

Die Zertifikate in diesem Ordner werden nicht eingecheckt (siehe `.gitignore`).
