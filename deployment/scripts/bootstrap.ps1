# Bootstrap the minimum CRK toolchain: proto plus pinned moon/python/uv.
# Run once before the README quick start.
param(
    [switch]$ToolchainOnly,
    [switch]$Configure,
    [string]$Workflow = "self-hosted",
    [switch]$NonInteractive,
    [switch]$Force,
    [switch]$DryRun,
    [string]$EnvFile = "",
    [string]$SearxngSettingsFile = "",
    [string[]]$Set = @()
)

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

function Invoke-CrkBootstrapConfig {
    $configArgs = @("deployment/scripts/bootstrap_env.py", "configure", "--workflow", $Workflow)
    if ($NonInteractive) { $configArgs += "--non-interactive" }
    if ($Force) { $configArgs += "--force" }
    if ($DryRun) { $configArgs += "--dry-run" }
    if ($EnvFile) { $configArgs += @("--env-file", $EnvFile) }
    if ($SearxngSettingsFile) { $configArgs += @("--searxng-settings-file", $SearxngSettingsFile) }
    foreach ($item in $Set) {
        $configArgs += @("--set", $item)
    }
    & python @configArgs
}

if ($ToolchainOnly) {
    exit 0
}

if ($Configure) {
    Invoke-CrkBootstrapConfig
} elseif (-not [Console]::IsInputRedirected -and -not [Console]::IsOutputRedirected) {
    $answer = Read-Host "Configure local CRK environment now? [Y/n]"
    if (-not $answer -or $answer -match "^(y|yes)$") {
        Invoke-CrkBootstrapConfig
    }
} else {
    Write-Host "To configure local deployment env later:"
    Write-Host "  .\deployment\scripts\bootstrap.ps1 -Configure"
}
