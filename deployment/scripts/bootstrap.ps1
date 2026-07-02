# Bootstrap the minimum CRK toolchain: proto plus pinned moon/python/uv.
# Run once before the README quick start.
$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..\..")

if (-not (Get-Command proto -ErrorAction SilentlyContinue)) {
    Write-Host "Installing proto (https://moonrepo.dev/proto)..."
    Invoke-RestMethod https://moonrepo.dev/install/proto.ps1 | Invoke-Expression
    $env:Path = "$env:USERPROFILE\.proto\bin;$env:USERPROFILE\.proto\shims;$env:Path"
}

Write-Host "Installing tools pinned in .prototools (moon, python, uv)..."
proto use

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Installing uv (https://docs.astral.sh/uv/)..."
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}

Write-Host ""
Write-Host "Toolchain ready. Continue with the README quick start:"
Write-Host "  moon run crk:check"
