# Erkennt einen Firmen-Proxy, der HTTPS neu signiert, und legt dessen Stammzertifikat
# für die Container ab. Wird von start.cmd aufgerufen; von Hand:
#   powershell -NoProfile -ExecutionPolicy Bypass -File werkzeuge\firmenzertifikat.ps1
#
# Ablauf: Ein Container prüft die Verbindung zu huggingface.co. Ist das Zertifikat fremd,
# ergänzt Windows die Kette aus seinem eigenen Zertifikatspeicher. Zwischen- und
# Stammzertifikat landen in config\zertifikate\firmen-ca.pem (nicht eingecheckt). Der
# Dienst "zertifikate" nimmt sie beim nächsten "docker compose up" auf.
# Neu erkennen: config\zertifikate\firmen-ca.pem löschen und start.cmd erneut ausführen.

$ErrorActionPreference = 'Continue'
Set-Location (Split-Path -Parent $PSScriptRoot)
$ziel = 'config\zertifikate\firmen-ca.pem'

if (Test-Path $ziel) {
    Write-Host "      Firmenzertifikat vorhanden ($ziel)."
    exit 0
}

$ausgabe = & docker compose run --rm --no-deps -T zertifikate python /werkzeuge/zertifikate.py pruefen 2>$null
$code = $LASTEXITCODE
$text = ($ausgabe | Out-String)

if ($code -eq 0) {
    Write-Host '      Kein Firmen-Proxy erkannt, öffentliche Zertifikate genügen.'
    exit 0
}
if ($code -ne 3) {
    Write-Host '      Prüfung nicht möglich (keine Internetverbindung?), übersprungen.'
    exit 0
}

try {
    $b64 = [regex]::Match($text, '-----BEGIN CERTIFICATE-----(.+?)-----END CERTIFICATE-----', 'Singleline').Groups[1].Value -replace '\s', ''
    $server = [Security.Cryptography.X509Certificates.X509Certificate2]::new([Convert]::FromBase64String($b64))
} catch {
    Write-Host "      FEHLER: Serverzertifikat nicht lesbar: $($_.Exception.Message)"
    exit 1
}
Write-Host "      Firmen-Proxy erkannt. Zertifikat ausgestellt von: $($server.Issuer)"

$kette = [Security.Cryptography.X509Certificates.X509Chain]::new()
$kette.ChainPolicy.RevocationMode = 'NoCheck'
$vertraut = $kette.Build($server)
$anzahl = $kette.ChainElements.Count
$stamm = $kette.ChainElements[$anzahl - 1].Certificate

if (-not $vertraut -or $anzahl -lt 2) {
    Write-Host '      FEHLER: Windows vertraut diesem Zertifikat auch nicht.'
    Write-Host '      Bitte die IT nach dem Stammzertifikat der SSL-Prüfung fragen (.cer oder .pem)'
    Write-Host '      und als Datei in config\zertifikate\ ablegen, dann start.cmd erneut ausführen.'
    exit 1
}

$bloecke = for ($i = 1; $i -lt $anzahl; $i++) {
    "-----BEGIN CERTIFICATE-----`n" +
    [Convert]::ToBase64String($kette.ChainElements[$i].Certificate.RawData, 'InsertLineBreaks') +
    "`n-----END CERTIFICATE-----"
}
[IO.File]::WriteAllText((Join-Path (Get-Location) $ziel), (($bloecke -join "`n") + "`n").Replace("`r`n", "`n"))
Write-Host "      Stammzertifikat aus Windows übernommen: $($stamm.Subject)"
Write-Host "      Gespeichert in $ziel"
exit 0
