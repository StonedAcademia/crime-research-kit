# Bootstrap the minimum TRCR toolchain: proto, plus the moon and python
# versions pinned in .prototools. Run once before the README quick start.
$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..\..")

if (-not (Get-Command proto -ErrorAction SilentlyContinue)) {
    Write-Host "Installing proto (https://moonrepo.dev/proto)..."
    Invoke-RestMethod https://moonrepo.dev/install/proto.ps1 | Invoke-Expression
    $env:Path = "$env:USERPROFILE\.proto\bin;$env:USERPROFILE\.proto\shims;$env:Path"
}

Write-Host "Installing tools pinned in .prototools (moon, python)..."
proto use

Write-Host ""
Write-Host "Toolchain ready. Continue with the README quick start:"
Write-Host "  moon run trcr:install-dev"
