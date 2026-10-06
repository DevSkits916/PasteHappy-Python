param([string]$SigningCertificateThumbprint = "")
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (!(Test-Path .venv/Scripts/python.exe)) {
    python -m venv .venv
    if ($LASTEXITCODE) { throw "Virtual environment creation failed" }
}
& .venv/Scripts/python.exe -m pip install -r requirements-build.txt
if ($LASTEXITCODE) { throw "Dependency installation failed" }
npm ci
if ($LASTEXITCODE) { throw "Frontend dependency installation failed" }
npm run build
if ($LASTEXITCODE) { throw "Frontend build failed" }
& .venv/Scripts/python.exe -m unittest discover -s tests_python -v
if ($LASTEXITCODE) { throw "Tests failed" }
& .venv/Scripts/python.exe -m PyInstaller --noconfirm --clean --onefile --console --name PasteHappy --distpath releases --workpath build/pyinstaller --specpath build --add-data "$PSScriptRoot/dist;dist" --collect-all playwright desktop.py
if ($LASTEXITCODE) { throw "Executable build failed" }
if ($SigningCertificateThumbprint) {
    $certificate = Get-Item -LiteralPath "Cert:\CurrentUser\My\$SigningCertificateThumbprint"
    if (!$certificate.HasPrivateKey -or $certificate.NotAfter -le (Get-Date)) {
        throw "Signing requires a current code-signing certificate with a private key"
    }
    $signature = Set-AuthenticodeSignature -FilePath releases/PasteHappy.exe -Certificate $certificate -HashAlgorithm SHA256 -TimestampServer "http://timestamp.digicert.com"
    if ($signature.Status -ne "Valid") { throw "Signature verification failed: $($signature.StatusMessage)" }
}
$digest = (Get-FileHash releases/PasteHappy.exe -Algorithm SHA256).Hash.ToLowerInvariant()
"$digest  PasteHappy.exe" | Set-Content -Encoding ascii releases/SHA256SUMS.txt
